from drawing_checker.features.extraction.schemas import Entity
from drawing_checker.features.ingest.schemas import DrawingPage
from drawing_checker.features.sheets.schemas import SheetInfo


class ExtractionService:
    """v0: heuristic (regex + ghép theo tọa độ). v1: model trên đồ thị nét vẽ, train từ nhãn đã sửa."""

    def extract(self, page: DrawingPage, sheet: SheetInfo) -> list[Entity]:
        raise NotImplementedError
