"""Checker: kiến thức nghiệp vụ để kiểm một loại tiêu chí từ thực thể đã trích. Lõi so ngưỡng ở evaluator.py.

Mỗi checker nhận CheckPlan (+ rule) và thực thể, trả LineResult kèm bằng chứng. Thêm loại tiêu chí =
thêm checker + dòng trong plan_table.py, không sửa lõi. Chỉ dùng số GHI trên bản vẽ.
"""

import re
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from drawing_checker.common.enums import ComparisonOperator, FindingStatus
from drawing_checker.common.geometry import Point, Polygon, Precision
from drawing_checker.features.extraction.schemas import Entity, EntityKind
from drawing_checker.features.findings.schemas import Evidence, EvidenceRole, LineResult
from drawing_checker.features.rules.evaluator import at_threshold, compare, describe
from drawing_checker.features.rules.materials import find_materials, main_material
from drawing_checker.features.rules.materials import label as material_label
from drawing_checker.features.rules.schemas import CheckPlan, RuleInput

MAX_EVIDENCE_PAGES = 4  # cùng một số liệu lặp trên nhiều trang → giữ vài trang làm bằng chứng


@dataclass
class Level:
    key: str
    value: float
    confidence: float
    entities: list[Entity]
    note: str = ""


@dataclass
class CheckContext:
    entities: list[Entity]
    levels: dict[str, Level] = field(default_factory=dict)

    @classmethod
    def build(cls, entities: list[Entity]) -> "CheckContext":
        return cls(entities=entities, levels=_consolidate_levels(entities))

    def of(self, kind: EntityKind) -> list[Entity]:
        return [e for e in self.entities if e.kind == kind]


# ------------------------------------------------------------------ cao độ & chiều cao tầng


def _consolidate_levels(entities: list[Entity]) -> dict[str, Level]:
    """Gom cao độ cùng nhãn trên mọi trang; lấy số đông, ghi chú nếu có chỗ ghi khác."""
    by_key: dict[str, list[Entity]] = defaultdict(list)
    for e in entities:
        if e.kind == EntityKind.LEVEL:
            by_key[str(e.attributes["key"])].append(e)
    levels: dict[str, Level] = {}
    for key, items in by_key.items():
        counts = Counter(e.value for e in items)
        value, n = counts.most_common(1)[0]
        confidence, note = 0.95, ""
        if len(counts) > 1:
            others = [e for e in items if e.value != value]
            share = n / len(items)
            confidence = 0.9 if share >= 0.8 else 0.7
            note = (f"{len(others)}/{len(items)} chỗ ghi khác ({', '.join(_m(e.value) for e in others[:3])}"
                    f" — trang {', '.join(str(p) for p in sorted({e.page_number for e in others}))})")
        chosen = [e for e in items if e.value == value]
        levels[key] = Level(key, value, confidence, _one_per_page(chosen) + [e for e in items if e.value != value], note)
    # Nhãn "TẦNG n" trên cùng trùng cao độ mái là mái, không phải một tầng.
    roof = levels.get("roof")
    storeys = _storey_numbers(levels)
    if roof and storeys and levels[f"storey:{storeys[-1]}"].value == roof.value:
        del levels[f"storey:{storeys[-1]}"]
    return levels


def _storey_numbers(levels: dict[str, Level]) -> list[int]:
    return sorted(int(k.split(":")[1]) for k in levels if k.startswith("storey:"))


@dataclass
class Storey:
    name: str
    height: float
    confidence: float
    evidence: list[Entity]
    note: str = ""


