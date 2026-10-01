"""Rule engine lõi: so giá trị đã trích với ngưỡng. Hàm thuần, không chứa nghiệp vụ (D-10).

Chính xác tuyệt đối khi đầu vào đúng — độ tin cậy của kết quả do bước trích xuất quyết định, không phải ở đây.
"""

from drawing_checker.common.enums import ComparisonOperator
from drawing_checker.features.rules.schemas import NormalizedValue


class UnsupportedComparison(ValueError):
    pass


def compare(operator: ComparisonOperator | None, standard: NormalizedValue, measured: float) -> bool:
    """measured (cùng đơn vị cơ sở với standard) có thỏa ngưỡng không."""
    if operator == ComparisonOperator.GTE and standard.min is not None:
        return measured >= standard.min
    if operator == ComparisonOperator.LTE and standard.max is not None:
        return measured <= standard.max
    if operator == ComparisonOperator.BETWEEN and standard.min is not None and standard.max is not None:
        return standard.min <= measured <= standard.max
    if operator == ComparisonOperator.IN_LIST and standard.options:
        return any(abs(measured - option) < 1e-9 for option in standard.options)
    raise UnsupportedComparison(f"Không so được toán tử {operator} với giá trị {standard.raw!r}")


def at_threshold(operator: ComparisonOperator | None, standard: NormalizedValue, measured: float) -> bool:
    """Đạt nhưng đúng bằng ngưỡng — ghi chú 'sát ngưỡng' để người xem lưu ý."""
    bound = standard.min if operator == ComparisonOperator.GTE else standard.max
    return operator in (ComparisonOperator.GTE, ComparisonOperator.LTE) and bound is not None and measured == bound


def describe(operator: ComparisonOperator | None, standard: NormalizedValue) -> str:
    """Chuỗi ngưỡng cho người đọc, vd. '≥ 150 mm', '∈ {17, 18, 21}'."""
    unit = f" {standard.unit}" if standard.unit else ""
    if operator == ComparisonOperator.GTE:
        return f"≥ {_fmt(standard.min)}{unit}"
    if operator == ComparisonOperator.LTE:
        return f"≤ {_fmt(standard.max)}{unit}"
    if operator == ComparisonOperator.BETWEEN:
        return f"{_fmt(standard.min)} – {_fmt(standard.max)}{unit}"
    if operator == ComparisonOperator.IN_LIST and standard.options:
        return "∈ {" + ", ".join(_fmt(o) for o in standard.options) + "}"
    return standard.raw


def _fmt(v: float | None) -> str:
    if v is None:
        return "?"
    return str(int(v)) if float(v).is_integer() else f"{v:g}"
