"""Đọc cấu trúc hồ sơ (giai đoạn A): khung tên, tiêu đề hình / bảng, bảng viết tắt, đặc điểm hồ sơ."""

from pathlib import Path

import pytest

from drawing_checker.common.geometry import Point, Polygon, Precision
from drawing_checker.features.extraction.service import ExtractionService
from drawing_checker.features.ingest.schemas import DrawingPage, TextSpan
from drawing_checker.features.ingest.service import IngestService
from drawing_checker.features.sheets.service import SheetService, expand_abbreviations

PDF = Path("D:/Downloads/tieuchuan/PN2.DN-Ban ve mau demo test AI.pdf")


def span(text: str, x: float, y: float, w: float = 40, h: float = 6, size: float = 6.0) -> TextSpan:
    pts = [Point(x=x, y=y), Point(x=x + w, y=y), Point(x=x + w, y=y + h), Point(x=x, y=y + h)]
    return TextSpan(text=text, polygon=Polygon(points=pts, precision=Precision.BBOX), size=size)


def title_block_margin() -> list[TextSpan]:
    """Khung tên dạng cột ở mép phải như PN2 (nằm ngoài vùng hiển thị): nhãn nhỏ, giá trị ngay dưới."""
    return [
        span("HẠNG MỤC - ITEM", 1449, 774, 42, 5, 4.8), span("MẪU NHÀ SH1", 1515, 786, 43, 6, 6.3),
        span("MẪU NHÀ SH1", 1515, 786, 43, 6, 6.3),  # CAD xuất trùng, vẽ đè
        span("GIAI ĐOẠN - PROJECT PHASE:", 1449, 844, 70, 5, 4.8), span("HỒ SƠ THIẾT KẾ THI CÔNG", 1495, 856, 84, 6, 6.3),
        span("TÊN BẢN VẼ - DRAWING NAME", 1449, 873, 71, 5, 4.8),
        span("MẶT BẰNG HOÀN THIỆN SÀN TẦNG 1", 1450, 915, 173, 10, 9.5),
        span("CHỦ NHIỆM DỰ ÁN - PROJECT MANAGER:", 1449, 972, 98, 5, 4.8), span("HOÀNG THỊ BÍCH LIÊN", 1451, 983, 69, 6, 6.3),
        span("NGÀY PHÁT HÀNH - ISSUE DAY:", 1537, 1108, 73, 5, 4.8), span("TỶ LỆ / SCALE:", 1451, 1109, 35, 5, 4.8),
        span("2026", 1571, 1117, 14, 6, 6.3), span("1/100", 1502, 1118, 16, 6, 6.3),
        span("PN2.DN", 1463, 1140, 24, 6, 6.3), span("CD", 1519, 1140, 10, 6, 6.3), span("CD", 1520, 1140, 9, 6, 6.3),
        span("SH1 A 121", 1550, 1140, 49, 6, 6.3),
    ]


def plan_page() -> DrawingPage:
    texts = [span(f"{i * 100}", 100 + i * 40, 300, 20, 6, 7.0) for i in range(12)]  # chữ thường (số kích thước)
    texts += [span("MẶT BẰNG KIẾN TRÚC TẦNG 1 _ TL:1/50", 579, 823, 300, 14, 15.8),
              span("CHI TIẾT PHỄU THU NƯỚC SÀN MÁI- BAN", 1135, 509, 260, 11, 11.9),
              span("CÔNG-SÂN THƯỢNG", 1135, 526, 120, 11, 11.9),
              span("MÔ TẢ", 900, 400, 40, 11, 11.9)]  # đầu cột bảng ngắn → không phải tiêu đề
    return DrawingPage(page_number=9, width=1445, height=1162, rotation=0, texts=texts, margin_texts=title_block_margin())


def abbreviation_page() -> DrawingPage:
    texts = [span("VIẾT TẮT / ABBREVIATIONS", 213, 227, 120, 8, 8.0), span("CHÚ THÍCH KÝ HIỆU / SIGN NOTES", 819, 228, 150, 8, 8.0)]
    rows = [("AC", "ĐIỀU HÒA KHÔNG KHÍ"), ("BTCT", "BÊ TÔNG CỐT THÉP"), ("BVKC", "BẢN VẼ KẾT CẤU"), ("DR", "CỬA ĐI"), ("MIN", "TỐI THIỂU")]
    for i, (abbr, meaning) in enumerate(rows):
        y = 380 + 22.6 * i
        texts += [span(abbr, 212, y, 22, 7, 7.0), span(meaning, 340, y + 0.5, 90, 7, 7.0)]
    rows2 = [("FW", "PHỂU THU NƯỚC SÀN"), ("FFL", "CAO ĐỘ SÀN HOÀN THIỆN"), ("SSL", "CAO ĐỘ SÀN KẾT CẤU"), ("NTS", "KHÔNG CÓ TỈ LỆ")]
    for i, (abbr, meaning) in enumerate(rows2):
        y = 288 + 22.6 * i
        texts += [span(abbr, 514, y, 22, 7, 7.0), span(meaning, 642, y + 1, 90, 7, 7.0)]
    texts.append(span("RANH ĐẤT", 823, 288, 40, 7, 7.0))  # cột của bảng ký hiệu bên cạnh — không phải nghĩa của FW
    return DrawingPage(page_number=2, width=1445, height=1162, rotation=0, texts=texts)