def _storeys(ctx: CheckContext) -> dict[str, Storey]:
    """Chiều cao tầng = cao độ sàn tầng trên − cao độ sàn tầng này (số ghi, không đo hình)."""
    lv = ctx.levels
    result: dict[str, Storey] = {}
    numbers = _storey_numbers(lv)
    for i, n in enumerate(numbers):
        bottom = lv[f"storey:{n}"]
        top, top_conf = None, 0.95
        if i + 1 < len(numbers):
            top = lv[f"storey:{numbers[i + 1]}"]
        elif "roof" in lv:
            top, top_conf = lv["roof"], 0.85  # tầng trên cùng: tính tới cao độ mái
        if top is None:
            continue
        result[str(n)] = _storey(f"tầng {n}", bottom, top, top_conf)
    if "basement" in lv and numbers:
        result["basement"] = _storey("tầng hầm", lv["basement"], lv[f"storey:{numbers[0]}"], 0.9)
    if "attic" in lv:
        top = lv.get("roof_top") or lv.get("roof")
        if top and top.value > lv["attic"].value:
            result["attic"] = _storey("tầng tum", lv["attic"], top, 0.85)
    return result


def _storey(name: str, bottom: Level, top: Level, top_conf: float) -> Storey:
    notes = list(dict.fromkeys(n for n in (bottom.note, top.note) if n))
    return Storey(name, top.value - bottom.value, min(bottom.confidence, top.confidence, top_conf),
                  bottom.entities[:MAX_EVIDENCE_PAGES] + top.entities[:MAX_EVIDENCE_PAGES], "; ".join(notes))


def check_ground_floor_above_sidewalk(plan: CheckPlan, rule: RuleInput, ctx: CheckContext) -> list[LineResult]:
    lv = ctx.levels
    if "storey:1" not in lv or "sidewalk" not in lv:
        missing = "cao độ tầng 1" if "storey:1" not in lv else "cao độ vỉa hè"
        return [_unknown(plan, f"Không tìm thấy {missing} (nhãn + số) trên bản vẽ.")]
    ground, sidewalk = lv["storey:1"], lv["sidewalk"]
    diff = ground.value - sidewalk.value
    note = "; ".join(n for n in (ground.note, sidewalk.note) if n)
    return [_threshold_result(
        plan, diff, min(ground.confidence, sidewalk.confidence),
        f"Tầng 1 {_lv(ground.value)} − vỉa hè {_lv(sidewalk.value)} = {_m(diff)}",
        ground.entities[:MAX_EVIDENCE_PAGES] + sidewalk.entities[:MAX_EVIDENCE_PAGES], note,
    )]


def check_storey_height(plan: CheckPlan, rule: RuleInput, ctx: CheckContext) -> list[LineResult]:
    storeys = _storeys(ctx)
    wanted = str(plan.params.get("storey"))
    if wanted == "2-3":
        names = [k for k in ("2", "3") if k in storeys]
        if not names:
            return [_unknown(plan, "Không tìm thấy cao độ tầng 2, 3 để tính chiều cao tầng.")]
    elif wanted in storeys:
        names = [wanted]
    else:
        conditional = wanted in ("basement", "attic")
        label = {"basement": "tầng hầm", "attic": "tầng tum"}.get(wanted, f"tầng {wanted}")
        reason = (f"Không thấy {label} trên bản vẽ — tiêu chí chỉ áp dụng nếu có." if conditional
                  else f"Không tính được chiều cao {label} (thiếu cao độ tầng trên / tầng này).")
        return [_unknown(plan, reason)]
    items = [storeys[n] for n in names]
    worst = min(items, key=lambda s: s.height) if plan.operator == ComparisonOperator.GTE else max(items, key=lambda s: s.height)
    detail = "; ".join(f"{s.name}: {_m(s.height)}" for s in items)
    notes = "; ".join(dict.fromkeys(n for s in items for n in s.note.split("; ") if n))  # bỏ trùng
    evidence = [e for s in items for e in s.evidence]
    return [_threshold_result(plan, worst.height, min(s.confidence for s in items), detail, evidence, notes)]


# ------------------------------------------------------------------ thang bộ


@dataclass
class RiserGroup:
    storey: str  # "1→2"
    step: int
    count: int
    flights: list[Entity]


