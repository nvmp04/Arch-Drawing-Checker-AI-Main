"""Nhận bảng từ lưới kẻ (geometry/tables.py) + in bảng trong bản tóm tắt gửi AI."""

from pathlib import Path

import pytest

from drawing_checker.common.geometry import Polygon
from drawing_checker.features.geometry.service import GeometryService
from drawing_checker.features.geometry.tables import detect_tables
from drawing_checker.features.ingest.schemas import TextSpan, VectorPath
from drawing_checker.features.ingest.service import IngestService
from drawing_checker.features.semantic.digest import build_digest
from drawing_checker.features.sheets.schemas import DocumentIndex, DossierProfile

PDF = Path("D:/Downloads/tieuchuan/PN2.DN-Ban ve mau demo test AI.pdf")


def line(x0: float, y0: float, x1: float, y1: float) -> VectorPath:
    return VectorPath(points=[(x0, y0), (x1, y1)], closed=False, filled=False)


def rect(x0: float, y0: float, x1: float, y1: float) -> VectorPath:
    return VectorPath(points=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, filled=False)


def text(s: str, cx: float, cy: float) -> TextSpan:
    return TextSpan(text=s, polygon=Polygon.from_bbox(cx - 4, cy - 1.5, 8, 3), size=2.5)


def grid(xs: list[float], ys: list[float], skip_v: set[tuple[int, int]] = frozenset()) -> list[VectorPath]:
    """Lưới đủ nét; skip_v = {(cột đường dọc, hàng)} bỏ đoạn dọc → gộp hai ô ngang của hàng đó."""
    paths = [line(xs[0], y, xs[-1], y) for y in ys]
    for i, x in enumerate(xs):
        for j in range(len(ys) - 1):
            if (i, j) not in skip_v:
                paths.append(line(x, ys[j], x, ys[j + 1]))  # CAD hay cắt đường dọc thành từng đoạn ở giao điểm
    return paths


XS, YS = [0, 40, 120, 200], [0, 10, 20, 30, 40]


def test_grid_cells_and_text_assignment() -> None:
    texts = [text("KÝ HIỆU", 20, 5), text("MÔ TẢ", 80, 5), text("FC-01", 20, 15), text("TRẦN THẠCH CAO", 80, 15),
             text("FC-02", 20, 25), text("TRẦN GỖ", 80, 25), text("dòng 2 của ô", 80, 28), text("ngoài bảng", 300, 300)]
    tables = detect_tables(1, grid(XS, YS), texts)
    assert len(tables) == 1
    t = tables[0]
    assert (t.rows, t.cols) == (4, 3)
    by_pos = {(c.row, c.col): c for c in t.cells}
    assert by_pos[(1, 1)].text_indices == [3]
    assert by_pos[(2, 1)].text_indices == [5, 6]  # ô nhiều dòng giữ liền nhau, đúng thứ tự đọc
    assert all(7 not in c.text_indices for c in t.cells)


def test_merged_cell_spans_columns() -> None:
    # Hàng đầu không có đường dọc ở x=40 và x=120 → một ô tiêu đề trải 3 cột.
    paths = grid(XS, YS, skip_v={(1, 0), (2, 0)})
    texts = [text("BẢNG VẬT LIỆU", 100, 5), *(text(f"ô {r}{c}", (XS[c] + XS[c + 1]) / 2, (YS[r] + YS[r + 1]) / 2)
                                             for r in range(1, 4) for c in range(3))]
    t = detect_tables(1, paths, texts)[0]
    header = next(c for c in t.cells if c.row == 0)
    assert (header.col, header.col_span, header.text_indices) == (0, 3, [0])


def test_cells_drawn_as_rectangles() -> None:
    paths = [rect(XS[i], YS[j], XS[i + 1], YS[j + 1]) for i in range(3) for j in range(4)]
    texts = [text(f"A{r}{c}", (XS[c] + XS[c + 1]) / 2, (YS[r] + YS[r + 1]) / 2) for r in range(4) for c in range(3)]
    assert len(detect_tables(1, paths, texts)[0].cells) == 12


