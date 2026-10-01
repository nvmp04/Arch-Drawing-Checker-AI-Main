"""Trích thực thể từ chữ vector — v0 heuristic thuần (regex + quan hệ tọa độ), KHÔNG có model AI.

Chỉ dùng số GHI trên bản vẽ, không đo hình học (tỉ lệ bản vẽ có thể sai / bị gõ đè).
Các mẫu dưới đây rút từ bộ PN2 (research-log §4, §6); bản vẽ đơn vị khác có thể cần mở rộng.
"""

import re

from drawing_checker.common.geometry import Point, Polygon, Precision
from drawing_checker.features.extraction.schemas import Entity, EntityKind
from drawing_checker.features.ingest.schemas import DrawingPage, TextSpan

# --- Cao độ: nhãn "TẦNG 2" với số "+4.450" ngay bên dưới (mặt đứng, mặt cắt) ---
LEVEL_VALUE = re.compile(r"^([±+\-]?)\s?(\d+)[.,](\d{3})$")
LEVEL_LABELS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^TẦNG\s+(\d+)$"), "storey:{0}"),
    (re.compile(r"^(?:TẦNG\s+)?HẦM$"), "basement"),
    (re.compile(r"^(?:TẦNG\s+)?TUM$"), "attic"),
    (re.compile(r"^ĐỈNH\s+MÁI$"), "roof_top"),
    (re.compile(r"^MÁI$"), "roof"),
    (re.compile(r"^VỈA\s+HÈ$"), "sidewalk"),
]
LEVEL_MAX_DY = 20.0  # point: số nằm ngay dưới nhãn
LEVEL_MAX_DX = 15.0

# --- Vế thang: "18 BẬC x 168=3024" ---
STAIR = re.compile(r"(\d+)\s*BẬC\s*[xX×]\s*(\d+)(?:\s*=\s*(\d+))?", re.IGNORECASE)

# --- Bảng thống kê cửa: "4800w x 3000h" + mã cột "DR-01" ---
OPENING_SIZE = re.compile(r"^(\d{3,4})\s*w\s*[xX×]\s*(\d{3,4})\s*h$", re.IGNORECASE)
OPENING_CODE = re.compile(r"^(DR|WD|CD|CS|D|W|S|V)[-.]?\d{1,3}[A-Z]?$")
CELL_MARGIN = 10.0  # chữ trong ô bảng căn trái; mã cột căn giữa → ô i = [x_i − lề, x_{i+1} − lề)
CELL_TEXT_DEPTH = 80.0  # các dòng mô tả loại cửa nằm ngay dưới dòng kích thước

# --- Bảng vật liệu hoàn thiện: tiêu đề "VẬT LIỆU HOÀN THIỆN TRẦN" + đầu cột "KÝ HIỆU | MÔ TẢ" + mã FC-01, FW1, L1 ---
FINISH_CODE = re.compile(r"^[A-ZĐ]{1,4}[-.]?\d{1,3}[A-Z]?$")
FINISH_TITLE_GAP = 20.0  # point: tiêu đề nằm ngay trên dòng đầu cột
FINISH_ROW_GAP = 30.0  # hai mã liên tiếp cách xa hơn → hết bảng
FINISH_CODE_SLACK = 30.0  # mã căn giữa cột "KÝ HIỆU" → lệch trái/phải so với chữ đầu cột
FINISH_WIDTH_RATIO = 1.6  # cột mô tả rộng ~1.6 lần khoảng "KÝ HIỆU" → "MÔ TẢ"
SURFACES: list[tuple[str, re.Pattern]] = [
    ("ceiling", re.compile(r"\bTRẦN\b")),
    ("wall", re.compile(r"\bTƯỜNG\b")),
    ("floor", re.compile(r"\bSÀN\b")),
]
# Ghi chú ngoài bảng: đợt đầu chỉ lấy ghi chú về trần (5.1); tường / sàn mở rộng khi có checker.
CALLOUT_SURFACES = {"ceiling"}
CALLOUT_STACK_GAP = 1.2  # × chiều cao chữ: các dòng của một ghi chú xếp chồng sát nhau
CALLOUT_STACK_DX = 4.0
CALLOUT_SKIP = re.compile(r"\bĐÈN\b")  # "ĐÈN ỐP TRẦN" là thiết bị điện, không phải vật liệu trần
# Dấu hiệu trang / bảng thuộc phần ngoài nhà (phạm vi của nhóm 5.x). Danh sách tay — sau này thay bằng embedding.
EXTERIOR_HINTS = re.compile(r"NGOẠI THẤT|NGOÀI NHÀ|MÁI ĐÓN|SẢNH|\bHIÊN\b|BAN CÔNG|LÔ GIA|LOGIA|SÂN THƯỢNG")