def _stairs(ctx: CheckContext) -> tuple[list[RiserGroup], list[Entity]]:
    """Tách vế ghi chiều cao bậc (risers) khỏi vế ghi chiều rộng bậc (treads) — KHÔNG đoán theo giá trị.

    Trong một chuỗi kích thước, các vế cùng chiều cao bậc cộng lại phải bằng chiều cao một tầng
    (vd. 18 + 7 bậc × 168 = 4200 = +4.450 − 0.250). Khớp được → là bậc cao của tầng đó.
    """
    flights = ctx.of(EntityKind.STAIR_FLIGHT)
    storeys = _storeys(ctx)
    storey_heights = [(k, s.height) for k, s in storeys.items() if k.isdigit()]
    chains: dict[str, list[Entity]] = defaultdict(list)
    for f in flights:
        chains[str(f.attributes["chain"])].append(f)
    groups: dict[tuple[str, int, int], RiserGroup] = {}
    riser_ids: set[int] = set()
    for chain in chains.values():
        by_step: dict[int, list[Entity]] = defaultdict(list)
        for f in chain:
            by_step[int(f.attributes["step"])].append(f)
        for step, items in by_step.items():
            count = sum(int(f.attributes["count"]) for f in items)
            total = count * step
            for k, height in storey_heights:
                if abs(total - height) <= max(10, count):
                    key = (k, step, count)
                    label = f"{k}→{int(k) + 1}" if f"storey:{int(k) + 1}" in ctx.levels else f"{k}→mái"
                    groups.setdefault(key, RiserGroup(label, step, count, [])).flights.extend(items)
                    riser_ids.update(id(f) for f in items)
                    break
    treads = [f for f in flights if id(f) not in riser_ids]
    return sorted(groups.values(), key=lambda g: g.storey), treads


def check_stair_riser(plan: CheckPlan, rule: RuleInput, ctx: CheckContext) -> list[LineResult]:
    groups, _ = _stairs(ctx)
    if not groups:
        return [_unknown(plan, _no_riser_reason(ctx))]
    worst = max(groups, key=lambda g: g.step)
    detail = "; ".join(f"tầng {g.storey}: {g.count} bậc × {g.step} mm" for g in groups)
    return [_threshold_result(plan, worst.step, 0.95, detail, [f for g in groups for f in g.flights])]


def check_stair_count(plan: CheckPlan, rule: RuleInput, ctx: CheckContext) -> list[LineResult]:
    groups, _ = _stairs(ctx)
    if not groups:
        return [_unknown(plan, _no_riser_reason(ctx))]
    failing = [g for g in groups if not compare(plan.operator, plan.value, g.count)] if plan.value else []
    detail = "; ".join(f"tầng {g.storey}: {g.count} bậc" for g in groups)
    subject = failing[0] if failing else groups[0]
    return [_threshold_result(plan, subject.count, 0.95, detail, [f for g in groups for f in g.flights], unit="bậc")]


def check_stair_tread(plan: CheckPlan, rule: RuleInput, ctx: CheckContext) -> list[LineResult]:
    _, treads = _stairs(ctx)
    if not treads:
        return [_unknown(plan, "Không tìm thấy ghi chú 'N BẬC x rộng' cho chiều rộng bậc.")]
    steps = sorted({int(f.attributes["step"]) for f in treads})
    worst = steps[0] if plan.operator == ComparisonOperator.GTE else steps[-1]
    detail = f"Các vế thang ghi chiều rộng bậc: {', '.join(f'{s} mm' for s in steps)}"
    # 0.85: "không phải bậc cao" suy ra bằng loại trừ — kém chắc hơn nhóm bậc cao đã khớp chiều cao tầng.
    return [_threshold_result(plan, worst, 0.85, detail, treads)]


def _no_riser_reason(ctx: CheckContext) -> str:
    if not ctx.of(EntityKind.STAIR_FLIGHT):
        return "Không tìm thấy ghi chú 'N BẬC x cao' trên bản vẽ."
    return "Không xác định được vế ghi chiều cao bậc: tổng các vế không khớp chiều cao tầng nào (hoặc thiếu cao độ tầng)."