def test_title_block_fields_from_margin_text() -> None:
    tb = SheetService().analyze(plan_page()).title_block
    assert tb is not None and tb.source == "margin"
    assert tb.name == "MẶT BẰNG HOÀN THIỆN SÀN TẦNG 1"
    assert (tb.scale, tb.scale_denominator, tb.issued) == ("1/100", 100, "2026")
    assert tb.item == "MẪU NHÀ SH1" and tb.phase == "HỒ SƠ THIẾT KẾ THI CÔNG"
    assert tb.number == "PN2.DN CD SH1 A 121"  # chữ vẽ đè hai lần chỉ lấy một


def test_view_titles_with_scale_and_wrapped_lines() -> None:
    views = {v.title: v.scale_denominator for v in SheetService().analyze(plan_page()).views}
    assert views == {"MẶT BẰNG KIẾN TRÚC TẦNG 1 _ TL:1/50": 50,
                     "CHI TIẾT PHỄU THU NƯỚC SÀN MÁI- BAN CÔNG-SÂN THƯỢNG": None}


def test_abbreviation_table_two_column_groups() -> None:
    table = {a.abbr: a.meaning for a in SheetService().abbreviations(abbreviation_page())}
    assert table["BTCT"] == "BÊ TÔNG CỐT THÉP" and table["MIN"] == "TỐI THIỂU"
    assert table["FW"] == "PHỂU THU NƯỚC SÀN"  # không lấy nhầm "RANH ĐẤT" của bảng bên cạnh
    assert len(table) == 9


def test_expand_abbreviations_keeps_codes() -> None:
    abbrs = SheetService().abbreviations(abbreviation_page())
    assert expand_abbreviations("SÀN BTCT( xem BVKC)", abbrs) == "SÀN BÊ TÔNG CỐT THÉP( xem BẢN VẼ KẾT CẤU)"
    assert expand_abbreviations("LƯỚI THÉP D6@200, DÀY MIN 50mm", abbrs) == "LƯỚI THÉP D6@200, DÀY TỐI THIỂU 50mm"
    assert expand_abbreviations("DR-01 · CT-FW · A.FX.301", abbrs) == "DR-01 · CT-FW · A.FX.301"  # mã không bị thay


def test_profile_from_title_blocks_and_levels() -> None:
    page = plan_page()
    section = DrawingPage(page_number=38, width=1445, height=1162, rotation=0, texts=[
        span(label, 1380, y, 30, 7, 7.0) for label, y in (("TẦNG 1", 748), ("TẦNG 2", 510), ("TẦNG 3", 317), ("TẦNG 4", 123), ("MÁI", 160))
    ] + [span(v, 1385, y + 11, 30, 7, 7.0) for v, y in (("+0.250", 748), ("+4.450", 510), ("+7.850", 317), ("+11.250", 123), ("+11.250", 160))])
    service = SheetService()
    entities = [e for p in (page, section) for e in ExtractionService().extract(p)]
    index = service.build_index([service.analyze(page), service.analyze(section)], [], entities)
    assert index.profile.items == ["MẪU NHÀ SH1"]
    assert index.profile.storeys == [1, 2, 3]  # "TẦNG 4" trùng cao độ mái → là mái
    assert index.profile.pages_without_title_block == [38]


@pytest.mark.skipif(not PDF.exists(), reason="Không có PDF mẫu PN2 trên máy này")
def test_sample_pdf_document_index() -> None:
    doc = IngestService().open(PDF)
    service = SheetService()
    sheets = [service.analyze(p) for p in doc.pages]
    abbrs = [a for p in doc.pages for a in service.abbreviations(p)]
    index = service.build_index(sheets, abbrs, [e for p in doc.pages for e in ExtractionService().extract(p)])
    names = {s.page_number: s.title_block.name for s in index.sheets if s.title_block}
    assert len(names) == 48
    assert names[5] == "CHI TIẾT CẤU TẠO ĐIỂN HÌNH - 2" and names[13] == "MẶT BẰNG CHỐNG MỐI"
    assert names[18] == "MẶT BẰNG HOÀN THIỆN SÀN TẦNG 1" and names[47] == "BẢNG THỐNG KÊ CỬA - 01"
    assert index.sheets[17].title_block.scale == "1/100"
    table = {a.abbr: a.meaning for a in index.abbreviations}
    assert len(table) >= 50 and table["BTCT"] == "BÊ TÔNG CỐT THÉP" and table["FW"] == "PHỂU THU NƯỚC SÀN"
    assert {v.title for v in index.sheets[4].views} >= {"BẢNG THỐNG KÊ CẤU TẠO SÀN", "QUY ĐỊNH TƯỜNG XÂY"}
    assert ("MẶT ĐỨNG TRÍCH ĐOẠN A-B - TẦNG 1_TL:1/25", 25) in {(v.title, v.scale_denominator) for v in index.sheets[30].views}
    assert index.profile.items == ["MẪU NHÀ SH1"] and index.profile.storeys == [1, 2, 3]
