from drawing_checker.features.ingest.schemas import DrawingPage
from drawing_checker.features.sheets.schemas import SheetInfo


class SheetService:
    def analyze(self, page: DrawingPage) -> SheetInfo:
        """Phân loại trang (từ tiêu đề + khung tên) và tách khung nhìn kèm tỉ lệ."""
        raise NotImplementedError
