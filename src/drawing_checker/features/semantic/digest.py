"""Bản tóm tắt hồ sơ gửi AI: chữ vector có mã khối, theo trang, kèm khung tên + tiêu đề hình + layer (gợi ý).

Không gửi ảnh, không gửi tọa độ (D-22). AI trích dẫn bằng MÃ KHỐI CHỮ ("p5-12"); code tra mã → trang + polygon
để làm bằng chứng — AI không bịa được bằng chứng. Thứ tự và định dạng cố định (cùng hồ sơ → cùng chuỗi) để
prompt caching dùng lại được và để đo độ ổn định.

Quy ước thể hiện bản vẽ: docs/drawing-knowledge.md. Không chứa gì về câu tiêu chí (D-18).
"""

import re
from dataclasses import dataclass, field

from drawing_checker.common.geometry import Polygon
from drawing_checker.features.geometry.schemas import Table
from drawing_checker.features.ingest.schemas import TextSpan
from drawing_checker.features.sheets.schemas import DocumentIndex

# Khối chỉ gồm số / dấu (giá trị kích thước "4650", cao độ trần "+3.600", "1/100") — vô nghĩa khi tách khỏi hình,
# chiếm ~nửa số khối. Phần số do rule engine (checker số) xử lý. Bật include_numeric để gửi cả.
NUMERIC_ONLY = re.compile(r"^[\d\s.,:;+\-±xX×/%()@Øø]*$")
ROW_TOLERANCE = 0.6  # × cỡ chữ: hai khối cùng "dòng đọc" khi tâm lệch dọc ít hơn
# Tách vùng kiểu XY-cut: khoảng trống ≥ GAP × cỡ chữ trung vị chia trang thành cột / dải → hai bảng đặt cạnh nhau
# không bị đọc xen hàng. Chỉ dựa vào vị trí chữ (chưa dùng đường kẻ — việc của `geometry`, drawing-knowledge §3.3).
# Cắt cột cần khe rộng hơn hẳn cắt dải ngang: khe giữa các cột TRONG một bảng không được tách bảng thành từng cột.
REGION_GAP_ROWS = 4.0
REGION_GAP_COLUMNS = 8.0  # đo trên PN2 trang 5: 12 làm hai bảng cạnh nhau đọc xen hàng, 6–8 tách đúng
XREF_PREFIX = re.compile(r"^.*\|")  # "xr-se|A-dim" → "A-dim"


@dataclass(slots=True)
class TextBlock:
    id: str  # "p5-12": trang 5, khối thứ 12 của trang (thứ tự đọc của PageReader)
    page_number: int
    text: str
    polygon: Polygon
    layer: str | None = None


@dataclass
class DossierDigest:
    text: str  # chuỗi gửi AI
    blocks: dict[str, TextBlock] = field(default_factory=dict)  # mọi khối có mã (kể cả khối số bị lược)
    stats: dict[str, int] = field(default_factory=dict)


def block_id(page_number: int, index: int) -> str:
    return f"p{page_number}-{index}"