class ExtractionService:
    """v0: heuristic (regex + ghép theo tọa độ). v1: model trên đồ thị nét vẽ, train từ nhãn đã sửa."""

    def extract(self, page: DrawingPage) -> list[Entity]:
        finishes, used = extract_finish_tables(page)
        return [*extract_levels(page), *extract_stair_flights(page), *extract_openings(page),
                *finishes, *extract_callouts(page, exclude=used)]


def extract_levels(page: DrawingPage) -> list[Entity]:
    values = [(t, m) for t in page.texts if (m := LEVEL_VALUE.match(t.text))]
    entities = []
    for label in page.texts:
        key = _level_key(label.text)
        if key is None:
            continue
        lx, ly = _x0(label), _y0(label)
        best = None
        for value, m in values:
            dy, dx = _y0(value) - ly, abs(_x0(value) - lx)
            if 0 < dy <= LEVEL_MAX_DY and dx <= LEVEL_MAX_DX and (best is None or dy < best[0]):
                best = (dy, value, m)
        if best is None:
            continue
        _, value, m = best
        sign = -1 if m.group(1) == "-" else 1
        mm = sign * (int(m.group(2)) * 1000 + int(m.group(3)))
        entities.append(
            Entity(
                kind=EntityKind.LEVEL,
                page_number=page.page_number,
                label=label.text,
                text=f"{label.text} {value.text}",
                value=float(mm),
                unit="mm",
                polygon=_union(label, value),
                confidence=0.95,
                layer=value.layer,
                attributes={"key": key},
            )
        )
    return entities


def extract_stair_flights(page: DrawingPage) -> list[Entity]:
    entities = []
    for t in page.texts:
        m = STAIR.search(t.text)
        if not m:
            continue
        count, step = int(m.group(1)), int(m.group(2))
        total = int(m.group(3)) if m.group(3) else None
        consistent = total is None or abs(count * step - total) <= count  # làm tròn khi ghi tổng
        entities.append(
            Entity(
                kind=EntityKind.STAIR_FLIGHT,
                page_number=page.page_number,
                text=t.text,
                value=float(step),
                unit="mm",
                polygon=t.polygon,
                confidence=0.95 if consistent else 0.6,
                layer=t.layer,
                # Cùng một chuỗi kích thước: các chữ thẳng hàng theo x (cùng cột).
                attributes={"count": count, "step": step, "total": total or count * step,
                            "chain": f"{page.page_number}:{round(_x0(t) / 4)}"},
            )
        )
    return entities


def extract_openings(page: DrawingPage) -> list[Entity]:
    sizes = sorted(((t, m) for t in page.texts if (m := OPENING_SIZE.match(t.text))), key=lambda p: _x0(p[0]))
    if not sizes:
        return []
    codes = [t for t in page.texts if OPENING_CODE.match(t.text) and _y0(t) < _y0(sizes[0][0])]
    location_label = next((t for t in page.texts if t.text.upper() == "VỊ TRÍ"), None)
    entities = []
    for i, (size, m) in enumerate(sizes):
        left = _x0(size) - CELL_MARGIN
        right = _x0(sizes[i + 1][0]) - CELL_MARGIN if i + 1 < len(sizes) else float("inf")
        in_cell = [t for t in page.texts if left <= _x0(t) < right]
        code = next((t for t in codes if left <= _x0(t) < right), None)
        description = " ".join(
            t.text for t in sorted(in_cell, key=_y0) if 0 < _y0(t) - _y0(size) <= CELL_TEXT_DEPTH
        )
        location = None
        if location_label is not None:
            location = next((t.text for t in in_cell if abs(_y0(t) - _y0(location_label)) < 3), None)
        width, height = int(m.group(1)), int(m.group(2))
        entities.append(
            Entity(
                kind=EntityKind.OPENING,
                page_number=page.page_number,
                label=code.text if code else None,
                text=size.text,
                values=[float(width), float(height)],
                unit="mm",
                polygon=size.polygon,
                confidence=0.9,
                layer=size.layer,
                attributes={"description": description, "location": location or "",
                            "width": width, "height": height,
                            **({"code_bbox": _bbox_str(code)} if code else {})},
            )
        )
    return entities


