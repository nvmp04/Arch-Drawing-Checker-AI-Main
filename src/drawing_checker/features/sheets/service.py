"""Đọc cấu trúc bộ hồ sơ — giai đoạn A (research-log §12). Thuật toán cố định, chỉ đọc bản vẽ (D-18).

- Khung tên: nhãn song ngữ cỡ nhỏ ("TÊN BẢN VẼ - DRAWING NAME", "TỶ LỆ / SCALE:") + giá trị ngay dưới nhãn.
  Nhãn là quy ước khung tên bản vẽ, không phải nội dung tiêu chí.
- Tiêu đề hình / bảng: chữ ngang to hẳn so với chữ thường của trang; tiêu đề dài xuống dòng thì ghép.
- Bảng viết tắt: tiêu đề "VIẾT TẮT" + cột chữ viết tắt + nghĩa ngang hàng bên phải.
- Đặc điểm hồ sơ: gom từ khung tên + cao độ đã trích (`extraction`).
"""

import re
import statistics
from collections import Counter, defaultdict

from drawing_checker.common.geometry import Point, Polygon, Precision
from drawing_checker.features.extraction.schemas import Entity, EntityKind
from drawing_checker.features.ingest.schemas import DrawingPage, TextSpan
from drawing_checker.features.sheets.schemas import (
    Abbreviation,
    DocumentIndex,
    DossierProfile,
    DrawingView,
    SheetInfo,
    TitleBlock,
)

# --- Khung tên ---
# Nhãn song ngữ: "<tiếng Việt> - <TIẾNG ANH>" hoặc "<tiếng Việt> / <TIẾNG ANH>:"; trường lấy theo phần tiếng Anh.
TITLE_LABEL = re.compile(r"[-/]\s*([A-Z][A-Z .&]*[A-Z])\s*:?\s*$")
TITLE_FIELDS: dict[str, str] = {
    "DRAWING NAME": "name",
    "SCALE": "scale",
    "ITEM": "item",
    "PROJECT PHASE": "phase",
    "LOCATION": "project",
    "CONSULTANT": "discipline",  # "BỘ MÔN - CONSULTANT" (≠ "DESIGN CONSULTANT")
    "ISSUE DAY": "issued",
    "DRAWING NO": "number",
    "SHEET NO": "number",
}
SCALE_VALUE = re.compile(r"^\s*1\s*/\s*(\d+|NTS)\b", re.IGNORECASE)
TITLE_ROW_TOLERANCE = 4.0  # point: các nhãn cùng hàng
TITLE_STRIP_WIDTH = 260.0  # point: khung tên dạng cột dọc ở mép phải

# --- Tiêu đề hình / bảng ---
VIEW_TITLE_RATIO = 1.3  # cỡ chữ ≥ 1.3 × cỡ chữ trung vị của trang
VIEW_TITLE_MIN_CHARS = 10  # bỏ đầu cột bảng ngắn ("MÔ TẢ", "KÝ HIỆU")
VIEW_SCALE = re.compile(r"(?<![A-ZĐ])TL\s*[:.]?\s*1\s*/\s*(\d+)", re.IGNORECASE)  # "…_TL:1/25"
VIEW_TITLE_LINE_GAP = 1.6  # × cỡ chữ: dòng thứ hai của tiêu đề dài

# --- Bảng viết tắt ---
ABBR_HEADER = re.compile(r"VIẾT TẮT|ABBREVIATION")
ABBR_TOKEN = re.compile(r"^[A-Z][A-Za-z0-9&.\-/]{0,7}$|^[&#±Ø]$")  # "BTCT", "No.", "M&E", "Ø"
ABBR_ROW_TOLERANCE = 9.0  # point: nghĩa căn giữa ô nên lệch dọc vài point so với chữ viết tắt
ABBR_MAX_DEPTH = 900.0  # point: bảng nằm dưới tiêu đề


