"""Diễn giải: requirementLine → CheckPlan. Bước này tương lai có thể tách endpoint riêng + người duyệt (Q-07).

Hiện tại là MOCK: chọn checker theo bảng khai báo `plan_table.PLAN_TABLE` (không NLP). Bộ diễn giải thật
sau này chỉ cần sinh ra cùng `CheckPlan` — lõi so ngưỡng và các checker giữ nguyên.
"""

import re

from drawing_checker.features.rules.plan_table import PLAN_TABLE, rule_key
from drawing_checker.features.rules.schemas import CheckPlan, NormalizedValue, RuleInput

_NUM = r"\d+(?:[.,]\d+)?"
_UNIT = r"(mm|cm|m|%)?"


class ValueParseError(ValueError):
    pass


class RuleInterpreter:
    def interpret(self, rule: RuleInput) -> list[CheckPlan]:
        """Một rule → nhiều kế hoạch (mỗi requirementLine một, D-09). Dòng không có trong bảng → checker None."""
        entries = PLAN_TABLE.get(rule_key(rule), {})
        plans = []
        for index, text in enumerate(rule.requirement_lines):
            entry = entries.get(index) or entries.get("*")
            value = None
            if entry and rule.value:
                try:
                    value = self.parse_value(rule.value)
                except ValueParseError:
                    value = None
            plans.append(
                CheckPlan(
                    rule_id=rule.rule_id,
                    line_index=index,
                    text=text,
                    operator=rule.operator,
                    value=value,
                    checker=entry["checker"] if entry else None,
                    params=entry.get("params", {}) if entry else {},
                    target=entry.get("target") if entry else None,
                    attribute=entry.get("attribute") if entry else None,
                    note=entry.get("note") if entry else None,
                )
            )
        return plans

    def parse_value(self, raw: str) -> NormalizedValue:
        """'1.1m' | '150mm' | '2.8 x 5.6m' | '1.2m - 2.6m' | '18%' | '17, 18, 21' → NormalizedValue (Q-03)."""
        text = raw.strip().lower().replace("×", "x")

        m = re.fullmatch(rf"({_NUM})\s*{_UNIT}\s*x\s*({_NUM})\s*{_UNIT}", text)
        if m:  # cặp kích thước, đơn vị có thể chỉ ghi ở số sau
            unit = m.group(4) or m.group(2) or ""
            return _value(unit, raw, pair=[_to_base(m.group(1), m.group(2) or unit), _to_base(m.group(3), unit)])

        m = re.fullmatch(rf"({_NUM})\s*{_UNIT}\s*[-–]\s*({_NUM})\s*{_UNIT}", text)
        if m:  # khoảng
            unit = m.group(4) or m.group(2) or ""
            return _value(unit, raw, min=_to_base(m.group(1), m.group(2) or unit), max=_to_base(m.group(3), unit))

        if "," in text and re.fullmatch(r"\d+(\s*,\s*\d+)+", text):  # danh sách số nguyên
            return _value("", raw, options=[float(x) for x in text.split(",")])

        m = re.fullmatch(rf"({_NUM})\s*{_UNIT}", text)
        if m:
            unit = m.group(2) or ""
            v = _to_base(m.group(1), unit)
            return _value(unit, raw, min=v, max=v)

        raise ValueParseError(f"Không phân tích được giá trị {raw!r}")


def _to_base(number: str, unit: str | None) -> float:
    """Độ dài → mm; % và số đếm giữ nguyên."""
    v = float(number.replace(",", "."))
    return {"m": v * 1000, "cm": v * 10}.get(unit or "", v)


def _value(unit: str, raw: str, **kw: object) -> NormalizedValue:
    base_unit = "mm" if unit in ("m", "cm", "mm") else unit
    return NormalizedValue(unit=base_unit, raw=raw, **kw)