def extract_finish_tables(page: DrawingPage) -> tuple[list[Entity], set[int]]:
    """Bảng vật liệu hoàn thiện → mỗi mã một thực thể. PDF từ CAD không có "bảng" thật: chỉ là chữ đặt theo tọa độ,
    nên dựng lại từ mốc (tiêu đề chứa "VẬT LIỆU", đầu cột "KÝ HIỆU" / "MÔ TẢ") và ghép mô tả với mã gần nhất theo y.

    Trả thêm id các khối chữ đã thuộc bảng, để bộ trích ghi chú không lấy lại.
    """
    texts = [t for t in page.texts if abs(t.rotation) < 1]
    heads = [t for t in texts if _norm(t.text) == "KÝ HIỆU"]
    exterior = _exterior_hint(page)
    entities: list[Entity] = []
    used: set[int] = set()
    for head in heads:
        hx0, hy0, hx1, hy1 = _box(head)
        desc_head = min((t for t in texts if _norm(t.text) == "MÔ TẢ" and abs(_cy(t) - _cy(head)) < 3 and _box(t)[0] > hx1),
                        key=lambda t: _box(t)[0], default=None)
        if desc_head is None:
            continue
        dx = _box(desc_head)[0]
        right = dx + (dx - hx0) * FINISH_WIDTH_RATIO
        neighbour = [_box(t)[0] for t in heads if t is not head and abs(_cy(t) - _cy(head)) < 3 and _box(t)[0] > hx1]
        if neighbour:  # hai bảng đặt cạnh nhau (vd. PN2 trang 22)
            right = min(right, min(neighbour) - CALLOUT_STACK_DX)
        title_spans = [t for t in texts if 0 < hy0 - _box(t)[3] < FINISH_TITLE_GAP and hx0 - 2 * FINISH_CODE_SLACK < _box(t)[0] < right]
        title = " ".join(t.text.strip() for t in sorted(title_spans, key=lambda t: _box(t)[0]))
        if "VẬT LIỆU" not in title.upper():
            continue  # bảng đèn, chú thích ký hiệu…
        codes: list[TextSpan] = []
        last_y = hy1
        for t in sorted((t for t in texts if _box(t)[1] > hy1 and hx0 - FINISH_CODE_SLACK < _box(t)[0] < hx1 + FINISH_CODE_SLACK
                         and FINISH_CODE.match(t.text.strip())), key=_cy):
            if _cy(t) - last_y > FINISH_ROW_GAP:
                break
            codes.append(t)
            last_y = _cy(t)
        if not codes:
            continue
        code_ids = {id(c) for c in codes}
        rows: dict[int, list[TextSpan]] = {id(c): [] for c in codes}
        for t in texts:
            if id(t) in code_ids or not (hy1 < _cy(t) < last_y + FINISH_ROW_GAP / 2) or not (hx0 - FINISH_CODE_SLACK < _box(t)[0] < right):
                continue
            rows[id(min(codes, key=lambda c: abs(_cy(c) - _cy(t))))].append(t)
        surface = _surface(title)
        scope = "NGOẠI THẤT" if "NGOẠI THẤT" in title.upper() else exterior
        for code in codes:
            parts = sorted(rows[id(code)], key=lambda t: (round(_cy(t)), _box(t)[0]))
            description = " ".join(" ".join(t.text.split()) for t in parts)
            used.update(id(t) for t in (code, *parts))
            entities.append(Entity(
                kind=EntityKind.FINISH,
                page_number=page.page_number,
                label=code.text.strip(),
                text=f"{code.text.strip()} {description}".strip(),
                polygon=_union(code, *parts),
                confidence=0.9,
                layer=code.layer,
                attributes={"code": code.text.strip(), "description": description, "surface": surface,
                            "table": title, "exterior": scope},
            ))
        used.update(id(t) for t in (head, desc_head, *title_spans))
    return entities, used