def build_digest(
    pages: list[tuple[int, list[TextSpan]]], index: DocumentIndex, include_numeric: bool = False,
    tables: dict[int, list[Table]] | None = None,
) -> DossierDigest:
    """pages: (số trang, chữ trong vùng hiển thị) theo thứ tự trang.

    tables: bảng nhận từ lưới kẻ (`geometry`) theo trang. Có thì chữ trong bảng in theo hàng / ô (ô nhiều dòng
    không còn xen với ô bên cạnh); None = chỉ dựa vào vị trí chữ như trước (mốc so sánh).
    """
    blocks: dict[str, TextBlock] = {}
    layer_codes: dict[str, str] = {}
    sheets = {s.page_number: s for s in index.sheets}
    page_sections: list[str] = []
    sent = skipped = tables_sent = 0

    def keep(content: str) -> bool:
        nonlocal skipped
        if not any(ch.isalnum() for ch in content):
            return False
        if not include_numeric and NUMERIC_ONLY.match(content):
            skipped += 1
            return False
        return True

    for page_number, texts in sorted(pages, key=lambda p: p[0]):
        lines: list[str] = []
        view_titles = {v.title for v in sheets[page_number].views} if page_number in sheets else set()
        for i, t in enumerate(texts):
            blocks[block_id(page_number, i)] = TextBlock(block_id(page_number, i), page_number, t.text, t.polygon, t.layer)
        page_tables = (tables or {}).get(page_number, [])
        in_table = {i for table in page_tables for cell in table.cells for i in cell.text_indices}
        free = [(i, t) for i, t in enumerate(texts) if i not in in_table]
        for region_no, region in enumerate(_regions_of(free)):
            if region_no and lines and lines[-1]:
                lines.append("")  # dòng trống = sang vùng khác của trang
            for i, t in region:
                content = " ".join(t.text.split())
                if not keep(content):
                    continue
                layer = _layer_code(t.layer, layer_codes)
                mark = " ==" if _is_view_title(content, view_titles) else ""
                lines.append(f"{block_id(page_number, i)} {layer}{mark} {content}")
                sent += 1
        for table in page_tables:
            rows: dict[int, list[str]] = {}
            for cell in sorted(table.cells, key=lambda c: (c.row, c.col)):
                parts = []
                for i in cell.text_indices:
                    content = " ".join(texts[i].text.split())
                    if keep(content):
                        parts.append(f"{block_id(page_number, i)} {content}")
                        sent += 1
                if parts:
                    span = (f"+{cell.col_span - 1}" if cell.col_span > 1 else "") + \
                           (f"↓{cell.row_span}" if cell.row_span > 1 else "")
                    rows.setdefault(cell.row, []).append(f"C{cell.col + 1}{span}: " + "; ".join(parts))
            if not rows:
                continue
            tables_sent += 1
            if lines and lines[-1]:
                lines.append("")
            lines.append(f"[BẢNG {tables_sent}]")
            lines.extend(f"H{row + 1}| " + " | ".join(cells) for row, cells in sorted(rows.items()))
        while lines and not lines[-1]:
            lines.pop()
        page_sections.append(_page_header(page_number, sheets.get(page_number)) + "\n" + "\n".join(lines))

    header = _dossier_header(index, layer_codes, tables_sent > 0)
    stats = {"pages": len(pages), "blocksSent": sent, "blocksSkippedNumeric": skipped, "layers": len(layer_codes),
             "tables": tables_sent}
    return DossierDigest(text=header + "\n\n" + "\n\n".join(page_sections), blocks=blocks, stats=stats)


Item = tuple[int, TextSpan]


def _regions(texts: list[TextSpan]) -> list[list[Item]]:
    return _regions_of(list(enumerate(texts)))