class SheetService:
    def analyze(self, page: DrawingPage) -> SheetInfo:
        """Khung tên + các tiêu đề hình / bảng của một trang."""
        return SheetInfo(page_number=page.page_number, title_block=read_title_block(page), views=read_views(page))

    def abbreviations(self, page: DrawingPage) -> list[Abbreviation]:
        return read_abbreviations(page)

    def build_index(self, sheets: list[SheetInfo], abbreviations: list[Abbreviation],
                    entities: list[Entity]) -> DocumentIndex:
        return DocumentIndex(sheets=sorted(sheets, key=lambda s: s.page_number),
                             abbreviations=_dedupe_abbreviations(abbreviations),
                             profile=build_profile(sheets, entities))


# ------------------------------------------------------------------ khung tên


def read_title_block(page: DrawingPage) -> TitleBlock | None:
    """Ưu tiên chữ ngoài vùng hiển thị (khung tên bị cắt khỏi khổ in), rồi tới chữ trong trang."""
    for source, texts in (("margin", page.margin_texts), ("page", page.texts)):
        block = _title_block(texts)
        if block is not None:
            block.source = source
            return block
    return None


def _title_block(texts: list[TextSpan]) -> TitleBlock | None:
    horizontal = [t for t in texts if abs(t.rotation) < 1 or abs(t.rotation - 360) < 1]
    labels = [t for t in horizontal if TITLE_LABEL.search(t.text.strip())]
    anchor = next((t for t in labels if "DRAWING NAME" in t.text.upper()), None)
    if anchor is None:
        return None
    left = _box(anchor)[0] - 15
    strip = _dedupe_overlaps([t for t in horizontal if left <= _box(t)[0] <= left + TITLE_STRIP_WIDTH])
    labels = [t for t in labels if t in strip]
    values: dict[int, list[TextSpan]] = defaultdict(list)
    for t in strip:
        if t in labels:
            continue
        above = [lb for lb in labels if _box(lb)[1] < _box(t)[1] - 1]
        if not above:
            continue
        row = max(_box(lb)[1] for lb in above)
        same_row = [lb for lb in above if row - _box(lb)[1] <= TITLE_ROW_TOLERANCE]
        owner = min(same_row, key=lambda lb: abs(_cx(lb) - _cx(t)))
        values[id(owner)].append(t)

    block = TitleBlock()
    loose: list[TextSpan] = []  # chữ không hợp nhãn (vd. số hiệu bản vẽ nằm dưới hàng tỉ lệ / ngày)
    for label in sorted(labels, key=lambda lb: (_box(lb)[1], _box(lb)[0])):
        english = TITLE_LABEL.search(label.text.strip()).group(1).strip()
        field = TITLE_FIELDS.get(english)
        if english == "CONSULTANT" and "DESIGN" in label.text.upper():
            field = None
        items = sorted(values[id(label)], key=lambda t: (round(_box(t)[1] / 3), _box(t)[0]))
        if field == "scale":
            kept = [t for t in items if SCALE_VALUE.match(t.text)]
            loose += [t for t in items if t not in kept]
            items = kept[:1]
        elif field == "issued":
            kept = [t for t in items if re.search(r"\d{4}|\d{1,2}/\d{1,2}", t.text) and len(t.text) <= 12]
            loose += [t for t in items if t not in kept]
            items = kept[:1]
        value = " ".join(" ".join(t.text.split()) for t in items).strip()
        if not value:
            continue
        block.fields[" ".join(label.text.split())] = value
        if field and getattr(block, field) is None:
            setattr(block, field, value)
    if block.number is None and loose:
        block.number = " ".join(" ".join(t.text.split()) for t in sorted(loose, key=lambda t: (round(_box(t)[1] / 3), _box(t)[0])))
    if block.scale:
        m = SCALE_VALUE.match(block.scale)
        block.scale_denominator = int(m.group(1)) if m and m.group(1).isdigit() else None
    return block


# ------------------------------------------------------------------ tiêu đề hình / bảng