# ------------------------------------------------------------------ danh mục kích thước cửa

CATALOG_ITEM = re.compile(r"(\d{3,4})\s*(?:mm)?\s*[xX×]\s*(\d{3,4})\s*(?:mm)?((?:\s*/\s*\d{3,4}\s*(?:mm)?)*)")


@dataclass
class CatalogItem:
    rule: RuleInput
    plan: CheckPlan
    height: int
    widths: list[int]

    def matches(self, width: int, height: int) -> bool:
        return height == self.height and width in self.widths

    def distance(self, width: int, height: int) -> int:
        return abs(height - self.height) + min(abs(width - w) for w in self.widths)

    def label(self) -> str:
        return f"{self.height} × {'/'.join(str(w) for w in self.widths)}"


def _catalog(rule_plans: list[tuple[RuleInput, list[CheckPlan]]]) -> list[CatalogItem]:
    items = []
    for rule, plans in rule_plans:
        for plan in plans:
            # Dòng danh mục ghi "(Cao x Rộng): 2800 x 1100mm" — lấy phần sau dấu ":" để tránh "cách sàn 0.9m".
            m = CATALOG_ITEM.search(plan.text.split(":", 1)[-1])
            if m:
                widths = [int(m.group(2))] + [int(w) for w in re.findall(r"\d{3,4}", m.group(3) or "")]
                items.append(CatalogItem(rule, plan, int(m.group(1)), widths))
    return items


def _opening_class(e: Entity) -> tuple[str | None, str | None]:
    """(door|window, swing|sliding|fixed) từ mã + mô tả trong bảng cửa."""
    code = (e.label or "").upper()
    text = str(e.attributes.get("description", "")).lower()
    opening = "window" if code.startswith(("WD", "W", "CS")) or "cửa sổ" in text else (
        "door" if code.startswith(("DR", "D", "CD")) or text.startswith("cửa") else None)
    mechanism = ("sliding" if re.search(r"trượt|lùa", text) else
                 "swing" if re.search(r"\bmở\b|\bbật\b|quay", text) else
                 "fixed" if re.search(r"cố định|vách", text) else None)
    return opening, mechanism


def check_opening_catalog(rule_plans: list[tuple[RuleInput, list[CheckPlan]]], ctx: CheckContext) -> list[LineResult]:
    """Mỗi cửa trong bảng thống kê phải có kích thước thuộc danh mục CHTK đúng loại (1.4.1–1.4.5)."""
    catalog = _catalog(rule_plans)
    openings = [e for e in ctx.of(EntityKind.OPENING) if e.label]  # mục không mã (vd. cửa thăm mái) bỏ qua
    if not openings:
        return [_unknown(plans[0], "Không tìm thấy bảng thống kê cửa (dạng '900w x 2800h' + mã DR-/WD-).")
                for _, plans in rule_plans if plans]
    results = []
    for e in openings:
        width, height = int(e.attributes["width"]), int(e.attributes["height"])
        opening, mechanism = _opening_class(e)
        same_class = [c for c in catalog if _plan_class(c.plan) == (opening, mechanism)]
        same_opening = [c for c in catalog if _plan_class(c.plan)[0] == opening] or catalog
        evidence = _opening_evidence(e)
        kind = f"{'cửa đi' if opening == 'door' else 'cửa sổ' if opening == 'window' else 'cửa'}" \
               f"{' ' + {'swing': 'mở', 'sliding': 'lùa', 'fixed': 'cố định'}[mechanism] if mechanism else ''}"
        # Bảng cửa ghi "R w x C h"; danh mục CHTK ghi "Cao x Rộng" → hiển thị thống nhất C × R.
        size = f"{height} × {width}"
        subject = f"{e.label} ({kind}, {e.attributes.get('location') or 'không rõ vị trí'}): {size} mm (C × R)"
        exact = next((c for c in same_class if c.matches(width, height)), None)
        if exact:
            results.append(_result(exact.plan, FindingStatus.PASS, 0.9,
                                   f"{subject} khớp mục danh mục {exact.label()}.",
                                   size, exact.label(), evidence))
            continue
        other = next((c for c in same_opening if c.matches(width, height)), None)
        pool = same_class or same_opening
        nearest = min(pool, key=lambda c: c.distance(width, height))
        allowed = "; ".join(c.label() for c in pool)
        if other:
            results.append(_result(nearest.plan, FindingStatus.WARNING, 0.75,
                                   f"{subject} có trong danh mục nhưng ở nhóm khác ({other.rule.title}); cần xác nhận loại cửa.",
                                   size, allowed, evidence))
            continue
        confidence = 0.9 if same_class else 0.75  # không xác định được loại cửa → không đủ chắc để kết luận fail
        results.append(_result(nearest.plan, FindingStatus.FAIL, confidence,
                               f"{subject} không thuộc danh mục kích thước CHTK "
                               f"({'nhóm ' + nearest.rule.title if same_class else 'không rõ loại, so với mọi mục cùng nhóm'}). "
                               f"Gần nhất: {nearest.label()}.",
                               size, allowed, evidence))
    return results


