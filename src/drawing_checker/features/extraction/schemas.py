"""Thực thể trích từ bản vẽ — đầu vào của rule engine và semantic. Đây là phần lõi AI (D-10)."""

from enum import Enum

from pydantic import BaseModel

from drawing_checker.common.geometry import Polygon


class EntityKind(str, Enum):
    LEVEL = "level"  # cao độ: "TẦNG 2 +4.450", "FFL +0.200", "SSL +0.150"
    DIMENSION = "dimension"  # đường kích thước + con số
    STAIR_FLIGHT = "stair-flight"  # "18 BẬC x 168"
    OPENING = "opening"  # cửa đi / cửa sổ: "2100w x 2800h", mã DR-01
    CALLOUT = "callout"  # ghi chú vật liệu / cấu tạo + đường dẫn tới vị trí
    ROOM = "room"  # tên phòng + polygon (từ geometry)
    TABLE_ROW = "table-row"  # dòng bảng thống kê
    FINISH = "finish"  # dòng bảng vật liệu hoàn thiện: "FC-01 | TRẦN CEMBOARD HOÀN THIỆN SƠN NƯỚC"


class Entity(BaseModel):
    kind: EntityKind
    page_number: int
    view_title: str | None = None
    label: str | None = None  # vd. "TẦNG 2", "DR-01", "Phòng khách"
    text: str | None = None
    value: float | None = None  # đã quy đổi mm (hoặc %)
    values: list[float] | None = None  # vd. rộng × cao
    unit: str | None = None
    polygon: Polygon
    confidence: float = 1.0
    layer: str | None = None
    attributes: dict[str, str | float | int] = {}  # dữ liệu riêng theo loại (vd. số bậc, cột bảng)
