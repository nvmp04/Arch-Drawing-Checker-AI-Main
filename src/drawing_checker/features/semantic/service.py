"""So khớp tiêu chí dạng chữ với ghi chú trên bản vẽ. Local: từ khóa + so số → embedding + phân loại (D-10)."""

from drawing_checker.features.extraction.schemas import Entity
from drawing_checker.features.findings.schemas import LineResult
from drawing_checker.features.rules.schemas import CheckPlan


class SemanticService:
    def retrieve(self, plan: CheckPlan, callouts: list[Entity]) -> list[Entity]:
        """Tìm ghi chú liên quan (ô chi tiết có tiêu đề khớp, nội dung gần nghĩa)."""
        raise NotImplementedError

    def judge(self, plan: CheckPlan, candidates: list[Entity]) -> LineResult:
        """Phù hợp → pass · mâu thuẫn → fail/warning · không thấy → unknown."""
        raise NotImplementedError
