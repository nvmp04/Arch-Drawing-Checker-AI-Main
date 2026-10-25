"""Nhận bảng từ lưới kẻ của PDF vector (drawing-knowledge.md §3.3) — kiểu "lattice": chỉ dựa vào nét kẻ.

1. Lấy các đoạn ngang / dọc từ mọi nét (kể cả cạnh của hình chữ nhật kín — nhiều bảng vẽ ô bằng hình chữ nhật).
   Không lọc theo layer: trên PN2 lưới bảng nằm ở `0`, `A-DETL-LLIN`, `A-Door`… (layer chỉ là gợi ý, §1).
2. Nối đoạn thẳng hàng sát nhau; gom các đường ngang + dọc cắt nhau thành cụm lưới.
3. Mỗi cụm → lưới ô cơ sở theo các vị trí đường kẻ; hai ô kề nhau thiếu nét ngăn → gộp (ô gộp). Vùng gộp không
   phải hình chữ nhật, hoặc thiếu viền ngoài → không phải ô (khoảng trống quanh bảng hình chữ L…).
4. Chữ thuộc ô nhỏ nhất chứa tâm của nó. Chỉ giữ cụm có đủ ô chứa chữ — loại lưới do mặt đứng, cửa sổ, trục,
   hatch tạo ra.

Thuần hình học, không phụ thuộc bộ tiêu chí (D-18). Tọa độ: point trang đã xoay.
"""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass

from drawing_checker.common.geometry import Polygon
from drawing_checker.features.geometry.schemas import Table, TableCell
from drawing_checker.features.ingest.schemas import TextSpan, VectorPath

AXIS_TOLERANCE = 0.3  # pt: đoạn coi là ngang / dọc khi hai đầu lệch ít hơn
MIN_SEGMENT = 2.0  # pt: bỏ đoạn quá ngắn (đầu mũi tên, ký hiệu, nét chữ vẽ bằng đường)
JOIN_GAP = 1.0  # pt: nối hai đoạn thẳng hàng hở ít hơn (CAD hay cắt đường kẻ ở giao điểm)
SNAP = 1.0  # pt: hai đường song song gần hơn coi là một (nét đôi, sai số làm tròn)
TOUCH = 1.0  # pt: đường ngang và dọc coi là cắt / chạm nhau
COVER = 0.8  # cạnh ô phải có nét kẻ phủ ít nhất tỉ lệ này
MIN_CELL = 1.5  # pt: khoảng giữa hai đường kẻ nhỏ hơn → không phải ô (nét đôi của viền đậm)
MAX_GRID = 40_000  # số ô cơ sở tối đa của một cụm — lớn hơn là lưới hatch / mặt đứng, không phải bảng
MIN_TEXT_CELLS = 4  # bảng phải có ít nhất chừng này ô chứa chữ
MIN_TEXT_ROWS = 2
MAX_TEXTS_PER_CELL_SHARE = 0.6  # một ô chứa quá nửa chữ của "bảng" → đó là khung bản vẽ, không phải bảng
MIN_FILLED_RATIO = 0.3  # tỉ lệ ô có chữ tối thiểu — lưới do tường / mặt đứng tạo ra phần lớn ô trống (PN2: 5–18%)
MAX_CELL_PAGE_SHARE = 0.1  # "ô" lớn hơn tỉ lệ này của trang là vùng vẽ trong khung trang, không phải ô bảng


@dataclass(slots=True)
class _Line:
    pos: float  # y của đường ngang / x của đường dọc
    lo: float
    hi: float


def detect_tables(
    page_number: int, paths: list[VectorPath], texts: list[TextSpan], page_size: tuple[float, float] | None = None,
) -> list[Table]:
    """Các bảng có lưới kẻ trên trang, kèm chữ trong từng ô. Thứ tự: trên → dưới, trái → phải."""
    horizontal, vertical = _segments(paths)
    horizontal, vertical = _merge(horizontal), _merge(vertical)
    max_cell = MAX_CELL_PAGE_SHARE * page_size[0] * page_size[1] if page_size else float("inf")
    candidates = [g for hs, vs in _components(horizontal, vertical) if (g := _grid(hs, vs, max_cell)) is not None]
    if not candidates:
        return []
    centers = [_center(t) for t in texts]
    # Chữ thuộc ô nhỏ nhất chứa tâm (bảng lồng trong khung lớn hơn).
    owner: dict[int, tuple[int, int]] = {}
    for ti, (cx, cy) in enumerate(centers):
        best = None
        for gi, grid in enumerate(candidates):
            x0, y0, x1, y1 = grid.box
            if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                continue
            for ci, (cx0, cy0, cx1, cy1) in enumerate(grid.cell_boxes):
                if cx0 <= cx <= cx1 and cy0 <= cy <= cy1:
                    area = (cx1 - cx0) * (cy1 - cy0)
                    if best is None or area < best[0]:
                        best = (area, gi, ci)
        if best is not None:
            owner[ti] = (best[1], best[2])
    tables = []
    for gi, grid in enumerate(candidates):
        members: dict[int, list[int]] = {}
        for ti, (g, ci) in owner.items():
            if g == gi:
                members.setdefault(ci, []).append(ti)
        table = _table(page_number, grid, members, texts)
        if table is not None:
            tables.append(table)
    return sorted(tables, key=lambda t: (_poly_box(t.polygon)[1], _poly_box(t.polygon)[0]))


