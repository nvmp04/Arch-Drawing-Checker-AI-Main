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
# --- Bảng thống kê cấu tạo sàn: "KÍ HIỆU | VỊ TRÍ | CHI TIẾT | MÔ TẢ CÁC LỚP CẤU TẠO", mã F1.1, F2.2, F3.1 ---
ASSEMBLY_HEAD = "MÔ TẢ CÁC LỚP CẤU TẠO"
ASSEMBLY_CODE = re.compile(r"^[A-Z]{1,3}\d+(?:\.\d+)?$")
ASSEMBLY_END_GAP = 60.0  # point: hết dòng mô tả một quãng dài → hết bảng
# Một lớp cấu tạo có thể ghi trên nhiều dòng; dòng mở đầu lớp mới bắt đầu bằng các từ này, còn lại là dòng nối tiếp.
LAYER_START = re.compile(r"^(LỚP|SÀN|BẢN|ĐÁ|GẠCH|ĐẤT|HOÀN THIỆN|TRẦN|MÀNG)\b")
OPENING_GLASS = re.compile(r"kính[^0-9]*?dày\s*(\d+(?:[.,]\d+)?)\s*mm", re.IGNORECASE)


class ExtractionService:
    """v0: heuristic (regex + ghép theo tọa độ). v1: model trên đồ thị nét vẽ, train từ nhãn đã sửa."""

    def extract(self, page: DrawingPage) -> list[Entity]:
        return [*extract_levels(page), *extract_stair_flights(page), *extract_openings(page),
                *extract_finish_tables(page), *extract_floor_assemblies(page)]


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
        glass = OPENING_GLASS.search(description)
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
                            **({"glass_mm": float(glass.group(1).replace(",", "."))} if glass else {}),
                            **({"code_bbox": _bbox_str(code)} if code else {})},
            )
        )
    return entities


def extract_finish_tables(page: DrawingPage) -> list[Entity]:
    """Bảng vật liệu hoàn thiện → mỗi mã một thực thể. PDF từ CAD không có "bảng" thật: chỉ là chữ đặt theo tọa độ,
    nên dựng lại từ mốc (tiêu đề chứa "VẬT LIỆU", đầu cột "KÝ HIỆU" / "MÔ TẢ") và ghép mô tả với mã gần nhất theo y.
    """
    texts = [t for t in page.texts if abs(t.rotation) < 1]
    heads = [t for t in texts if _norm(t.text) == "KÝ HIỆU"]
    entities: list[Entity] = []
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
            right = min(right, min(neighbour) - 4.0)
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
        for code in codes:
            parts = sorted(rows[id(code)], key=lambda t: (round(_cy(t)), _box(t)[0]))
            description = " ".join(" ".join(t.text.split()) for t in parts)
            entities.append(Entity(
                kind=EntityKind.FINISH,
                page_number=page.page_number,
                label=code.text.strip(),
                text=f"{code.text.strip()} {description}".strip(),
                polygon=_union(code, *parts),
                confidence=0.9,
                layer=code.layer,
                attributes={"code": code.text.strip(), "description": description, "surface": surface, "table": title},
            ))
    return entities


