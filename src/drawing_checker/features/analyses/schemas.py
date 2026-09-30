"""Hợp đồng BE ↔ MAIN — mirror khung BE (ai-client.service.ts, analysis-callback.dto.ts). Xem docs/integration-contract.md."""

from pydantic import BaseModel, Field

from drawing_checker.common.enums import AnalysisRunState, AnalysisStage, ChtkCategory, HouseType
from drawing_checker.features.findings.schemas import RawFinding
from drawing_checker.features.rules.schemas import RuleInput


class DispatchRequest(BaseModel):
    """BE → MAIN: `AiClientService.dispatchAnalysis`."""

    review_id: str = Field(alias="reviewId")
    pdf_url: str = Field(alias="pdfUrl")  # URL có chữ ký, MAIN tự tải
    house_type: HouseType = Field(alias="houseType")  # người dùng chọn ở form FE (Q-02)
    categories: list[ChtkCategory]
    rules: list[RuleInput]
    callback_url: str = Field(alias="callbackUrl")

    model_config = {"populate_by_name": True}


class DispatchResult(BaseModel):
    external_job_id: str = Field(alias="externalJobId")
    stage: AnalysisStage

    model_config = {"populate_by_name": True}


class AnalysisCallback(BaseModel):
    """MAIN → BE: POST /internal/analysis/callback (x-internal-token). Idempotent theo (reviewId, stage)."""

    review_id: str = Field(alias="reviewId")
    external_job_id: str = Field(alias="externalJobId")
    stage: AnalysisStage
    state: AnalysisRunState
    percent: int = Field(ge=0, le=100)
    page_count: int | None = Field(default=None, ge=1, alias="pageCount")
    findings: list[RawFinding] | None = None
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = {"populate_by_name": True}


class AnalysisStatus(BaseModel):
    external_job_id: str = Field(alias="externalJobId")
    review_id: str = Field(alias="reviewId")
    stage: AnalysisStage
    state: AnalysisRunState
    percent: int

    model_config = {"populate_by_name": True}
