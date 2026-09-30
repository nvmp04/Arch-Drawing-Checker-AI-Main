from drawing_checker.features.extraction.schemas import Entity
from drawing_checker.features.ingest.schemas import DrawingPage
from drawing_checker.features.sheets.schemas import DrawingView


class GeometryService:
    def rooms(self, page: DrawingPage, view: DrawingView) -> list[Entity]:
        """Tường (khối hatch) → vùng kín → polygon phòng (approximate/exact) + tên phòng bên trong."""
        raise NotImplementedError

    def clear_width(self, room: Entity, dimensions: list[Entity]) -> Entity:
        """Chiều rộng lọt lòng, xác thực bằng đường kích thước cắt qua phòng."""
        raise NotImplementedError
