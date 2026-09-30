"""Rule engine: so giá trị đã trích với ngưỡng. Chính xác tuyệt đối khi đầu vào đúng (D-10)."""

from drawing_checker.features.extraction.schemas import Entity
from drawing_checker.features.findings.schemas import LineResult
from drawing_checker.features.rules.schemas import CheckPlan


class RuleEvaluator:
    def evaluate(self, plan: CheckPlan, entities: list[Entity]) -> LineResult:
        raise NotImplementedError