def _plan_class(plan: CheckPlan) -> tuple[str | None, str | None]:
    return plan.params.get("opening"), plan.params.get("mechanism")  # type: ignore[return-value]


def _opening_evidence(e: Entity) -> list[Evidence]:
    evidence = [_evidence(e, EvidenceRole.MEASUREMENT)]
    if "code_bbox" in e.attributes:
        x0, y0, x1, y1 = (float(v) for v in str(e.attributes["code_bbox"]).split(","))
        evidence.append(Evidence(pageNumber=e.page_number, polygon=_rect(x0, y0, x1, y1),
                                 role=EvidenceRole.SUBJECT, text=e.label))
    return evidence


# ------------------------------------------------------------------ vật liệu trần ngoài nhà (5.1)

# Yêu cầu hoàn thiện của dòng (params.finish) → (từ khóa phải có, mẫu chi tiết để coi là đạt hẳn).
FINISH_REQUIREMENTS: dict[str, tuple[str, str, re.Pattern | None]] = {
    "plaster": ("trát vữa", "TRÁT", re.compile(r"\b15\s*MM|DÀY\s*15")),
    "paint": ("sơn nước", "SƠN", None),
}


def check_exterior_ceiling(rule_plans: list[tuple[RuleInput, list[CheckPlan]]], ctx: CheckContext) -> list[LineResult]:
    """Trần ngoài nhà (5.1.x): vật liệu trần trên bản vẽ phải thuộc loại tiêu chí cho phép.

    Nguồn: dòng bảng "VẬT LIỆU HOÀN THIỆN TRẦN" + ghi chú có chữ "TRẦN". Vật liệu được phép suy ra từ câu tiêu chí
    (hoặc tên rule khi dòng không nêu vật liệu, vd. 5.1.2 "Trần bê tông") bằng cùng từ điển `materials`.
    Phạm vi "ngoài nhà" lấy từ gợi ý của trang; không có gợi ý → hạ tin cậy (không kết luận fail).
    Mỗi loại vật liệu một kết quả, bằng chứng là mọi chỗ ghi (bảng + ghi chú) trên các trang.
    """
    pairs = [(rule, plan) for rule, plans in rule_plans for plan in plans]
    material_lines = [(rule, plan) for rule, plan in pairs if find_materials(plan.text)]
    finish_lines = [(rule, plan) for rule, plan in pairs if plan.params.get("finish")]
    allowed_by_rule: dict[str, set[str]] = defaultdict(set)
    for rule, plan in pairs:
        allowed_by_rule[rule.code or rule.rule_id].update(find_materials(plan.text) or find_materials(rule.title or ""))
    allowed = set().union(*allowed_by_rule.values())
    standard = "; ".join(f"{code}: {', '.join(material_label(k) for k in sorted(keys))}"
                         for code, keys in allowed_by_rule.items() if keys)
    first_line = (material_lines or pairs)[0][1]

    groups: dict[str, list[Entity]] = defaultdict(list)
    for e in ctx.entities:
        if e.attributes.get("surface") != "ceiling" or e.kind not in (EntityKind.FINISH, EntityKind.CALLOUT):
            continue
        text = str(e.attributes.get("description") or e.text or "")
        material = main_material(text)
        if material is None and e.kind == EntityKind.CALLOUT:
            continue  # ghi chú nhắc "trần" mà không nêu vật liệu (tên hình, cao độ trần…) — không phải bằng chứng
        groups[material or "unknown"].append(e)
    if not groups:
        return [_unknown(plans[0], "Không tìm thấy vật liệu trần (bảng 'VẬT LIỆU HOÀN THIỆN TRẦN' hoặc ghi chú) trên bản vẽ.")
                for _, plans in rule_plans if plans]

    results = []
    for material, items in groups.items():
        evidence = _annotation_evidence(items)
        pages = ", ".join(str(p) for p in sorted({e.page_number for e in items}))
        codes = sorted({e.label for e in items if e.label})
        subject = ", ".join(codes + (["ghi chú chi tiết"] if any(e.kind == EntityKind.CALLOUT for e in items) else []))
        hints = sorted({str(e.attributes["exterior"]) for e in items if e.attributes.get("exterior")})
        confidence = 0.9 if hints else 0.7
        scope = (f"Phạm vi ngoài nhà: trang có ghi '{', '.join(hints)}'." if hints
                 else "Không thấy dấu hiệu 'ngoài nhà' trên trang — cần xác nhận phạm vi.")
        where = f"{subject} — trang {pages}"
        if material in ("unknown", "raw"):
            sample = str(items[0].attributes.get("description") or items[0].text)
            results.append(_result(first_line, FindingStatus.PENDING, confidence,
                                   f"Trần ghi '{sample}' ({where}): không nêu vật liệu trần, cần người xem. {scope}",
                                   sample, standard, evidence))
            continue
        if material not in allowed:
            results.append(_result(first_line, FindingStatus.FAIL, confidence,
                                   f"Trần ngoài nhà dùng {material_label(material)} ({where}). Không thuộc vật liệu CHTK "
                                   f"cho phép ({standard}) — không đạt ở mọi vùng áp dụng. {scope}",
                                   material_label(material), standard, evidence))
            continue
        board_lines = [(r, p) for r, p in material_lines if material in find_materials(p.text)]
        if board_lines:
            # Đúng loại tấm; độ dày / chống ẩm / vùng (biển – đồng bằng) chưa kiểm được từ mô tả → người xem.
            rule, plan = board_lines[0]
            results.append(_result(plan, FindingStatus.PENDING, confidence,
                                   f"Trần {material_label(material)} ({where}) đúng loại vật liệu của {rule.code}; "
                                   f"chưa kiểm được độ dày, chống ẩm và vùng áp dụng. {scope}",
                                   material_label(material), plan.text, evidence))
            continue
        text = " ".join(str(e.attributes.get("description") or e.text) for e in items).upper()
        for rule, plan in finish_lines:
            if material not in find_materials(rule.title or ""):
                continue
            name, keyword, detail = FINISH_REQUIREMENTS[str(plan.params["finish"])]
            base = f"Trần {material_label(material)} ({where}) đúng loại của {rule.code}"
            if keyword not in text:
                status, reason = FindingStatus.PENDING, f"{base}; không thấy ghi {name} — cần người xem."
            elif detail is not None and not detail.search(text):
                status, reason = FindingStatus.PENDING, f"{base}; có ghi {name} nhưng không ghi chi tiết để đối chiếu '{plan.text}'."
            else:
                status, reason = FindingStatus.PASS, f"{base}; có ghi {name}."
            results.append(_result(plan, status, confidence, f"{reason} {scope}", material_label(material), plan.text, evidence))
    return results


