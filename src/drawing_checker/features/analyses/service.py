"""Điều phối pipeline — feature duy nhất được phụ thuộc các feature khác (qua service công khai).

Thứ tự bước và nghĩa: docs/architecture.md §2, §5.
  extract   : ingest + sheets → báo pageCount
  ocr       : extraction thực thể số (không phải OCR)
  material  : semantic
  geometry  : geometry
  aggregate : rules.evaluator + findings → gửi toàn bộ kết quả

Hiện tại (hợp đồng BE v0): extract = tải PDF + ingest + trích thực thể + đọc cấu trúc hồ sơ (`sheets`) từng trang
→ rule engine (không AI) → AI cho các dòng rule engine chưa hỗ trợ (chỉ khi MAIN_AI_PROVIDER ≠ off, D-22)
→ aggregate kèm findings v1 (mọi dòng tiêu chí, integration-contract.md §5.3). BE cho phép bỏ qua bước giữa.
Kết quả ingest xem ở viewer debug của job (features/ingest/inspector.py, phục vụ tại /debug/inspect/), gồm tab "Kiểm tra".
BE v0 luôn gửi `rules: []` → dùng bộ rule mock (MAIN_MOCK_RULESET) nếu được cấu hình.
"""

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path

from drawing_checker.common.enums import AnalysisRunState, AnalysisStage
from drawing_checker.features.analyses.schemas import (
    AnalysisCallback,
    AnalysisStatus,
    DispatchRequest,
    DispatchResult,
)
from drawing_checker.features.extraction.schemas import Entity
from drawing_checker.features.extraction.service import ExtractionService
from drawing_checker.features.findings.schemas import LineResult, RawFinding
from drawing_checker.features.findings.service import FindingsService, PageSizes
from drawing_checker.features.geometry.schemas import Table
from drawing_checker.features.geometry.service import GeometryService
from drawing_checker.features.ingest.inspector import IngestInspector
from drawing_checker.features.ingest.schemas import TextSpan
from drawing_checker.features.ingest.service import IngestError, IngestService, PageReader
from drawing_checker.features.rules.schemas import RuleInput
from drawing_checker.features.rules.service import UNSUPPORTED_REASON, CheckReport, RulesService, load_mock_rules
from drawing_checker.features.semantic.digest import build_digest
from drawing_checker.features.semantic.service import AiRun, SemanticService, outcome_of
from drawing_checker.features.sheets.schemas import Abbreviation, DocumentIndex, SheetInfo
from drawing_checker.features.sheets.service import SheetService
from drawing_checker.infrastructure.backend_client import BackendClient, CallbackRejected, JobAborted
from drawing_checker.infrastructure.job_runner import JobRunner
from drawing_checker.infrastructure.pdf_fetcher import PdfFetchError, PdfFetcher

logger = logging.getLogger(__name__)


class JobNotFound(Exception):
    pass


class _StageFailed(Exception):
    """Lỗi đã biết trong một bước — message tiếng Việt gửi BE qua errorMessage."""


