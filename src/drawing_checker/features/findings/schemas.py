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


class Applicability(str, Enum):
    APPLIES = "applies"
    NOT_APPLICABLE = "not-applicable"  # không áp dụng cho hồ sơ này — gửi kèm status "unknown" (Không xác định)
    UNKNOWN = "unknown"  # chưa kiểm được (chưa hỗ trợ / thiếu dữ liệu)


class BackendEvidence(BaseModel):
    """Một bằng chứng gửi BE: trang + bbox % (Q-01)."""

    page_number: int = Field(ge=1, alias="pageNumber")
    bounding_box: BoundingBox = Field(alias="boundingBox")
    role: EvidenceRole
    text: str | None = None

    model_config = {"populate_by_name": True}


class RuleSnapshot(BaseModel):
    """Bản chụp rule kèm mỗi finding — BE chưa lưu bộ tiêu chí (L-01) nên không tra được rule theo `ruleId`."""

    code: str | None = None
    parent_code: str | None = Field(default=None, alias="parentCode")
    title: str = ""
    requirement_line: str = Field(default="", alias="requirementLine")

    model_config = {"populate_by_name": True}


class RawFinding(BaseModel):
    """Payload gửi BE — `RawFindingV1` (integration-contract.md §5.3): một phần tử = một dòng tiêu chí."""

    main_result_id: str = Field(alias="mainResultId")  # "<jobId>:<ruleId>:<lineIndex>:<k>" — ghép dữ liệu huấn luyện
    rule_id: str = Field(alias="ruleId")
    line_index: int = Field(ge=0, alias="lineIndex")
    rule: RuleSnapshot
    status: FindingStatus  # không bao giờ APPROVED
    applicability: Applicability
    severity: FindingSeverity | None = None  # Q-09: MAIN không gửi, BE tự gán
    check_type: CheckType | None = Field(default=None, alias="checkType")  # D-08
    confidence: float = Field(ge=0, le=1)
    extracted_value: str | None = Field(default=None, alias="extractedValue")
    standard_value: str | None = Field(default=None, alias="standardValue")
    reason: str
    # Bằng chứng chính — None khi dòng không có bằng chứng định vị (không áp dụng, chưa hỗ trợ…).
    page_number: int | None = Field(default=None, ge=1, alias="pageNumber")
    bounding_box: BoundingBox | None = Field(default=None, alias="boundingBox")
    evidence: list[BackendEvidence] = []

    model_config = {"populate_by_name": True}
