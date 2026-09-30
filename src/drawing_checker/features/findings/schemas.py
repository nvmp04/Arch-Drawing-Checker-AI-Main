"""Kết quả của MAIN: theo requirementLine (D-09), kèm bằng chứng Polygon (D-06)."""

from enum import Enum

from pydantic import BaseModel, Field

from drawing_checker.common.enums import CheckType, FindingSeverity, FindingStatus
from drawing_checker.common.geometry import Polygon


class EvidenceRole(str, Enum):
    SUBJECT = "subject"  # đối tượng được kiểm (phòng, cửa, bậc thang…)
    MEASUREMENT = "measurement"  # con số ghi trên bản vẽ làm căn cứ
    ANNOTATION = "annotation"  # ghi chú vật liệu / cấu tạo
    REGION = "region"  # vùng cần người xem (vd. tiêu chí chủ quan)


class Evidence(BaseModel):
    page_number: int = Field(ge=1, alias="pageNumber")  # 1-based, khớp BE
    polygon: Polygon
    role: EvidenceRole
    text: str | None = None
    measured_value: float | None = Field(default=None, alias="measuredValue")
    unit: str | None = None

    model_config = {"populate_by_name": True}


class LineResult(BaseModel):
    """Kết quả nội bộ của một dòng yêu cầu."""

    rule_id: str = Field(alias="ruleId")
    line_index: int = Field(ge=0, alias="lineIndex")
    status: FindingStatus  # không bao giờ APPROVED
    confidence: float = Field(ge=0, le=1)
    reason: str
    extracted_value: str | None = Field(default=None, alias="extractedValue")
    standard_value: str | None = Field(default=None, alias="standardValue")
    evidence: list[Evidence] = []

    model_config = {"populate_by_name": True}


class BoundingBox(BaseModel):
    """Khớp BoundingBoxDto của BE: % 0–100, trang đã xoay, gốc trên-trái."""

    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    width: float = Field(ge=0, le=100)
    height: float = Field(ge=0, le=100)


class RawFinding(BaseModel):
    """Payload gửi BE. Các trường BE hiện có + trường MAIN đề xuất thêm (L-02, L-03, L-04)."""

    rule_id: str = Field(alias="ruleId")
    status: FindingStatus
    severity: FindingSeverity | None = None  # BE đang bắt buộc — Q-09
    extracted_value: str = Field(alias="extractedValue")
    standard_value: str = Field(alias="standardValue")
    confidence: float = Field(ge=0, le=1)
    check_type: CheckType | None = Field(default=None, alias="checkType")  # D-08
    page_number: int = Field(ge=1, alias="pageNumber")
    bounding_box: BoundingBox = Field(alias="boundingBox")
    # Đề xuất thêm — BE chưa có:
    line_index: int | None = Field(default=None, alias="lineIndex")
    reason: str | None = None
    evidence: list[Evidence] = []

    model_config = {"populate_by_name": True}
