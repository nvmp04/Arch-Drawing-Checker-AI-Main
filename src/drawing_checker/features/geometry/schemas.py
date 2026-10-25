"""Đối tượng hình học nhận từ nét vẽ (drawing-knowledge.md). Không chứa gì về câu tiêu chí (D-18)."""

from pydantic import BaseModel

from drawing_checker.common.geometry import Polygon


class TableCell(BaseModel):
    """Một ô của bảng (ô gộp: `row_span` / `col_span` > 1). Chỉ số 0-based, hàng từ trên xuống, cột từ trái sang."""

    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    polygon: Polygon  # khung ô, point trang đã xoay
    text_indices: list[int] = []  # chỉ số khối chữ (`DrawingPage.texts`) nằm trong ô, theo thứ tự đọc


class Table(BaseModel):
    """Bảng nhận từ lưới kẻ (drawing-knowledge.md §3.3): đường ngang + dọc cắt nhau tạo ô, có chữ trong ô."""

    page_number: int
    polygon: Polygon  # khung bao cả bảng
    rows: int
    cols: int
    cells: list[TableCell]  # theo thứ tự hàng → cột (ô gộp xếp theo ô góc trên-trái)
