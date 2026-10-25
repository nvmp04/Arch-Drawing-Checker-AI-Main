"""Đọc cấu trúc bộ hồ sơ (giai đoạn A): khung tên từng trang, tiêu đề hình / bảng, bảng viết tắt, đặc điểm hồ sơ.

Chỉ đọc bản vẽ — thuật toán cố định, KHÔNG phụ thuộc bộ tiêu chí, không diễn giải nghĩa (D-18). Kết quả là
mục lục để bước sau (định vị, diễn giải — AI) tìm tới đúng trang / bảng.
"""

from pydantic import BaseModel

from drawing_checker.common.geometry import Polygon


class TitleBlock(BaseModel):
    """Khung tên của một trang. Giá trị giữ nguyên chữ trên bản vẽ."""

    name: str | None = None  # TÊN BẢN VẼ - DRAWING NAME: "MẶT BẰNG HOÀN THIỆN SÀN TẦNG 1"
    number: str | None = None  # số hiệu bản vẽ: "PN2.DN FCC CD CD SH1 A 121 00 00"
    scale: str | None = None  # TỶ LỆ / SCALE: "1/100", "1/NTS"
    scale_denominator: int | None = None  # 100 cho "1/100"; None khi không theo tỉ lệ (NTS)
    item: str | None = None  # HẠNG MỤC - ITEM: "MẪU NHÀ SH1"
    project: str | None = None  # CÔNG TRÌNH - ĐỊA ĐIỂM / PROJECT - LOCATION
    phase: str | None = None  # GIAI ĐOẠN - PROJECT PHASE
    discipline: str | None = None  # BỘ MÔN - CONSULTANT: "KIẾN TRÚC ARCHITECTURAL"
    issued: str | None = None  # NGÀY PHÁT HÀNH - ISSUE DAY
    fields: dict[str, str] = {}  # mọi cặp nhãn → giá trị đọc được (kể cả nhãn chưa đặt tên trường)
    source: str = "margin"  # "margin" (chữ ngoài vùng hiển thị) | "page"


class DrawingView(BaseModel):
    """Một hình / bảng có tiêu đề trên trang (bản vẽ chính, ô chi tiết, keyplan, bảng)."""

    page_number: int
    title: str  # "MẶT ĐỨNG TRÍCH ĐOẠN A-B - TẦNG 1_TL:1/25", "BẢNG THỐNG KÊ CẤU TẠO SÀN"
    scale_denominator: int | None = None  # 25 cho "TL:1/25"
    polygon: Polygon  # khung của dòng tiêu đề (chưa tách vùng của cả hình — cần hình học)


class SheetInfo(BaseModel):
    page_number: int
    title_block: TitleBlock | None = None
    views: list[DrawingView] = []


class Abbreviation(BaseModel):
    """Một dòng của bảng viết tắt trong chính bộ hồ sơ (PN2 trang 2)."""

    abbr: str  # "BTCT"
    meaning: str  # "BÊ TÔNG CỐT THÉP"
    page_number: int
    polygon: Polygon  # khung chữ viết tắt + nghĩa


class DossierProfile(BaseModel):
    """Đặc điểm hồ sơ — chỉ những gì đọc thẳng được từ bản vẽ, chưa suy luận (vd. chưa quy "SH1" ra loại nhà)."""

    page_count: int
    items: list[str] = []  # HẠNG MỤC trong khung tên: ["MẪU NHÀ SH1"]
    project: str | None = None
    phase: str | None = None
    storeys: list[int] = []  # các tầng có nhãn cao độ "TẦNG n"
    has_basement: bool = False  # có nhãn cao độ "HẦM"
    has_attic: bool = False  # có nhãn cao độ "TUM"
    levels: dict[str, float] = {}  # khóa cao độ → mm (số ghi xuất hiện nhiều nhất): {"storey:1": 250, "roof": 11250}
    scales: list[str] = []  # các tỉ lệ khung tên
    pages_without_title_block: list[int] = []


class DocumentIndex(BaseModel):
    """Mục lục bộ hồ sơ: trang → khung tên + hình / bảng; bảng viết tắt; đặc điểm hồ sơ."""

    sheets: list[SheetInfo]
    abbreviations: list[Abbreviation] = []
    profile: DossierProfile