def test_rejects_sparse_or_numeric_grids() -> None:
    # Lưới lớn ít chữ (mặt bằng / mặt đứng) và lưới toàn số (dải kích thước) không phải bảng.
    big = grid([i * 10 for i in range(21)], [j * 10 for j in range(21)])
    sparse = [text("P. NGỦ", 15, 15), text("WC", 55, 55), text("BẾP", 95, 95), text("KHO", 135, 135)]
    assert detect_tables(1, big, sparse) == []
    numeric = [text(str(1000 + k), (XS[c] + XS[c + 1]) / 2, (YS[r] + YS[r + 1]) / 2)
               for k, (r, c) in enumerate((r, c) for r in range(4) for c in range(3))]
    assert detect_tables(1, grid(XS, YS), numeric) == []


def test_page_frame_area_is_not_a_cell() -> None:
    # Khung trang + khung tên: vùng vẽ lớn không phải ô; chữ trong vùng vẽ không bị gom vào bảng.
    frame = grid([0, 800, 1000], [0, 150, 300, 450, 600])
    texts = [text(f"KHUNG TÊN {j}", 900, 75 + 150 * j) for j in range(4)] + [text("MẶT BẰNG", 400, 300)]
    tables = detect_tables(1, frame, texts, page_size=(1000, 600))
    assert len(tables) == 1
    assert all(4 not in c.text_indices for c in tables[0].cells)


def test_digest_prints_table_rows_with_block_ids() -> None:
    texts = [text("KÝ HIỆU", 20, 5), text("MÔ TẢ", 80, 5), text("FC-01", 20, 15), text("TRẦN THẠCH CAO", 80, 15),
             text("FC-02", 20, 25), text("TRẦN GỖ", 80, 25), text("ghi chú ngoài", 300, 300)]
    tables = {1: detect_tables(1, grid(XS, YS), texts)}
    index = DocumentIndex(profile=DossierProfile(page_count=1), sheets=[], abbreviations=[])
    with_grid = build_digest([(1, texts)], index, tables=tables)
    assert "[BẢNG 1]" in with_grid.text
    assert "H2| C1: p1-2 FC-01 | C2: p1-3 TRẦN THẠCH CAO" in with_grid.text
    assert "p1-6 L- ghi chú ngoài" in with_grid.text  # chữ ngoài bảng vẫn in như cũ
    assert with_grid.stats["tables"] == 1
    plain = build_digest([(1, texts)], index)  # không có lưới → giữ nguyên cách cũ (mốc so sánh)
    assert "[BẢNG" not in plain.text and "p1-3 L- TRẦN THẠCH CAO" in plain.text


@pytest.mark.skipif(not PDF.exists(), reason="Không có PDF mẫu PN2 trên máy này")
@pytest.mark.parametrize(
    ("page", "row_texts"),
    [
        (3, ["FC-01", "TRẦN CEMBOARD HOÀN THIỆN SƠN NƯỚC MÀU TRẮNG"]),  # bảng vật liệu hoàn thiện trần
        (5, ["F2.2", "BAN CÔNG"]),  # bảng thống kê cấu tạo sàn (ô nhiều dòng)
        (47, ["KÍCH THƯỚC", "4800w x 3000h", "3700w x 3000h"]),  # bảng cửa
    ],
)
def test_pn2_tables(page: int, row_texts: list[str]) -> None:
    drawing = IngestService().load_paths(PDF, page)
    drawing.texts = IngestService().load_text(PDF, page).texts
    tables = GeometryService().tables(drawing)
    rows = {}
    for t_no, t in enumerate(tables):
        for c in t.cells:
            rows.setdefault((t_no, c.row), []).append(" ".join(drawing.texts[i].text for i in c.text_indices))
    assert any(all(any(want in cell for cell in cells) for want in row_texts) for cells in rows.values())


@pytest.mark.skipif(not PDF.exists(), reason="Không có PDF mẫu PN2 trên máy này")
def test_pn2_floor_table_merged_storey_cell() -> None:
    drawing = IngestService().load_paths(PDF, 5)
    drawing.texts = IngestService().load_text(PDF, 5).texts
    cells = [c for t in GeometryService().tables(drawing) for c in t.cells
             if any(drawing.texts[i].text.strip() == "TẦNG 2,3" for i in c.text_indices)]
    assert len(cells) == 1 and cells[0].row_span == 4  # ô "TẦNG 2,3" trải 4 hàng F2.1–F2.4
