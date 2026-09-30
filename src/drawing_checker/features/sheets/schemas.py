"""Hiểu tờ bản vẽ: loại trang, các khung nhìn (ô chi tiết) và tỉ lệ của từng khung."""

from enum import Enum

from pydantic import BaseModel

from drawing_checker.common.geometry import Polygon


class PageKind(str, Enum):
    FLOOR_PLAN = "floor-plan"  # mặt bằng kiến trúc / kích thước / hoàn thiện / trần / tường
    ELEVATION = "elevation"  # mặt đứng, mặt đứng trích đoạn
    SECTION = "section"  # mặt cắt
    DETAIL = "detail"  # chi tiết cấu tạo (nhiều ô trên một trang)
    STAIR = "stair"  # mặt bằng / mặt cắt thang
    SCHEDULE = "schedule"  # bảng thống kê, định vị cửa đi – cửa sổ
    SITE = "site"  # mặt bằng xây dựng, keyplan
    GENERAL = "general"  # bìa, ghi chú chung, ký hiệu
    UNKNOWN = "unknown"


class DrawingView(BaseModel):
    """Một khung nhìn trên trang: bản vẽ chính, ô chi tiết, keyplan, bảng."""

    page_number: int
    title: str | None = None  # vd. "CHI TIẾT CHÂN TƯỜNG HÀNG RÀO"
    scale: float | None = None  # mẫu số tỉ lệ: 50 cho TL 1/50
    region: Polygon


class SheetInfo(BaseModel):
    page_number: int
    kind: PageKind
    title: str | None = None
    views: list[DrawingView] = []