def extract_floor_assemblies(page: DrawingPage) -> list[Entity]:
    """Bảng thống kê cấu tạo sàn → mỗi LỚP cấu tạo một thực thể, mang mã dòng, vị trí ("BAN CÔNG SÂN THƯỢNG…"), nhóm tầng.

    Dữ liệu chữ không có lưới bảng nên dựng từ mốc: đầu cột "MÔ TẢ CÁC LỚP CẤU TẠO", "VỊ TRÍ", "KÍ HIỆU";
    ranh giới giữa hai dòng bảng = khoảng hở lớn nhất giữa các dòng mô tả nằm giữa hai mã liên tiếp.
    """
    texts = [t for t in page.texts if abs(t.rotation) < 1]
    entities: list[Entity] = []
    for desc_head in (t for t in texts if _norm(t.text) == ASSEMBLY_HEAD):
        same_line = [t for t in texts if abs(_cy(t) - _cy(desc_head)) < 4 and _box(t)[0] < _box(desc_head)[0]]

        def head(*names: str) -> TextSpan | None:
            return max((t for t in same_line if _norm(t.text) in names), key=lambda t: _box(t)[0], default=None)

        code_head, loc_head, detail_head = head("KÍ HIỆU", "KÝ HIỆU"), head("VỊ TRÍ"), head("CHI TIẾT")
        if code_head is None or loc_head is None:
            continue
        top = _box(desc_head)[3]
        kx, lx, dx = _box(code_head)[0], _box(loc_head)[0], _box(desc_head)[0]
        loc_right = _box(detail_head)[0] if detail_head else dx
        codes = sorted((t for t in texts if _box(t)[1] > top and kx - 20 < _box(t)[0] < lx - 10
                        and ASSEMBLY_CODE.match(t.text.strip())), key=_cy)
        lines = sorted((t for t in texts if _box(t)[1] > top and dx - 30 <= _box(t)[0] <= dx + 80
                        and any(ch.isalnum() for ch in t.text)), key=_cy)  # bỏ dấu gạch đầu dòng "·"
        if not codes or not lines:
            continue
        size = lines[0].size or 0.0
        body: list[TextSpan] = []
        for t in lines:  # dừng ở cuối bảng: quãng trống dài sau mã cuối; bỏ chữ khác cỡ (tiêu đề bảng khác)
            if body and _cy(t) - _cy(body[-1]) > ASSEMBLY_END_GAP and _cy(t) > _cy(codes[-1]):
                break
            if size and t.size and abs(t.size - size) > 0.2 * size:
                continue
            body.append(t)
        rows = _split_rows(codes, body)
        extents = {id(c): (min([_box(c)[1]] + [_box(t)[1] for t in rows[id(c)]]),
                           max([_box(c)[3]] + [_box(t)[3] for t in rows[id(c)]])) for c in codes}
        bottom = max(e[1] for e in extents.values()) + ASSEMBLY_END_GAP / 2
        locations: dict[int, list[TextSpan]] = {id(c): [] for c in codes}
        for t in texts:
            if top < _box(t)[1] < bottom and lx - 45 < _box(t)[0] < loc_right - 20 and not any(t is c for c in codes):
                row = min(codes, key=lambda c: max(extents[id(c)][0] - _cy(t), _cy(t) - extents[id(c)][1], 0.0))
                locations[id(row)].append(t)
        groups = [t for t in texts if top < _box(t)[1] < bottom and kx - 90 < _box(t)[0] < kx - 20]
        for code in codes:
            lo, hi = extents[id(code)]
            group = min(groups, key=lambda g: abs(_cy(g) - (lo + hi) / 2), default=None)
            location = " ".join(t.text.strip() for t in sorted(locations[id(code)], key=_cy))
            for order, layer in enumerate(_layers(rows[id(code)])):
                entities.append(Entity(
                    kind=EntityKind.TABLE_ROW,
                    page_number=page.page_number,
                    label=code.text.strip(),
                    text=" ".join(" ".join(t.text.split()) for t in layer),
                    polygon=_union(*layer),
                    confidence=0.9,
                    layer=layer[0].layer,
                    attributes={"table": "floor-assembly", "code": code.text.strip(), "location": location,
                                "group": group.text.strip() if group else "", "order": order},
                ))
    return entities


def _split_rows(codes: list[TextSpan], lines: list[TextSpan]) -> dict[int, list[TextSpan]]:
    """Chia các dòng mô tả cho từng mã: ranh giới = khoảng hở lớn nhất giữa hai mã liên tiếp."""
    rows: dict[int, list[TextSpan]] = {}
    start = 0
    for i, code in enumerate(codes):
        if i + 1 == len(codes):
            rows[id(code)] = lines[start:]
            break
        # Xét từ dòng đầu tiên ngang / dưới mã này tới dòng đầu tiên ngang / dưới mã kế tiếp.
        first = next((j for j in range(start, len(lines)) if _cy(lines[j]) >= _cy(code)), len(lines))
        last = next((j for j in range(start, len(lines)) if _cy(lines[j]) >= _cy(codes[i + 1])), len(lines) - 1)
        candidates = range(max(first, start + 1), last + 1)
        cut = max(candidates, key=lambda j: _cy(lines[j]) - _cy(lines[j - 1]), default=last + 1)
        rows[id(code)] = lines[start:cut]
        start = cut
    return rows


def _layers(lines: list[TextSpan]) -> list[list[TextSpan]]:
    layers: list[list[TextSpan]] = []
    for t in sorted(lines, key=_cy):
        if layers and not LAYER_START.match(t.text.strip().upper()):
            layers[-1].append(t)
        else:
            layers.append([t])
    return layers


def _surface(text: str) -> str:
    upper = text.upper()
    return next((name for name, pattern in SURFACES if pattern.search(upper)), "")


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
