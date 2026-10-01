from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Response, status

from drawing_checker.common.security import require_service_token
from drawing_checker.config import get_settings
from drawing_checker.features.analyses.schemas import AnalysisStatus, DispatchRequest, DispatchResult
from drawing_checker.features.analyses.service import AnalysesService, JobNotFound
from drawing_checker.infrastructure.backend_client import BackendClient
from drawing_checker.infrastructure.job_runner import JobRunner
from drawing_checker.infrastructure.pdf_fetcher import PdfFetcher

router = APIRouter(prefix="/v1/analyses", tags=["analyses"], dependencies=[Depends(require_service_token)])


@lru_cache
def get_analyses_service() -> AnalysesService:
    """Một instance cho cả process — giữ danh sách job đang chạy (PoC, in-memory)."""
    settings = get_settings()
    return AnalysesService(
        backend=BackendClient(settings.callback_token),
        fetcher=PdfFetcher(settings.work_dir),
        runner=JobRunner(),
        inspect_dir=settings.inspect_dir if settings.inspect_enabled else None,
        inspect_dpi=settings.inspect_dpi,
        mock_ruleset=settings.mock_ruleset,
        confidence_threshold=settings.confidence_threshold,
    )


def _job_not_found(job_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "JOB_NOT_FOUND", "message": f"Không có job {job_id}"},
    )


@router.post("", response_model=DispatchResult, response_model_by_alias=True, status_code=status.HTTP_202_ACCEPTED)
async def dispatch_analysis(
    request: DispatchRequest, service: AnalysesService = Depends(get_analyses_service)
) -> DispatchResult:
    """BE gọi khi tạo hồ sơ / chạy lại (AiClientService.dispatchAnalysis). Trả ngay, việc chạy nền."""
    return await service.dispatch(request)


@router.get("/{external_job_id}", response_model=AnalysisStatus, response_model_by_alias=True)
async def get_analysis(
    external_job_id: str, service: AnalysesService = Depends(get_analyses_service)
) -> AnalysisStatus:
    """Xem trạng thái (debug / đối soát)."""
    try:
        return await service.get_status(external_job_id)
    except JobNotFound:
        raise _job_not_found(external_job_id) from None


@router.delete("/{external_job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_analysis(external_job_id: str, service: AnalysesService = Depends(get_analyses_service)) -> Response:
    """Ứng với AiClientService.cancelAnalysis. BE chấp nhận cả 204 lẫn 404."""
    try:
        await service.cancel(external_job_id)
    except JobNotFound:
        raise _job_not_found(external_job_id) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
