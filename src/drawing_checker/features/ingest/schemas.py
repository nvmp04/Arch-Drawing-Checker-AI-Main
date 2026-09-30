"""Biểu diễn bản vẽ sau khi đọc PDF vector (không OCR — D-03).

Tọa độ nội bộ: point PDF của trang ĐANG HIỂN THỊ (đã áp /Rotate), gốc trên-trái, y hướng xuống.
Quy đổi sang hệ tọa độ trả BE (Q-01) làm ở tầng findings, không ở đây.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from drawing_checker.common.geometry import Polygon


class TextSpan(BaseModel):
    """Một lượt vẽ chữ trong PDF (thường là một cụm từ / một dòng ghi chú)."""

    text: str
    polygon: Polygon  # bbox của chữ
    font: str | None = None
    size: float | None = None
    rotation: float = 0.0  # độ, ngược chiều kim đồng hồ; chữ kích thước thường xoay 90°
    layer: str | None = None  # layer CAD (Optional Content), vd. "DETAILS|A-dim"


@dataclass(slots=True)
class VectorPath:
    """Một nét vẽ liền: đường gấp khúc, đa giác, vùng tô (hatch tường). Đường cong đã rời rạc hóa.

    Dataclass thay vì Pydantic: trang nặng ~317k nét, Pydantic tốn ~10 s/trang chỉ để dựng đối tượng.
    Dữ liệu thô nội bộ, không đi ra API — bằng chứng trả BE vẫn là Polygon (D-06).
    """

    points: list[tuple[float, float]]  # (x, y) point, trang đã xoay
    closed: bool
    filled: bool
    stroke_width: float | None = None
    color: str | None = None  # "#rrggbb" — màu nét (hoặc màu tô nếu chỉ tô)
    dashed: bool = False  # PDF xuất từ CAD thường vẽ nét đứt thành các đoạn rời → hiếm khi True
    layer: str | None = None  # layer CAD, vd. "xr-se|A-WALL-PATT"


class DrawingPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    page_number: int  # 1-based
    width: float  # point, trang đã xoay
    height: float
    rotation: int
    texts: list[TextSpan] = []
    paths: list[VectorPath] = []  # có thể rất lớn (tới ~316k nét/trang) — nạp lười qua load_paths
    timings: dict[str, int] = {}  # ms theo bước trích (textMs, pathsMs) — để đo hiệu năng


class DrawingDocument(BaseModel):
    page_count: int
    pages: list[DrawingPage] = []  # chỉ chữ; nét vẽ nạp riêng từng trang
