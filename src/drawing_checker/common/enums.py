"""Enum miền — giá trị khớp từng ký tự với BE (`src/common/enums`) và FE (`shared/constants/enums.ts`)."""

from enum import Enum


class FindingStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"  # dấu hiệu lệch nhưng chưa chắc / dưới ngưỡng tin cậy
    PENDING = "pending"  # cần người thẩm định xem
    APPROVED = "approved"  # CHỈ người xác nhận — MAIN không bao giờ sinh
    UNKNOWN = "unknown"  # không trích xuất được dữ liệu


class FindingSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CheckType(str, Enum):
    """Tồn tại nhưng CHƯA hiện thực (D-08): một rule có thể chứa nhiều loại."""

    A = "A"  # đối chiếu số đo
    B = "B"  # đối chiếu vật liệu / thông số
    C = "C"  # phân tích hình học
    D = "D"  # phán đoán chủ quan


class ChtkCategory(str, Enum):
    FACADE = "facade"  # 1.x
    DIMENSION = "dimension"  # 2.x
    STAIR_RAMP = "stair-ramp"  # 3.x
    STRUCTURE = "structure"  # 4.x
    FINISHING = "finishing"  # 5.x


class HouseType(str, Enum):
    SHOPHOUSE = "shophouse"
    TOWNHOUSE = "townhouse"
    SEMI_VILLA = "semi-villa"
    SINGLE_VILLA = "single-villa"
    SHOP_VILLA = "shop-villa"


class ComparisonOperator(str, Enum):
    GTE = "gte"
    LTE = "lte"
    EQ = "eq"
    BETWEEN = "between"
    IN_LIST = "in-list"
    PATTERN = "pattern"
    REQUIRED = "required"
    FORBIDDEN = "forbidden"


class AnalysisStage(str, Enum):
    """5 bước tiến độ của BE/FE. Nghĩa thực tế trong MAIN: docs/architecture.md §5."""

    EXTRACT = "extract"
    OCR = "ocr"  # MAIN: trích thực thể số — không phải OCR
    MATERIAL = "material"
    GEOMETRY = "geometry"
    AGGREGATE = "aggregate"


class AnalysisRunState(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