def read_views(page: DrawingPage) -> list[DrawingView]:
    horizontal = [t for t in page.texts if (abs(t.rotation) < 1 or abs(t.rotation - 360) < 1) and t.size]
    if not horizontal:
        return []
    median = statistics.median(t.size for t in horizontal)
    big = [t for t in horizontal if t.size >= VIEW_TITLE_RATIO * median and re.search(r"[^\W\d_]{2}", t.text)]
    used: set[int] = set()
    views: list[DrawingView] = []
    for t in sorted(big, key=lambda t: (_box(t)[1], _box(t)[0])):
        if id(t) in used:
            continue
        lines = [t]
        while True:  # tiêu đề dài xuống dòng: dòng dưới cùng lề trái, cùng cỡ chữ, sát ngay dưới
            last = lines[-1]
            nxt = next((u for u in big if id(u) not in used and u is not last and u not in lines
                        and abs(_box(u)[0] - _box(last)[0]) <= 3 and abs(u.size - last.size) < 0.5
                        and 0 < _box(u)[1] - _box(last)[1] <= VIEW_TITLE_LINE_GAP * last.size), None)
            if nxt is None:
                break
            lines.append(nxt)
        used.update(id(u) for u in lines)
        title = " ".join(" ".join(u.text.split()) for u in lines)
        if len(title) < VIEW_TITLE_MIN_CHARS:
            continue
        scale = VIEW_SCALE.search(title)
        views.append(DrawingView(page_number=page.page_number, title=title,
                                 scale_denominator=int(scale.group(1)) if scale else None, polygon=_union(lines)))
    # Cùng tiêu đề đặt hai lần đè nhau (PN2 trang 44) → giữ một.
    unique: dict[tuple[str, int, int], DrawingView] = {}
    for v in views:
        unique.setdefault((v.title, round(v.polygon.points[0].x), round(v.polygon.points[0].y)), v)
    return list(unique.values())


# ------------------------------------------------------------------ bảng viết tắt


def read_abbreviations(page: DrawingPage) -> list[Abbreviation]:
    """Bảng viết tắt: dưới tiêu đề "VIẾT TẮT", mỗi chữ viết tắt ghép với chữ gần nhất ngang hàng bên phải.

    Bảng có thể chia nhiều cặp cột; nghĩa của một chữ viết tắt phải nằm trước cột viết tắt kế tiếp.
    """
    texts = [t for t in page.texts if abs(t.rotation) < 1 or abs(t.rotation - 360) < 1]
    result: list[Abbreviation] = []
    for header in (t for t in texts if ABBR_HEADER.search(t.text.upper())):
        hx0, _, hx1, hy1 = _box(header)
        below = [t for t in texts if hy1 < _box(t)[1] <= hy1 + ABBR_MAX_DEPTH and t is not header]
        tokens = [t for t in below if ABBR_TOKEN.match(t.text.strip()) and not t.text.strip().isdigit()]
        if not tokens:
            continue
        # Cột viết tắt = các lề trái có nhiều chữ viết tắt thẳng hàng.
        columns = sorted(x for x, n in Counter(round(_box(t)[0] / 6) * 6 for t in tokens).items() if n >= 4)
        if not columns:
            continue
        # Bảng khác đặt cùng hàng tiêu đề (vd. "CHÚ THÍCH KÝ HIỆU") chặn biên phải.
        neighbours = [_box(u)[0] for u in texts if u is not header and abs(_cy(u) - _cy(header)) < 5 and _box(u)[0] > hx1]
        right_edge = min(neighbours) - 5 if neighbours else hx1 + (hx1 - hx0) * 3
        abbrs = [t for t in tokens if any(abs(_box(t)[0] - c) <= 6 for c in columns)]
        taken: set[int] = set()
        for t in sorted(abbrs, key=lambda t: (_box(t)[0], _box(t)[1])):
            col = min(columns, key=lambda c: abs(_box(t)[0] - c))
            nxt = next((c for c in columns if c > col + 12), right_edge)
            candidates = [u for u in below if id(u) not in taken and u not in abbrs and _box(t)[2] < _box(u)[0] < nxt
                          and abs(_cy(u) - _cy(t)) <= ABBR_ROW_TOLERANCE]
            # Gần nhất theo dọc; hòa thì chữ gần hơn theo ngang (không lấy chữ của bảng bên cạnh).
            meaning = min(candidates, key=lambda u: abs(_cy(u) - _cy(t)) + 0.05 * (_box(u)[0] - _box(t)[2]), default=None)
            if meaning is None:
                continue
            taken.add(id(meaning))
            result.append(Abbreviation(abbr=t.text.strip(), meaning=" ".join(meaning.text.split()),
                                       page_number=page.page_number, polygon=_union([t, meaning])))
    return result