class AnalysesService:
    def __init__(
        self,
        backend: BackendClient,
        fetcher: PdfFetcher,
        runner: JobRunner,
        ingest: IngestService | None = None,
        inspect_dir: Path | None = None,
        inspect_dpi: int = 0,
        mock_ruleset: Path | None = None,
        confidence_threshold: float = 0.8,
        semantic: SemanticService | None = None,
        ai_include_numeric: bool = False,
    ) -> None:
        self._backend = backend
        self._fetcher = fetcher
        self._runner = runner
        self._ingest = ingest or IngestService()
        self._inspect_dir = inspect_dir  # None = không ghi viewer debug
        self._inspect_dpi = inspect_dpi
        self._mock_ruleset = mock_ruleset  # dùng khi BE gửi rules: [] (hợp đồng v0)
        self._extraction = ExtractionService()
        self._sheets = SheetService()
        self._geometry = GeometryService()
        self._rules = RulesService()
        self._findings = FindingsService(confidence_threshold)
        self._semantic = semantic  # None = không gọi AI (mặc định)
        self._ai_include_numeric = ai_include_numeric
        self._jobs: dict[str, AnalysisStatus] = {}

    async def dispatch(self, request: DispatchRequest) -> DispatchResult:
        """Nhận việc, tạo externalJobId, đẩy pipeline chạy nền, trả ngay (202)."""
        job_id = f"job-{uuid.uuid4()}"
        self._jobs[job_id] = AnalysisStatus(
            externalJobId=job_id,
            reviewId=request.review_id,
            stage=AnalysisStage.EXTRACT,
            state=AnalysisRunState.RUNNING,
            percent=0,
        )
        self._runner.submit(job_id, lambda: self.run_pipeline(job_id, request))
        return DispatchResult(externalJobId=job_id, stage=AnalysisStage.EXTRACT)

    async def run_pipeline(self, job_id: str, request: DispatchRequest) -> None:
        """Tải PDF → chạy từng bước → callback BE sau mỗi bước; lỗi → callback state=failed."""
        stage, percent = AnalysisStage.EXTRACT, 5
        pdf_path = None
        inspector = self._new_inspector(job_id, request)
        outcome, error = "failed", None
        try:
            await self._report(job_id, request, stage, AnalysisRunState.RUNNING, percent)
            try:
                pdf_path = await self._fetcher.fetch(request.pdf_url, job_id)
                with self._ingest.reader(pdf_path) as reader:
                    page_count, entities, index, page_texts, page_sizes, tables = await self._ingest_pages(
                        job_id, request, reader, inspector)
            except (PdfFetchError, IngestError) as exc:
                raise _StageFailed(str(exc)) from exc
            percent = 90
            await self._report(job_id, request, stage, AnalysisRunState.COMPLETED, percent, page_count=page_count)
            if inspector is not None:
                inspector.write_dossier(_dossier_payload(index))

            # Rule engine (không AI) + AI cho dòng chưa hỗ trợ → viewer + findings v1 gửi BE.
            dossier = dossier_id(pdf_path)
            findings = await asyncio.to_thread(self._run_checks, job_id, request, entities, inspector, index,
                                               page_texts, dossier, page_sizes, tables)

            # Chưa có ocr/material/geometry — bước aggregate mang toàn bộ kết quả.
            stage, percent = AnalysisStage.AGGREGATE, 100
            await self._report(job_id, request, stage, AnalysisRunState.COMPLETED, percent, findings=findings)
            outcome = "completed"
        except _StageFailed as exc:
            error = str(exc)
            await self._report_failure(job_id, request, stage, self._jobs[job_id].percent, error)
        except JobAborted as exc:
            error = "BE dừng job (hồ sơ đã chạy lại / hủy / không còn)"
            logger.info("Job %s dừng theo yêu cầu BE: %s", job_id, exc)
            self._set_state(job_id, AnalysisRunState.FAILED)
        except CallbackRejected:
            error = "BE từ chối callback (sai hợp đồng / token)"
            logger.exception("BE từ chối callback của job %s — kiểm tra hợp đồng / token", job_id)
            self._set_state(job_id, AnalysisRunState.FAILED)
        except asyncio.CancelledError:
            outcome, error = "cancelled", "Đã hủy"
            self._set_state(job_id, AnalysisRunState.FAILED)
            raise
        except Exception as exc:
            error = f"Lỗi nội bộ: {exc!r}"
            logger.exception("Job %s lỗi ngoài dự kiến", job_id)
            await self._report_failure(job_id, request, stage, percent, "Lỗi nội bộ khi phân tích bản vẽ.")
        finally:
            if pdf_path is not None:
                pdf_path.unlink(missing_ok=True)
            if inspector is not None:
                try:
                    viewer = inspector.finish(outcome, error)
                    logger.info("Viewer ingest của job %s: %s", job_id, viewer)
                except OSError:
                    logger.exception("Không ghi được viewer của job %s", job_id)

    async def _ingest_pages(
        self, job_id: str, request: DispatchRequest, reader: PageReader, inspector: IngestInspector | None
    ) -> tuple[int, list[Entity], DocumentIndex, list[tuple[int, list[TextSpan]]], PageSizes, dict[int, list[Table]]]:
        """Ingest + trích thực thể + đọc cấu trúc hồ sơ (khung tên, tiêu đề hình, bảng viết tắt) từng trang
        trong thread (trang nặng ~5 s CPU), tiến độ 10 → 90%."""
        total = reader.page_count
        dpi = self._inspect_dpi
        entities: list[Entity] = []
        sheets: list[SheetInfo] = []
        abbreviations: list[Abbreviation] = []
        page_texts: list[tuple[int, list[TextSpan]]] = []  # chữ từng trang — cho bản tóm tắt gửi AI (nhẹ, ~10k khối)
        page_sizes: PageSizes = {}  # quy đổi tọa độ bằng chứng sang % (Q-01)
        tables: dict[int, list[Table]] = {}  # bảng từ lưới kẻ — bản tóm tắt gửi AI in chữ theo hàng / ô
        if inspector is not None:
            inspector.start(total, dpi)

        def process(page_number: int) -> None:
            page = reader.read(page_number)
            if inspector is not None:
                inspector.write_page(page, reader.render_jpeg(page_number, dpi) if dpi > 0 else None)
            entities.extend(self._extraction.extract(page))
            sheets.append(self._sheets.analyze(page))
            abbreviations.extend(self._sheets.abbreviations(page))
            page_texts.append((page_number, page.texts))
            page_sizes[page_number] = (page.width, page.height)
            tables[page_number] = self._geometry.tables(page)  # ~0,1 s / trang PN2
            # Nét vẽ của trang (có thể ~300k) được giải phóng ngay — bước sau chỉ cần thực thể.

        await self._report(job_id, request, AnalysisStage.EXTRACT, AnalysisRunState.RUNNING, 10)
        for n in range(1, total + 1):
            await asyncio.to_thread(process, n)
            percent = 10 + round(80 * n / total)
            if percent < 90:
                await self._report(job_id, request, AnalysisStage.EXTRACT, AnalysisRunState.RUNNING, percent)
        index = self._sheets.build_index(sheets, abbreviations, entities)
        return total, entities, index, page_texts, page_sizes, tables

    def _run_checks(
        self, job_id: str, request: DispatchRequest, entities: list[Entity], inspector: IngestInspector | None,
        index: DocumentIndex | None = None, page_texts: list[tuple[int, list[TextSpan]]] | None = None,
        dossier: str | None = None, page_sizes: PageSizes | None = None,
        tables: dict[int, list[Table]] | None = None,
    ) -> list[RawFinding]:
        rules, source = self._resolve_rules(request)
        if not rules:
            logger.info("Job %s: không có bộ rule (BE gửi rỗng, không cấu hình mock) — bỏ qua kiểm tra", job_id)
            return []
        report = self._rules.check(rules, request.house_type, request.categories, entities)
        ai = None
        if self._semantic is not None and index is not None and page_texts is not None:
            ai = self._run_ai(job_id, request, report, index, page_texts, tables)
        results = self._findings.finalize(report.results)
        logger.info("Job %s: kiểm %d dòng tiêu chí (%s) — %s", job_id, report.coverage["linesApplicable"],
                    source, report.coverage["byStatus"])
        if inspector is not None:
            inspector.write_checks(checks_payload(report, results, source, request.house_type.value,
                                                  [c.value for c in request.categories], entities, ai, dossier))
        return self._findings.to_backend(job_id, report.results, report.rules, page_sizes or {},
                                         is_not_applicable=lambda r: outcome_of(r) == "n/a")

    def _run_ai(
        self, job_id: str, request: DispatchRequest, report: CheckReport, index: DocumentIndex,
        page_texts: list[tuple[int, list[TextSpan]]], tables: dict[int, list[Table]] | None = None,
    ) -> AiRun:
        """AI kiểm các dòng rule engine chưa hỗ trợ; thay kết quả "chưa hỗ trợ" bằng kết quả AI (sửa `report` tại chỗ)."""
        only: dict[str, set[int]] = {}
        for r in report.results:
            if r.reason == UNSUPPORTED_REASON:
                only.setdefault(r.rule_id, set()).add(r.line_index)
        digest = build_digest(page_texts, index, include_numeric=self._ai_include_numeric, tables=tables)
        ai = self._semantic.judge_rules(report.rules, digest, request.house_type, request.categories, only)
        by_key = {(r.rule_id, r.line_index): r for r in ai.results}
        report.results = [by_key.get((r.rule_id, r.line_index), r) for r in report.results]
        report.coverage["ai"] = {
            "lines": sum(len(v) for v in only.values()), "calls": len(ai.calls), "usd": round(ai.spent_usd, 4),
            "errors": sum(1 for c in ai.calls if c["error"]), "stopped": ai.stopped,
        }
        logger.info("Job %s: AI kiểm %d dòng, %d lần gọi, %.4f USD%s", job_id, report.coverage["ai"]["lines"],
                    len(ai.calls), ai.spent_usd, f" — {ai.stopped}" if ai.stopped else "")
        return ai

    def _resolve_rules(self, request: DispatchRequest) -> tuple[list[RuleInput], str]:
        if request.rules:
            return request.rules, "BE"
        if self._mock_ruleset is not None and self._mock_ruleset.exists():
            return load_mock_rules(self._mock_ruleset), f"mock: {self._mock_ruleset.name}"
        return [], ""

    def _new_inspector(self, job_id: str, request: DispatchRequest) -> IngestInspector | None:
        if self._inspect_dir is None:
            return None
        try:
            return IngestInspector(
                self._inspect_dir,
                job_id,
                {
                    "source": "BE",
                    "reviewId": request.review_id,
                    "houseType": request.house_type.value,
                    "categories": [c.value for c in request.categories],
                    "ruleCount": len(request.rules),
                },
            )
        except OSError:
            logger.exception("Không tạo được thư mục viewer cho job %s — bỏ qua viewer", job_id)
            return None

    async def get_status(self, job_id: str) -> AnalysisStatus:
        status = self._jobs.get(job_id)
        if status is None:
            raise JobNotFound(job_id)
        return status

    async def cancel(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise JobNotFound(job_id)
        self._runner.cancel(job_id)
        self._set_state(job_id, AnalysisRunState.FAILED)

    async def _report(
        self,
        job_id: str,
        request: DispatchRequest,
        stage: AnalysisStage,
        state: AnalysisRunState,
        percent: int,
        **extra: object,
    ) -> None:
        callback = AnalysisCallback(
            reviewId=request.review_id,
            externalJobId=job_id,
            stage=stage,
            state=state,
            percent=percent,
            **extra,
        )
        self._jobs[job_id] = AnalysisStatus(
            externalJobId=job_id, reviewId=request.review_id, stage=stage, state=state, percent=percent
        )
        await self._backend.send_callback(request.callback_url, callback)

    async def _report_failure(
        self, job_id: str, request: DispatchRequest, stage: AnalysisStage, percent: int, message: str
    ) -> None:
        try:
            await self._report(job_id, request, stage, AnalysisRunState.FAILED, percent, error_message=message)
        except Exception:
            logger.exception("Không gửi được callback failed của job %s", job_id)
            self._set_state(job_id, AnalysisRunState.FAILED)

    def _set_state(self, job_id: str, state: AnalysisRunState) -> None:
        if job_id in self._jobs:
            self._jobs[job_id] = self._jobs[job_id].model_copy(update={"state": state})


def dossier_id(pdf_path: Path) -> str:
    """Mã hồ sơ = 16 ký tự đầu SHA-256 của PDF — khóa của kết quả duyệt (benchmark/reviews.py)."""
    h = hashlib.sha256()
    with pdf_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def checks_payload(
    report: CheckReport, results: list[LineResult], source: str, house_type: str | None, categories: list[str],
    entities: list[Entity], ai: AiRun | None = None, dossier: str | None = None,
) -> dict:
    """Dữ liệu tab "Kiểm tra" của viewer: một dòng / kết quả, kèm nội dung rule để người đọc + nút duyệt."""
    rules = {r.rule_id: r for r in report.rules}
    ai_lines = {(x["ruleId"], x["lineIndex"]): x for x in ai.lines} if ai else {}
    rows = []
    for r in results:
        rule = rules[r.rule_id]
        meta = ai_lines.get((r.rule_id, r.line_index))
        rows.append({
            "ruleId": r.rule_id,
            "outcome": outcome_of(r),
            "ai": {k: meta.get(k) for k in ("model", "promptVersion", "template", "callId")} if meta else None,
            "code": rule.code or f"{rule.parent_code} ({rule.title})",
            "title": rule.title or "",
            "headings": rule.headings,
            "category": rule.category.value if rule.category else None,
            "line": r.line_index,
            "lineText": rule.requirement_lines[r.line_index] if r.line_index < len(rule.requirement_lines) else "",
            "status": r.status.value,
            "confidence": r.confidence,
            "reason": r.reason,
            "supported": r.reason != UNSUPPORTED_REASON,
            "extracted": r.extracted_value,
            "standard": r.standard_value,
            "evidence": [
                {"page": e.page_number, "bbox": _bbox(e.polygon), "role": e.role.value, "text": e.text}
                for e in r.evidence
            ],
        })
    kinds: dict[str, int] = {}
    for e in entities:
        kinds[e.kind.value] = kinds.get(e.kind.value, 0) + 1
    return {
        "source": source,
        "dossier": dossier,
        "houseType": house_type or "không rõ",
        "categories": categories,
        "coverage": report.coverage,
        "entities": kinds,
        "rows": rows,
        "ai": {"calls": ai.calls, "usd": round(ai.spent_usd, 4), "stopped": ai.stopped} if ai else None,
    }


def _bbox(polygon) -> list[float]:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


def _dossier_payload(index: DocumentIndex) -> dict:
    """Dữ liệu tab "Hồ sơ" của viewer: đặc điểm hồ sơ, mục lục trang (khung tên + hình / bảng), bảng viết tắt."""
    sheets = []
    for s in index.sheets:
        tb = s.title_block
        sheets.append({
            "n": s.page_number,
            "name": tb.name if tb else None,
            "number": tb.number if tb else None,
            "scale": tb.scale if tb else None,
            "source": tb.source if tb else None,
            "views": [{"title": v.title, "scale": v.scale_denominator, "bbox": _bbox(v.polygon)} for v in s.views],
        })
    return {
        "profile": index.profile.model_dump(),
        "sheets": sheets,
        "abbreviations": [{"abbr": a.abbr, "meaning": a.meaning, "page": a.page_number, "bbox": _bbox(a.polygon)}
                          for a in index.abbreviations],
    }

