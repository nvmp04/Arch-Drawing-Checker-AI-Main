from drawing_checker.features.extraction.schemas import Entity
from drawing_checker.features.geometry.schemas import Table
from drawing_checker.features.geometry.tables import detect_tables
from drawing_checker.features.ingest.schemas import DrawingPage
from drawing_checker.features.sheets.schemas import DrawingView


class GeometryService:
    def tables(self, page: DrawingPage) -> list[Table]:
        """Bảng có lưới kẻ trên trang + chữ trong từng ô (drawing-knowledge.md §3.3). Cần `page.paths`."""
        return detect_tables(page.page_number, page.paths, page.texts, (page.width, page.height))

    def rooms(self, page: DrawingPage, view: DrawingView) -> list[Entity]:
        """Tường (khối hatch) → vùng kín → polygon phòng (approximate/exact) + tên phòng bên trong."""
        raise NotImplementedError

    def clear_width(self, room: Entity, dimensions: list[Entity]) -> Entity:
        """Chiều rộng lọt lòng, xác thực bằng đường kích thước cắt qua phòng."""
        raise NotImplementedError