def expand_abbreviations(text: str, abbreviations: list[Abbreviation]) -> str:
    """Thay chữ viết tắt (nguyên từ, từ 2 ký tự) bằng nghĩa trong bảng viết tắt của chính bộ hồ sơ.

    Chữ viết tắt 1 ký tự ("D", "M", "&") không thay — dễ trùng ký hiệu khác ("D6@200", "M75").
    Dùng để đưa chữ trên bản vẽ về tiếng Việt đầy đủ trước khi so với tiêu chí; bằng chứng vẫn giữ chữ gốc.
    """
    table = {a.abbr: a.meaning for a in abbreviations if len(a.abbr) >= 2 and any(ch.isalpha() for ch in a.abbr)}
    if not table:
        return text
    # Nguyên từ, không dính "-" / "." hai bên → không đụng mã ("DR-01", "CT-ST", "A.FX.301").
    words = "|".join(re.escape(k) for k in sorted(table, key=len, reverse=True))
    pattern = re.compile(r"(?<![\w.\-])(" + words + r")(?![\w\-])")
    return pattern.sub(lambda m: table[m.group(1)], text)


def _dedupe_abbreviations(items: list[Abbreviation]) -> list[Abbreviation]:
    seen: dict[str, Abbreviation] = {}
    for a in items:
        seen.setdefault(a.abbr, a)
    return list(seen.values())


# ------------------------------------------------------------------ đặc điểm hồ sơ


def build_profile(sheets: list[SheetInfo], entities: list[Entity]) -> DossierProfile:
    blocks = [s.title_block for s in sheets if s.title_block]
    levels: dict[str, Counter] = defaultdict(Counter)
    for e in entities:
        if e.kind == EntityKind.LEVEL and e.value is not None:
            levels[str(e.attributes.get("key"))][e.value] += 1
    level_values = {k: c.most_common(1)[0][0] for k, c in sorted(levels.items())}
    storeys = sorted(int(k.split(":")[1]) for k in level_values if k.startswith("storey:"))
    # Nhãn "TẦNG n" trên cùng có cao độ trùng mái → là mái, không phải một tầng (cùng quy tắc với rules/checkers).
    if storeys and "roof" in level_values and level_values[f"storey:{storeys[-1]}"] == level_values["roof"]:
        storeys.pop()
    return DossierProfile(
        page_count=len(sheets),
        items=sorted({b.item for b in blocks if b.item}),
        project=_most_common(b.project for b in blocks),
        phase=_most_common(b.phase for b in blocks),
        storeys=storeys,
        has_basement="basement" in level_values,
        has_attic="attic" in level_values,
        levels=level_values,
        scales=sorted({b.scale for b in blocks if b.scale}),
        pages_without_title_block=[s.page_number for s in sheets if s.title_block is None],
    )


def _most_common(values) -> str | None:
    counts = Counter(v for v in values if v)
    return counts.most_common(1)[0][0] if counts else None


# ------------------------------------------------------------------ tiện ích tọa độ


def _dedupe_overlaps(texts: list[TextSpan]) -> list[TextSpan]:
    """Bỏ chữ giống hệt vẽ đè lên nhau (CAD xuất trùng: "CD" "CD", "MẪU NHÀ SH1" hai lần)."""
    kept: list[TextSpan] = []
    for t in texts:
        if not any(u.text == t.text and abs(_box(u)[0] - _box(t)[0]) < 3 and abs(_box(u)[1] - _box(t)[1]) < 3
                   for u in kept):
            kept.append(t)
    return kept


def _box(t: TextSpan) -> tuple[float, float, float, float]:
    xs = [p.x for p in t.polygon.points]
    ys = [p.y for p in t.polygon.points]
    return min(xs), min(ys), max(xs), max(ys)


def _cx(t: TextSpan) -> float:
    b = _box(t)
    return (b[0] + b[2]) / 2


def _cy(t: TextSpan) -> float:
    b = _box(t)
    return (b[1] + b[3]) / 2


def _union(texts: list[TextSpan]) -> Polygon:
    boxes = [_box(t) for t in texts]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    return Polygon(points=[Point(x=x0, y=y0), Point(x=x1, y=y0), Point(x=x1, y=y1), Point(x=x0, y=y1)],
                   precision=Precision.BBOX)
