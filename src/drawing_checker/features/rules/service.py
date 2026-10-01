"""Chạy kiểm tra: lọc rule áp dụng → diễn giải → checker → kết quả + báo cáo độ phủ.

Điểm vào công khai của feature `rules` cho `analyses`.
"""

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel

from drawing_checker.common.enums import ChtkCategory, FindingStatus, HouseType
from drawing_checker.features.extraction.schemas import Entity
from drawing_checker.features.findings.schemas import LineResult
from drawing_checker.features.rules.checkers import GROUP_CHECKERS, LINE_CHECKERS, CheckContext
from drawing_checker.features.rules.interpreter import RuleInterpreter
from drawing_checker.features.rules.schemas import CheckPlan, RuleInput

UNSUPPORTED_REASON = "Chưa hỗ trợ kiểm tự động (chưa có checker cho dòng tiêu chí này)."


class CheckReport(BaseModel):
    rules: list[RuleInput]  # các rule áp dụng (sau lọc loại nhà + nhóm)
    results: list[LineResult]
    coverage: dict[str, int | dict[str, int]]
    notes: list[str] = []


class RulesService:
    def __init__(self, interpreter: RuleInterpreter | None = None) -> None:
        self._interpreter = interpreter or RuleInterpreter()

    def check(
        self,
        rules: list[RuleInput],
        house_type: HouseType,
        categories: list[ChtkCategory],
        entities: list[Entity],
    ) -> CheckReport:
        applicable = [r for r in rules if _applies(r, house_type, categories)]
        ctx = CheckContext.build(entities)
        results: list[LineResult] = []
        groups: dict[str, list[tuple[RuleInput, list[CheckPlan]]]] = {}
        supported_lines = 0

        for rule in applicable:
            plans = self._interpreter.interpret(rule)
            for plan in plans:
                if plan.checker is None:
                    results.append(LineResult(ruleId=rule.rule_id, lineIndex=plan.line_index,
                                              status=FindingStatus.UNKNOWN, confidence=0.0, reason=UNSUPPORTED_REASON))
                    continue
                supported_lines += 1
                if plan.checker in GROUP_CHECKERS:
                    group = groups.setdefault(plan.checker, [])
                    if not group or group[-1][0] is not rule:
                        group.append((rule, []))
                    group[-1][1].append(plan)
                else:
                    results.extend(LINE_CHECKERS[plan.checker](plan, rule, ctx))
        for name, rule_plans in groups.items():
            results.extend(GROUP_CHECKERS[name](rule_plans, ctx))

        total_lines = sum(len(r.requirement_lines) for r in applicable)
        coverage = {
            "rulesTotal": len(rules),
            "rulesApplicable": len(applicable),
            "linesApplicable": total_lines,
            "linesSupported": supported_lines,
            "linesUnsupported": total_lines - supported_lines,
            "byStatus": dict(Counter(r.status.value for r in results if r.reason != UNSUPPORTED_REASON)),
        }
        return CheckReport(rules=applicable, results=results, coverage=coverage)


def _applies(rule: RuleInput, house_type: HouseType, categories: list[ChtkCategory]) -> bool:
    if rule.house_types and house_type not in rule.house_types:
        return False
    if categories and rule.category is not None and rule.category not in categories:
        return False
    return True


def load_mock_rules(path: Path) -> list[RuleInput]:
    """Đọc JSON bộ tiêu chí do BE sinh từ Excel (docs/criteria-json.md) — MOCK khi BE gửi `rules: []` (v0)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    ruleset = data["data"][0] if "data" in data else data
    return [RuleInput.model_validate({**r, "ruleId": r["id"]}) for s in ruleset["sections"] for r in s["rules"]]