def _annotation_evidence(items: list[Entity]) -> list[Evidence]:
    seen, out = set(), []
    for e in items:
        key = (e.page_number, e.text)
        if key not in seen:
            seen.add(key)
            out.append(_evidence(e, EvidenceRole.ANNOTATION))
    return out


# ------------------------------------------------------------------ đăng ký

LINE_CHECKERS: dict[str, Callable[[CheckPlan, RuleInput, CheckContext], list[LineResult]]] = {
    "ground_floor_above_sidewalk": check_ground_floor_above_sidewalk,
    "storey_height": check_storey_height,
    "stair_riser": check_stair_riser,
    "stair_count": check_stair_count,
    "stair_tread": check_stair_tread,
}
# Checker cần nhìn nhiều rule cùng lúc (danh mục trải trên 1.4.1–1.4.5).
GROUP_CHECKERS: dict[str, Callable[[list[tuple[RuleInput, list[CheckPlan]]], CheckContext], list[LineResult]]] = {
    "opening_catalog": check_opening_catalog,
    "exterior_ceiling": check_exterior_ceiling,
}


# ------------------------------------------------------------------ tiện ích kết quả


def _threshold_result(plan: CheckPlan, measured: float, confidence: float, detail: str,
                      entities: list[Entity], note: str = "", unit: str | None = None) -> LineResult:
    if plan.value is None:
        return _unknown(plan, f"Không phân tích được ngưỡng của tiêu chí. Số liệu trích: {detail}.")
    unit = unit if unit is not None else (plan.value.unit or "")
    standard = describe(plan.operator, plan.value)
    ok = compare(plan.operator, plan.value, measured)
    extracted = f"{_fmt(measured)} {unit}".strip()
    reason = f"{detail}. {'Đạt' if ok else 'Không đạt'} ngưỡng {standard}"
    if ok and at_threshold(plan.operator, plan.value, measured):
        reason += " (đạt sát ngưỡng)"
    reason += "."
    if note:
        reason += f" Lưu ý: {note}."
    evidence = [_evidence(e, EvidenceRole.MEASUREMENT) for e in entities]
    if plan.note:
        return _result(plan, FindingStatus.PENDING, confidence,
                       f"{plan.note} Nếu áp dụng: {reason}", extracted, standard, evidence)
    return _result(plan, FindingStatus.PASS if ok else FindingStatus.FAIL, confidence, reason, extracted, standard, evidence)


