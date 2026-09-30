"""Mô hình hình học duy nhất của MAIN: Polygon (D-06).

Bounding box là Polygon 4 đỉnh với precision=bbox — không có kiểu BBox riêng.
Hệ tọa độ: CHƯA CHỐT (docs/open-questions.md Q-01). Đề xuất: % 0–100 của trang đang hiển thị
(đã áp /Rotate), gốc trên-trái — khớp BoundingBoxDto của BE.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Precision(str, Enum):
    BBOX = "bbox"  # khung chữ nhật bao quanh — phần tử không quá quan trọng
    APPROXIMATE = "approximate"  # hình gần đúng; số liệu được xác thực bằng con số ghi trên bản vẽ
    EXACT = "exact"  # đúng hình dạng (vd. cần diện tích phòng)


class Point(BaseModel):
    x: float
    y: float


class Polygon(BaseModel):
    points: list[Point] = Field(min_length=3)
    precision: Precision

    @classmethod
    def from_bbox(cls, x: float, y: float, width: float, height: float) -> "Polygon":
        raise NotImplementedError

    def bounding_box(self) -> tuple[float, float, float, float]:
        """(x, y, width, height) bao ngoài — để điền `boundingBox` cho BE hiện tại (L-03)."""
        raise NotImplementedError