# --- 1. đoạn thẳng -------------------------------------------------------------------------------------------


def _segments(paths: list[VectorPath]) -> tuple[list[_Line], list[_Line]]:
    horizontal: list[_Line] = []
    vertical: list[_Line] = []
    for path in paths:
        points = path.points
        if path.closed and points and points[0] != points[-1]:
            points = [*points, points[0]]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if abs(y0 - y1) <= AXIS_TOLERANCE and abs(x1 - x0) >= MIN_SEGMENT:
                horizontal.append(_Line((y0 + y1) / 2, min(x0, x1), max(x0, x1)))
            elif abs(x0 - x1) <= AXIS_TOLERANCE and abs(y1 - y0) >= MIN_SEGMENT:
                vertical.append(_Line((x0 + x1) / 2, min(y0, y1), max(y0, y1)))
    return horizontal, vertical


def _merge(lines: list[_Line]) -> list[_Line]:
    """Nối các đoạn cùng đường (lệch ≤ SNAP) chồng hoặc hở ≤ JOIN_GAP."""
    lines = sorted(lines, key=lambda s: (s.pos, s.lo))
    out: list[_Line] = []
    band: list[_Line] = []
    for line in lines:
        if band and line.pos - band[0].pos > SNAP:
            out.extend(_join(band))
            band = []
        band.append(line)
    if band:
        out.extend(_join(band))
    return out


def _join(band: list[_Line]) -> list[_Line]:
    pos = sum(s.pos for s in band) / len(band)
    out: list[_Line] = []
    for s in sorted(band, key=lambda s: s.lo):
        if out and s.lo <= out[-1].hi + JOIN_GAP:
            out[-1].hi = max(out[-1].hi, s.hi)
        else:
            out.append(_Line(pos, s.lo, s.hi))
    return out


# --- 2. cụm lưới ---------------------------------------------------------------------------------------------