def _regions_of(items: list[Item]) -> list[list[Item]]:
    """Chia trang thành các vùng chữ (XY-cut đệ quy), mỗi vùng xếp theo thứ tự đọc. Ổn định với cùng đầu vào."""
    if not items:
        return []
    sizes = sorted(t.size or 2.5 for _, t in items)
    median = sizes[len(sizes) // 2]
    gaps = (max(15.0, median * REGION_GAP_COLUMNS), max(6.0, median * REGION_GAP_ROWS))
    out: list[list[Item]] = []
    _cut(items, gaps, out, depth=0)
    return out


def _cut(items: list[Item], gaps: tuple[float, float], out: list[list[Item]], depth: int) -> None:
    if len(items) > 1 and depth < 12:
        best = None
        for axis in (0, 1):  # 0: cắt theo cột (khoảng trống dọc), 1: cắt theo dải ngang
            groups, widest = _split(items, axis, gaps[axis])
            # So khe theo tỉ lệ với ngưỡng của trục — khe cột phải "rộng tương xứng" mới thắng khe dải.
            if len(groups) > 1 and (best is None or widest / gaps[axis] > best[1]):
                best = (groups, widest / gaps[axis])
        if best is not None:
            for group in best[0]:
                _cut(group, gaps, out, depth + 1)
            return
    out.append(_reading_order(items))


def _split(items: list[Item], axis: int, gap: float) -> tuple[list[list[Item]], float]:
    """Gom khối thành nhóm ngăn cách bởi khoảng trống ≥ gap theo trục; trả (các nhóm theo thứ tự, khe lớn nhất)."""
    spans = sorted(((_box(t)[axis], _box(t)[axis + 2], item) for item in items for t in [item[1]]),
                   key=lambda s: (s[0], s[1], s[2][0]))
    groups: list[list[Item]] = [[spans[0][2]]]
    end, widest = spans[0][1], 0.0
    for lo, hi, item in spans[1:]:
        if lo - end >= gap:
            widest = max(widest, lo - end)
            groups.append([])
        groups[-1].append(item)
        end = max(end, hi)
    return groups, widest


def _box(t: TextSpan) -> tuple[float, float, float, float]:
    xs = [p.x for p in t.polygon.points]
    ys = [p.y for p in t.polygon.points]
    return min(xs), min(ys), max(xs), max(ys)


def _reading_order(items: list[Item]) -> list[Item]:
    """Trên → dưới, trái → phải trong một vùng; hàng của bảng giữ liền nhau."""

    def key(item: Item) -> tuple[float, float, int]:
        i, t = item
        x0, y0, _, y1 = _box(t)
        band = max(1.0, (t.size or 2.5) * ROW_TOLERANCE * 2)
        return (round((y0 + y1) / 2 / band), x0, i)

    return sorted(items, key=key)


def _layer_code(layer: str | None, codes: dict[str, str]) -> str:
    if not layer:
        return "L-"
    if layer not in codes:
        codes[layer] = f"L{len(codes) + 1}"
    return codes[layer]


def _is_view_title(content: str, titles: set[str]) -> bool:
    return content in titles


def _page_header(page_number: int, sheet) -> str:
    parts = [f"### TRANG {page_number}"]
    tb = sheet.title_block if sheet else None
    if tb:
        for label, value in (("tên", tb.name), ("số hiệu", tb.number), ("tỉ lệ", tb.scale), ("hạng mục", tb.item)):
            if value:
                parts.append(f"{label}: {value}")
    else:
        parts.append("(không đọc được khung tên)")
    if sheet and sheet.views:
        titles = "; ".join(f"{v.title}" + (f" [TL 1/{v.scale_denominator}]" if v.scale_denominator else "")
                           for v in sheet.views)
        parts.append(f"hình/bảng: {titles}")
    return " | ".join(parts)


def _dossier_header(index: DocumentIndex, layer_codes: dict[str, str], has_tables: bool = False) -> str:
    p = index.profile
    out = ["## ĐẶC ĐIỂM HỒ SƠ (đọc tự động từ bản vẽ, có thể thiếu)"]
    out.append(f"số trang: {p.page_count}; hạng mục: {', '.join(p.items) or '?'}; công trình: {p.project or '?'}; "
               f"giai đoạn: {p.phase or '?'}")
    out.append(f"tầng có nhãn cao độ: {p.storeys or '?'}; có hầm: {'có' if p.has_basement else 'không thấy'}; "
               f"có tum: {'có' if p.has_attic else 'không thấy'}")
    if p.levels:
        out.append("cao độ (mm): " + ", ".join(f"{k}={v:g}" for k, v in sorted(p.levels.items())))
    if index.abbreviations:
        out.append("\n## BẢNG VIẾT TẮT CỦA HỒ SƠ")
        out.append("; ".join(f"{a.abbr} = {a.meaning}" for a in index.abbreviations))
    out.append("\n## LAYER CAD (tên layer chỉ là GỢI Ý, có thể sai — không kết luận chỉ dựa vào tên layer)")
    out.append("; ".join(f"{code}={XREF_PREFIX.sub('', name)}" for name, code in layer_codes.items()))
    out.append("\n## CHỮ TRÊN BẢN VẼ")
    out.append("Mỗi dòng: <mã khối> <mã layer> [== nếu là tiêu đề hình/bảng] <nội dung>. "
               "Khối xếp theo thứ tự đọc trên → dưới, trái → phải; khối chỉ gồm số (kích thước) đã lược.")
    if has_tables:
        out.append("Bảng nhận từ đường kẻ trên bản vẽ in sau phần chữ của trang: \"[BẢNG n]\" rồi mỗi dòng một hàng "
                   "\"H<hàng>| C<cột>: <mã khối> <nội dung>; … | C<cột>: …\" (không có mã layer). Ô gộp: "
                   "\"C2+1\" = trải thêm 1 cột, \"C1↓4\" = trải 4 hàng — nội dung ô gộp áp dụng cho mọi hàng nó trải "
                   "qua. Hàng tiêu đề thường là hàng đầu. Mọi khối chữ của một ô liền nhau theo thứ tự đọc.")
    return "\n".join(out)
