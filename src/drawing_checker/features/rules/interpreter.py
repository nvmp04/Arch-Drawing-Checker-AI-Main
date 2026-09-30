"""Diễn giải: requirementLine → CheckPlan. Bước này tương lai có thể tách endpoint riêng + người duyệt (Q-07)."""

from drawing_checker.features.rules.schemas import CheckPlan, NormalizedValue, RuleInput


class RuleInterpreter:
    def interpret(self, rule: RuleInput) -> list[CheckPlan]:
        """Một rule → nhiều kế hoạch (mỗi requirementLine một, D-09)."""
        raise NotImplementedError

    def parse_value(self, raw: str) -> NormalizedValue:
        """'1.1m' | '150mm' | '2.8 x 5.6m' | '1.2m - 2.6m' | '18%' | '17, 18, 21' → NormalizedValue (Q-03)."""
        raise NotImplementedError