def _components(horizontal: list[_Line], vertical: list[_Line]) -> list[tuple[list[_Line], list[_Line]]]:
    """Gom đường ngang + dọc cắt / chạm nhau (union-find). Chỉ giữ cụm đủ để thành ô."""
    vertical = sorted(vertical, key=lambda s: s.pos)
    xs = [v.pos for v in vertical]
    n_h = len(horizontal)
    parent = list(range(n_h + len(vertical)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for hi_, h in enumerate(horizontal):
        for vi in range(bisect_left(xs, h.lo - TOUCH), bisect_right(xs, h.hi + TOUCH)):
            v = vertical[vi]
            if v.lo - TOUCH <= h.pos <= v.hi + TOUCH:
                a, b = find(hi_), find(n_h + vi)
                if a != b:
                    parent[a] = b
    groups: dict[int, tuple[list[_Line], list[_Line]]] = {}
    for i, h in enumerate(horizontal):
        groups.setdefault(find(i), ([], []))[0].append(h)
    for i, v in enumerate(vertical):
        groups.setdefault(find(n_h + i), ([], []))[1].append(v)
    return [(hs, vs) for hs, vs in groups.values() if len(hs) >= 3 and len(vs) >= 2]


# --- 3. ô ----------------------------------------------------------------------------------------------------


@dataclass
class _Grid:
    box: tuple[float, float, float, float]
    xs: list[float]
    ys: list[float]
    cells: list[tuple[int, int, int, int]]  # (cột, hàng, số cột gộp, số hàng gộp)
    cell_boxes: list[tuple[float, float, float, float]]


def _grid(horizontal: list[_Line], vertical: list[_Line], max_cell_area: float) -> _Grid | None:
    ys = _snap([h.pos for h in horizontal])
    xs = _snap([v.pos for v in vertical])
    n_cols, n_rows = len(xs) - 1, len(ys) - 1
    if n_cols < 1 or n_rows < 2 or n_cols * n_rows > MAX_GRID:
        return None
    h_by = _by_position(horizontal, ys)
    v_by = _by_position(vertical, xs)

    def has_h(j: int, x0: float, x1: float) -> bool:
        return _covered(h_by.get(j, []), x0, x1)

    def has_v(i: int, y0: float, y1: float) -> bool:
        return _covered(v_by.get(i, []), y0, y1)

    parent = list(range(n_cols * n_rows))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for j in range(n_rows):
        for i in range(n_cols):
            k = j * n_cols + i
            if i + 1 < n_cols and not has_v(i + 1, ys[j], ys[j + 1]):
                union(k, k + 1)
            if j + 1 < n_rows and not has_h(j + 1, xs[i], xs[i + 1]):
                union(k, k + n_cols)
    regions: dict[int, list[int]] = {}
    for k in range(n_cols * n_rows):
        regions.setdefault(find(k), []).append(k)

    cells: list[tuple[int, int, int, int]] = []
    boxes: list[tuple[float, float, float, float]] = []
    for members in regions.values():
        cols = [k % n_cols for k in members]
        rows = [k // n_cols for k in members]
        i0, i1, j0, j1 = min(cols), max(cols) + 1, min(rows), max(rows) + 1
        if (i1 - i0) * (j1 - j0) != len(members):
            continue  # vùng gộp không phải hình chữ nhật
        x0, x1, y0, y1 = xs[i0], xs[i1], ys[j0], ys[j1]
        if x1 - x0 < MIN_CELL or y1 - y0 < MIN_CELL or (x1 - x0) * (y1 - y0) > max_cell_area:
            continue
        if not (has_h(j0, x0, x1) and has_h(j1, x0, x1) and has_v(i0, y0, y1) and has_v(i1, y0, y1)):
            continue  # thiếu viền: khoảng trống quanh bảng, không phải ô
        cells.append((i0, j0, i1 - i0, j1 - j0))
        boxes.append((x0, y0, x1, y1))
    if len(cells) < MIN_TEXT_CELLS:
        return None
    order = sorted(range(len(cells)), key=lambda c: (cells[c][1], cells[c][0]))
    return _Grid(
        box=(xs[0], ys[0], xs[-1], ys[-1]), xs=xs, ys=ys,
        cells=[cells[c] for c in order], cell_boxes=[boxes[c] for c in order],
    )


def _snap(values: list[float]) -> list[float]:
    out: list[list[float]] = []
    for v in sorted(values):
        if out and v - out[-1][-1] <= SNAP:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(g) / len(g) for g in out]


def _by_position(lines: list[_Line], positions: list[float]) -> dict[int, list[tuple[float, float]]]:
    out: dict[int, list[tuple[float, float]]] = {}
    for line in lines:
        i = min(range(len(positions)), key=lambda k: abs(positions[k] - line.pos))
        if abs(positions[i] - line.pos) <= SNAP:
            out.setdefault(i, []).append((line.lo, line.hi))
    return out


def _covered(spans: list[tuple[float, float]], lo: float, hi: float) -> bool:
    length = hi - lo
    if length <= 0:
        return False
    total, end = 0.0, lo
    for a, b in sorted(spans):
        a, b = max(a, end), min(b, hi)
        if b > a:
            total += b - a
            end = b
    return total >= COVER * length - TOUCH


# --- 4. chữ trong ô ------------------------------------------------------------------------------------------


def _table(page_number: int, grid: _Grid, members: dict[int, list[int]], texts: list[TextSpan]) -> Table | None:
    filled = [c for c in range(len(grid.cells)) if members.get(c)]
    if len(filled) < MIN_TEXT_CELLS or len(filled) < MIN_FILLED_RATIO * len(grid.cells):
        return None
    worded = [c for c in filled if any(ch.isalpha() for t in members[c] for ch in texts[t].text)]
    if len(worded) < MIN_TEXT_CELLS:
        return None  # toàn số: dải số kích thước chồng nhau (PN2 trang 46), không phải bảng
    if len({grid.cells[c][1] for c in filled}) < MIN_TEXT_ROWS:
        return None
    total = sum(len(members[c]) for c in filled)
    if max(len(members[c]) for c in filled) > MAX_TEXTS_PER_CELL_SHARE * total:
        return None  # một ô ôm gần hết chữ → khung bản vẽ / khung tên bao cả hình
    cells = []
    for c, (i, j, ci, cj) in enumerate(grid.cells):
        x0, y0, x1, y1 = grid.cell_boxes[c]
        ordered = sorted(members.get(c, []), key=lambda t: (_center(texts[t])[1], _center(texts[t])[0], t))
        cells.append(TableCell(row=j, col=i, row_span=cj, col_span=ci,
                               polygon=Polygon.from_bbox(x0, y0, x1 - x0, y1 - y0), text_indices=ordered))
    x0, y0, x1, y1 = grid.box
    return Table(page_number=page_number, polygon=Polygon.from_bbox(x0, y0, x1 - x0, y1 - y0),
                 rows=len(grid.ys) - 1, cols=len(grid.xs) - 1, cells=cells)


def _center(t: TextSpan) -> tuple[float, float]:
    x, y, w, h = t.polygon.bounding_box()
    return x + w / 2, y + h / 2


def _poly_box(p: Polygon) -> tuple[float, float, float, float]:
    return p.bounding_box()
