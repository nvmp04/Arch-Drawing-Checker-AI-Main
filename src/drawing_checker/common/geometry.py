"""Mô hình hình học duy nhất của MAIN: Polygon (D-06).

Bounding box là Polygon 4 đỉnh với precision=bbox — không có kiểu BBox riêng.
Hệ tọa độ (Q-01, chốt 2026-10-19): nội bộ MAIN dùng point PDF của trang đang hiển thị (đã áp /Rotate),
gốc trên-trái; gửi BE quy đổi sang % 0–100 cùng trang — khớp BoundingBoxDto của BE (`findings.service`).
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
        return cls(points=[Point(x=x, y=y), Point(x=x + width, y=y), Point(x=x + width, y=y + height),
                           Point(x=x, y=y + height)], precision=Precision.BBOX)

    def bounding_box(self) -> tuple[float, float, float, float]:
        """(x, y, width, height) bao ngoài — để điền `boundingBox` cho BE (L-03)."""
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
