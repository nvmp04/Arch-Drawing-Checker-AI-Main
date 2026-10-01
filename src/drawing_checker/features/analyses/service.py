"""Điều phối pipeline — feature duy nhất được phụ thuộc các feature khác (qua service công khai).

Thứ tự bước và nghĩa: docs/architecture.md §2, §5.
  extract   : ingest + sheets → báo pageCount
  ocr       : extraction thực thể số (không phải OCR)
  material  : semantic
  geometry  : geometry
  aggregate : rules.evaluator + findings → gửi toàn bộ kết quả

Hiện tại (hợp đồng BE v0): extract = tải PDF + ingest + trích thực thể từng trang (tiến độ theo trang)
→ rule engine (không AI) → aggregate, findings rỗng. BE cho phép bỏ qua bước giữa. Kết quả ingest xem ở viewer debug của job
(features/ingest/inspector.py, phục vụ tại /debug/inspect/), gồm tab "Kiểm tra" — chưa gửi gì về BE ngoài tiến độ.
BE v0 luôn gửi `rules: []` → dùng bộ rule mock (MAIN_MOCK_RULESET) nếu được cấu hình.
"""

import asyncio
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
from drawing_checker.features.findings.schemas import LineResult
from drawing_checker.features.findings.service import FindingsService
from drawing_checker.features.ingest.inspector import IngestInspector
from drawing_checker.features.ingest.service import IngestError, IngestService, PageReader
from drawing_checker.features.rules.schemas import RuleInput
from drawing_checker.features.rules.service import UNSUPPORTED_REASON, CheckReport, RulesService, load_mock_rules
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
    ) -> None:
        self._backend = backend
        self._fetcher = fetcher
        self._runner = runner
        self._ingest = ingest or IngestService()
        self._inspect_dir = inspect_dir  # None = không ghi viewer debug
        self._inspect_dpi = inspect_dpi
        self._mock_ruleset = mock_ruleset  # dùng khi BE gửi rules: [] (hợp đồng v0)
        self._extraction = ExtractionService()
        self._rules = RulesService()
        self._findings = FindingsService(confidence_threshold)
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
                    page_count, entities = await self._ingest_pages(job_id, request, reader, inspector)
            except (PdfFetchError, IngestError) as exc:
                raise _StageFailed(str(exc)) from exc
            percent = 90
            await self._report(job_id, request, stage, AnalysisRunState.COMPLETED, percent, page_count=page_count)

            # Rule engine (không AI): kết quả chỉ ghi vào viewer, chưa gửi BE (chờ hợp đồng v1).
            await asyncio.to_thread(self._run_checks, job_id, request, entities, inspector)

            # Chưa có ocr/material/geometry — xong luôn, findings rỗng.
            stage, percent = AnalysisStage.AGGREGATE, 100
            await self._report(job_id, request, stage, AnalysisRunState.COMPLETED, percent, findings=[])
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
    ) -> tuple[int, list[Entity]]:
        """Ingest + trích thực thể lần lượt từng trang trong thread (trang nặng ~5 s CPU), tiến độ 10 → 90%."""
        total = reader.page_count
        dpi = self._inspect_dpi
        entities: list[Entity] = []
        if inspector is not None:
            inspector.start(total, dpi)

        def process(page_number: int) -> None:
            page = reader.read(page_number)
            if inspector is not None:
                inspector.write_page(page, reader.render_jpeg(page_number, dpi) if dpi > 0 else None)
            entities.extend(self._extraction.extract(page))
            # Nét vẽ của trang (có thể ~300k) được giải phóng ngay — bước sau chỉ cần thực thể.

        await self._report(job_id, request, AnalysisStage.EXTRACT, AnalysisRunState.RUNNING, 10)
        for n in range(1, total + 1):
            await asyncio.to_thread(process, n)
            percent = 10 + round(80 * n / total)
            if percent < 90:
                await self._report(job_id, request, AnalysisStage.EXTRACT, AnalysisRunState.RUNNING, percent)
        return total, entities

    def _run_checks(
        self, job_id: str, request: DispatchRequest, entities: list[Entity], inspector: IngestInspector | None
    ) -> None:
        rules, source = self._resolve_rules(request)
        if not rules:
            logger.info("Job %s: không có bộ rule (BE gửi rỗng, không cấu hình mock) — bỏ qua kiểm tra", job_id)
            return
        report = self._rules.check(rules, request.house_type, request.categories, entities)
        results = self._findings.finalize(report.results)
        logger.info("Job %s: kiểm %d dòng tiêu chí (%s) — %s", job_id, report.coverage["linesApplicable"],
                    source, report.coverage["byStatus"])
        if inspector is not None:
            inspector.write_checks(_checks_payload(report, results, source, request, entities))

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


def _checks_payload(
    report: CheckReport, results: list[LineResult], source: str, request: DispatchRequest, entities: list[Entity]
) -> dict:
    """Dữ liệu tab "Kiểm tra" của viewer: một dòng / kết quả, kèm nội dung rule để người đọc."""
    rules = {r.rule_id: r for r in report.rules}
    rows = []
    for r in results:
        rule = rules[r.rule_id]
        rows.append({
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
        "houseType": request.house_type.value,
        "categories": [c.value for c in request.categories],
        "coverage": report.coverage,
        "entities": kinds,
        "rows": rows,
    }


def _bbox(polygon) -> list[float]:
    xs = [p.x for p in polygon.points]
    ys = [p.y for p in polygon.points]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