def extract_callouts(page: DrawingPage, exclude: set[int] = frozenset()) -> list[Entity]:
    """Ghi chú vật liệu ngoài bảng (vd. "HỆ KHUNG TRẦN / TẤM CEMBOARD", "CHI TIẾT ĐÓNG TRẦN CEMBOARD ĐIỂN HÌNH").

    Một ghi chú CAD thường gồm vài dòng xếp chồng cùng lề trái → ghép các dòng sát nhau. Chưa lần theo đường dẫn
    (leader) tới đối tượng — bằng chứng là vị trí ghi chú.
    """
    texts = [t for t in page.texts if abs(t.rotation) < 1 and id(t) not in exclude]
    exterior = _exterior_hint(page)
    entities: list[Entity] = []
    seen: set[int] = set()
    for t in texts:
        upper = t.text.upper()
        surface = _surface(upper)
        if surface not in CALLOUT_SURFACES or CALLOUT_SKIP.search(upper) or id(t) in seen:
            continue
        block = _stack(t, texts)
        seen.update(id(b) for b in block)
        text = " ".join(" ".join(b.text.split()) for b in block)
        entities.append(Entity(
            kind=EntityKind.CALLOUT,
            page_number=page.page_number,
            text=text,
            polygon=_union(*block),
            confidence=0.8,
            layer=t.layer,
            attributes={"surface": surface, "exterior": exterior},
        ))
    return entities


def _stack(seed: TextSpan, texts: list[TextSpan]) -> list[TextSpan]:
    """Các dòng cùng lề trái, cùng layer, nằm sát ngay trên / dưới dòng gốc (tối đa 2 mỗi phía)."""
    block = [seed]
    for direction in (-1, 1):
        current = seed
        for _ in range(2):
            h = _box(current)[3] - _box(current)[1]
            nxt = min((t for t in texts if t.layer == current.layer and abs(_box(t)[0] - _box(current)[0]) <= CALLOUT_STACK_DX
                       and 0 < direction * (_cy(t) - _cy(current)) <= h * (1 + CALLOUT_STACK_GAP)),
                      key=lambda t: abs(_cy(t) - _cy(current)), default=None)
            if nxt is None:
                break
            block.append(nxt)
            current = nxt
    return sorted(block, key=_cy)


def _surface(text: str) -> str:
    upper = text.upper()
    return next((name for name, pattern in SURFACES if pattern.search(upper)), "")


def _exterior_hint(page: DrawingPage) -> str:
    """Từ khóa "ngoài nhà" đầu tiên xuất hiện trên trang ("" nếu không có) — gợi ý phạm vi, không phải kết luận."""
    for t in page.texts:
        m = EXTERIOR_HINTS.search(t.text.upper())
        if m:
            return m.group(0)
    return ""


def _norm(text: str) -> str:
    return " ".join(text.upper().split())


def _box(t: TextSpan) -> tuple[float, float, float, float]:
    xs = [p.x for p in t.polygon.points]
    ys = [p.y for p in t.polygon.points]
    return min(xs), min(ys), max(xs), max(ys)


def _cy(t: TextSpan) -> float:
    b = _box(t)
    return (b[1] + b[3]) / 2


def _level_key(text: str) -> str | None:
    s = " ".join(text.upper().split())
    for pattern, key in LEVEL_LABELS:
        m = pattern.match(s)
        if m:
            return key.format(*m.groups())
    return None


def _x0(t: TextSpan) -> float:
    return t.polygon.points[0].x


def _y0(t: TextSpan) -> float:
    return t.polygon.points[0].y


def _union(*texts: TextSpan) -> Polygon:
    xs = [p.x for t in texts for p in t.polygon.points]
    ys = [p.y for t in texts for p in t.polygon.points]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    return Polygon(
        points=[Point(x=x0, y=y0), Point(x=x1, y=y0), Point(x=x1, y=y1), Point(x=x0, y=y1)],
        precision=Precision.BBOX,
    )


def _bbox_str(t: TextSpan) -> str:
    xs = [p.x for p in t.polygon.points]
    ys = [p.y for p in t.polygon.points]
    return f"{min(xs):.2f},{min(ys):.2f},{max(xs):.2f},{max(ys):.2f}"