def _result(plan: CheckPlan, status: FindingStatus, confidence: float, reason: str,
            extracted: str | None, standard: str | None, evidence: list[Evidence]) -> LineResult:
    return LineResult(ruleId=plan.rule_id, lineIndex=plan.line_index, status=status, confidence=confidence,
                      reason=reason, extractedValue=extracted, standardValue=standard, evidence=evidence)


def _unknown(plan: CheckPlan, reason: str) -> LineResult:
    return _result(plan, FindingStatus.UNKNOWN, 0.0, reason, None,
                   describe(plan.operator, plan.value) if plan.value else None, [])


def _evidence(e: Entity, role: EvidenceRole) -> Evidence:
    return Evidence(pageNumber=e.page_number, polygon=e.polygon, role=role, text=e.text,
                    measuredValue=e.value, unit=e.unit)


def _one_per_page(items: list[Entity]) -> list[Entity]:
    seen, out = set(), []
    for e in items:
        if e.page_number not in seen:
            seen.add(e.page_number)
            out.append(e)
    return out


def _rect(x0: float, y0: float, x1: float, y1: float) -> Polygon:
    return Polygon(points=[Point(x=x0, y=y0), Point(x=x1, y=y0), Point(x=x1, y=y1), Point(x=x0, y=y1)],
                   precision=Precision.BBOX)


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _m(mm: float) -> str:
    return f"{_fmt(mm)} mm"


def _lv(mm: float) -> str:
    sign = "±" if mm == 0 else ("+" if mm > 0 else "−")
    return f"{sign}{abs(mm) / 1000:.3f}"
