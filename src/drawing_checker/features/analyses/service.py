"""Điều phối pipeline — feature duy nhất được phụ thuộc các feature khác (qua service công khai).

Thứ tự bước và nghĩa: docs/architecture.md §2, §5.
  extract   : ingest + sheets → báo pageCount
  ocr       : extraction thực thể số (không phải OCR)
  material  : semantic
  geometry  : geometry
  aggregate : rules.evaluator + findings → gửi toàn bộ kết quả

Hiện tại (hợp đồng BE v0): extract = tải PDF + ingest từng trang (tiến độ theo trang) → aggregate,
findings rỗng. BE cho phép bỏ qua bước giữa. Kết quả ingest xem ở viewer debug của job
(features/ingest/inspector.py, phục vụ tại /debug/inspect/) — chưa gửi gì về BE ngoài tiến độ.
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
from drawing_checker.features.ingest.inspector import IngestInspector
from drawing_checker.features.ingest.service import IngestError, IngestService, PageReader
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
    ) -> None:
        self._backend = backend
        self._fetcher = fetcher
        self._runner = runner
        self._ingest = ingest or IngestService()
        self._inspect_dir = inspect_dir  # None = không ghi viewer debug
        self._inspect_dpi = inspect_dpi
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
                    page_count = await self._ingest_pages(job_id, request, reader, inspector)
            except (PdfFetchError, IngestError) as exc:
                raise _StageFailed(str(exc)) from exc
            percent = 90
            await self._report(job_id, request, stage, AnalysisRunState.COMPLETED, percent, page_count=page_count)

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
    ) -> int:
        """Ingest lần lượt từng trang trong thread (trang nặng ~5 s CPU), báo tiến độ 10 → 90%."""
        total = reader.page_count
        dpi = self._inspect_dpi
        if inspector is not None:
            inspector.start(total, dpi)

        def process(page_number: int) -> None:
            page = reader.read(page_number)
            if inspector is not None:
                inspector.write_page(page, reader.render_jpeg(page_number, dpi) if dpi > 0 else None)
            # Chưa có bước sau dùng kết quả; `page` (có thể ~300k nét) được giải phóng ngay.

        await self._report(job_id, request, AnalysisStage.EXTRACT, AnalysisRunState.RUNNING, 10)
        for n in range(1, total + 1):
            await asyncio.to_thread(process, n)
            percent = 10 + round(80 * n / total)
            if percent < 90:
                await self._report(job_id, request, AnalysisStage.EXTRACT, AnalysisRunState.RUNNING, percent)
        return total

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
