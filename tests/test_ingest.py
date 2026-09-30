"""Ingest trên PDF tổng hợp: chữ + layer CAD (OCG), nét vẽ, trang xoay, PDF lỗi."""

from pathlib import Path

import pymupdf
import pytest

from drawing_checker.features.ingest.service import IngestError, IngestService

service = IngestService()
# Font chuẩn Helvetica không mã hóa được dấu tiếng Việt → dùng Arial của Windows nếu có.
ARIAL = Path("C:/Windows/Fonts/arial.ttf")
VN_TEXT = "TẦNG 2" if ARIAL.exists() else "TANG 2"


def build_pdf(tmp_path: Path, rotation: int = 0) -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    dim = doc.add_ocg("A-dim")
    wall = doc.add_ocg("A-WALL-PATT")
    page.insert_text((50, 100), "FFL +0.200", fontsize=10, oc=dim)
    font = {"fontname": "arial", "fontfile": str(ARIAL)} if ARIAL.exists() else {}
    page.insert_text((50, 200), VN_TEXT, fontsize=12, **font)
    page.insert_text((300, 250), "4650", fontsize=8, rotate=90, oc=dim)
    page.insert_text((1000, 1000), "ngoài trang", fontsize=8)  # nằm ngoài khổ trang → bỏ
    page.draw_line((10, 10), (110, 10), oc=wall)
    page.draw_rect(pymupdf.Rect(150, 150, 250, 220), color=None, fill=(1, 0, 0), oc=wall)  # chỉ tô, không viền
    page.draw_bezier((10, 50), (40, 20), (70, 80), (100, 50))
    if rotation:
        page.set_rotation(rotation)
    path = tmp_path / "sample.pdf"
    doc.save(path)
    return path


def test_open_extracts_texts_with_layers(tmp_path: Path) -> None:
    doc = service.open(build_pdf(tmp_path))
    assert doc.page_count == 1
    page = doc.pages[0]
    assert (page.width, page.height, page.rotation) == (400, 300, 0)
    by_text = {t.text: t for t in page.texts}
    assert set(by_text) == {"FFL +0.200", VN_TEXT, "4650"}  # dấu tiếng Việt giữ nguyên, bỏ chữ ngoài trang
    assert by_text["FFL +0.200"].layer == "A-dim"
    assert by_text[VN_TEXT].layer is None
    assert by_text["4650"].rotation == 90
    ffl = by_text["FFL +0.200"].polygon
    assert ffl.precision == "bbox" and len(ffl.points) == 4
    assert 49 <= ffl.points[0].x <= 51 and ffl.points[0].y < 100 < ffl.points[2].y  # gốc trên-trái, baseline y=100


def test_load_paths(tmp_path: Path) -> None:
    page = service.load_paths(build_pdf(tmp_path), 1)
    assert page.texts == []
    line = next(p for p in page.paths if p.points == [(10, 10), (110, 10)])
    assert line.layer == "A-WALL-PATT" and not line.closed and not line.filled
    rect = next(p for p in page.paths if p.filled)
    assert rect.closed and rect.color == "#ff0000" and rect.layer == "A-WALL-PATT"
    assert {(round(x), round(y)) for x, y in rect.points} == {(150, 150), (250, 150), (250, 220), (150, 220)}
    curve = next(p for p in page.paths if p.points[0] == (10, 50))
    assert len(curve.points) == 9 and curve.points[-1] == pytest.approx((100, 50))  # 8 đoạn thẳng


def test_rotated_page_uses_displayed_coordinates(tmp_path: Path) -> None:
    pdf = build_pdf(tmp_path, rotation=90)
    page = service.open(pdf).pages[0]
    assert (page.width, page.height, page.rotation) == (300, 400, 90)
    ffl = next(t for t in page.texts if t.text == "FFL +0.200")
    for p in ffl.polygon.points:
        assert 0 <= p.x <= 300 and 0 <= p.y <= 400
    assert ffl.rotation == 270  # chữ ngang trên trang xoay 90° hiện thành chữ dọc
    line = next(p for p in service.load_paths(pdf, 1).paths if p.layer == "A-WALL-PATT" and not p.filled)
    xs = {round(x) for x, _ in line.points}
    assert len(xs) == 1  # đường ngang trở thành đường dọc


def test_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.7 garbage")
    with pytest.raises(IngestError, match="Không đọc được"):
        service.open(bad)
    with pytest.raises(IngestError, match="không tồn tại"):
        service.load_paths(build_pdf(tmp_path), 2)
