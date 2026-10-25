"""Đọc PDF vector bằng PyMuPDF: chữ (kèm layer CAD) và nét vẽ. Không OCR (D-03).

- Chữ lấy qua `get_texttrace()` (không phải `get_text`) vì chỉ texttrace mang tên layer CAD.
  Đã đối chiếu trên bộ mẫu PN2: cùng nội dung ký tự với `get_text("dict")` (research-log §6).
- Nét vẽ lấy qua `get_cdrawings()` (nhanh ~3× `get_drawings`), tách thành các nét liền.
"""

import math
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

import pymupdf

from drawing_checker.common.geometry import Point, Polygon, Precision
from drawing_checker.features.ingest.schemas import DrawingDocument, DrawingPage, TextSpan, VectorPath
from drawing_checker.features.ingest.vni import decode_vni, is_vni_font

BEZIER_SEGMENTS = 8  # số đoạn thẳng thay cho một đường cong Bézier
# Khoảng trắng đặc biệt (NBSP…) do bảng mã font → khoảng trắng thường, để regex bước trích xuất đơn giản.
# Chữ còn được chuẩn hóa NFC: một số font CAD ghi dấu tiếng Việt dạng tổ hợp ("O" + dấu sắc rời, PN2 trang 6).
# Nối các lượt vẽ chữ của cùng một dòng (đơn vị: × cỡ chữ). Khoảng hở = từ mép cuối ký tự trước tới mép đầu ký tự sau.
SPLIT_MAX_GAP = 0.5  # rộng hơn một dấu cách → là hai dòng chữ khác nhau (ô bảng kế bên, số kích thước…)
SPLIT_MAX_OVERLAP = 0.3
SPLIT_SPACE_GAP = 0.15  # hở từ mức này → có một dấu cách bị lược
SPLIT_MAX_OFFSET = 0.3  # lệch khỏi dòng
SPLIT_SIZE_TOLERANCE = 0.15
_SPACES = str.maketrans({"\u00a0": " ", "\u2007": " ", "\u202f": " ", "\u3000": " "})


class IngestError(Exception):
    """PDF không đọc được. `str(exc)` là thông báo tiếng Việt cho người dùng."""


class IngestService:
    def count_pages(self, pdf_path: Path) -> int:
        """Mở PDF và đếm trang — đủ cho bắt tay v0 (báo pageCount ở bước extract)."""
        with _open(pdf_path) as doc:
            return doc.page_count

    def open(self, pdf_path: Path) -> DrawingDocument:
        """Đọc siêu dữ liệu + chữ của mọi trang (PyMuPDF). Nét vẽ nạp riêng bằng `load_paths`."""
        with _open(pdf_path) as doc:
            return DrawingDocument(page_count=doc.page_count, pages=[_read_page(page) for page in doc])

    def load_text(self, pdf_path: Path, page_number: int) -> DrawingPage:
        """Chữ của một trang (không có nét vẽ)."""
        with _open(pdf_path) as doc:
            return _read_page(_get_page(doc, page_number))

    def reader(self, pdf_path: Path) -> "PageReader":
        """Mở PDF một lần để đọc lần lượt từng trang (pipeline của job). Dùng với `with`."""
        return PageReader(_open(pdf_path))

    def load_paths(self, pdf_path: Path, page_number: int) -> DrawingPage:
        """Nạp nét vẽ của một trang khi cần (trang nặng hàng trăm nghìn nét). Không kèm chữ."""
        with _open(pdf_path) as doc:
            page = _get_page(doc, page_number)
            result = _page_shell(page)
            result.paths = extract_paths(page)
            return result


class PageReader:
    """Giữ PDF mở trong suốt job; `read(n)` trả chữ + nét vẽ + thời gian trích của trang n."""

    def __init__(self, doc: pymupdf.Document) -> None:
        self._doc = doc
        self.page_count = doc.page_count

    def read(self, page_number: int) -> DrawingPage:
        page = _get_page(self._doc, page_number)
        result = _page_shell(page)
        t0 = time.perf_counter()
        result.texts, result.margin_texts = extract_all_texts(page)
        t1 = time.perf_counter()
        result.paths = extract_paths(page)
        t2 = time.perf_counter()
        result.timings = {"textMs": round((t1 - t0) * 1000), "pathsMs": round((t2 - t1) * 1000)}
        return result

    def render_jpeg(self, page_number: int, dpi: int) -> bytes:
        """Ảnh trang — CHỈ cho viewer debug (D-07: MAIN không trả ảnh cho BE)."""
        return _get_page(self._doc, page_number).get_pixmap(dpi=dpi).tobytes("jpeg", jpg_quality=80)

    def close(self) -> None:
        self._doc.close()

    def __enter__(self) -> "PageReader":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _open(pdf_path: Path) -> pymupdf.Document:
    # Mở từ bytes: PyMuPDF lỗi khi mở file vẫn giữ handle tới lúc GC → Windows không xóa được file tạm.
    try:
        doc = pymupdf.open(stream=pdf_path.read_bytes(), filetype="pdf")
    except Exception as exc:  # PyMuPDF ném nhiều loại lỗi khác nhau cho file hỏng
        raise IngestError("Không đọc được file PDF.") from exc
    if doc.needs_pass:
        doc.close()
        raise IngestError("PDF bị mã hóa, không đọc được.")
    if doc.page_count < 1:
        doc.close()
        raise IngestError("File PDF không có trang nào.")
    return doc


def _get_page(doc: pymupdf.Document, page_number: int) -> pymupdf.Page:
    if not 1 <= page_number <= doc.page_count:
        raise IngestError(f"Trang {page_number} không tồn tại (PDF có {doc.page_count} trang).")
    return doc[page_number - 1]


def _page_shell(page: pymupdf.Page) -> DrawingPage:
    return DrawingPage(
        page_number=page.number + 1, width=page.rect.width, height=page.rect.height, rotation=page.rotation
    )


def _read_page(page: pymupdf.Page) -> DrawingPage:
    result = _page_shell(page)
    result.texts, result.margin_texts = extract_all_texts(page)
    return result


def _rect_polygon(x0: float, y0: float, x1: float, y1: float, precision: Precision = Precision.BBOX) -> Polygon:
    points = [Point(x=x0, y=y0), Point(x=x1, y=y0), Point(x=x1, y=y1), Point(x=x0, y=y1)]
    return Polygon.model_construct(points=points, precision=precision)


def extract_texts(page: pymupdf.Page) -> list[TextSpan]:
    """Chữ nằm trong vùng hiển thị của trang (xem `extract_all_texts`)."""
    return extract_all_texts(page)[0]


def extract_all_texts(page: pymupdf.Page) -> tuple[list[TextSpan], list[TextSpan]]:
    """Chữ của trang theo từng lượt vẽ chữ của PDF → (chữ trong vùng hiển thị, chữ ngoài vùng hiển thị).

    Chữ ngoài vùng hiển thị vẫn nằm trong nội dung trang nhưng bị cắt khỏi khổ in (CropBox) — ở bộ PN2 đó là
    toàn bộ khung tên (tên bản vẽ, số hiệu, tỉ lệ). Giữ riêng để đọc khung tên; không đưa vào bước trích thực thể.

    Hai chỉnh sửa do cách CAD xuất chữ (research-log §9):
    - font VNI-* dùng bảng mã VNI cũ ("LÔÙP VÖÕA") → giải mã sang Unicode;
    - một dòng chữ bị tách thành nhiều lượt vẽ quanh ký tự có dấu / khi CAD đổi font giữa chừng
      ("L" font VNI + "ỚP CHỐNG THẤM" font Arial; "QU" + "Ả" + "N") → nối các lượt sát nhau trên cùng dòng,
      chèn dấu cách khi khoảng hở cỡ một dấu cách.
    """
    matrix = page.rotation_matrix  # tọa độ PDF gốc → trang đang hiển thị
    bounds = page.rect
    groups: tuple[list[_Run], list[_Run]] = ([], [])  # (trong, ngoài) vùng hiển thị
    for span in page.get_texttrace():
        if span.get("type") == 3:  # chữ ẩn (render mode 3) — không nhìn thấy trên bản vẽ
            continue
        parts: dict[bool, list] = {}  # trong vùng hiển thị? → [chữ, khung, ký tự đầu, ký tự cuối]
        for code, _glyph, _origin, char_bbox in span["chars"]:
            rect = pymupdf.Rect(char_bbox) * matrix
            inside = pymupdf.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2) in bounds
            part = parts.setdefault(inside, [[], pymupdf.EMPTY_RECT(), char_bbox, char_bbox])
            part[0].append(chr(code))
            part[1] |= rect
            part[3] = char_bbox
        font = span.get("font") or ""
        for inside, (chars, box, first, last) in parts.items():
            text = "".join(chars).translate(_SPACES)
            if is_vni_font(font):
                text = decode_vni(text)
            run = _Run(text, box, font, span.get("size", 0.0), span["dir"], span.get("layer") or None, first, last)
            runs = groups[0 if inside else 1]
            gap = _gap(runs[-1], run) if runs else None
            if gap is not None:
                runs[-1].append(run, space=gap > SPLIT_SPACE_GAP * run.size)
            else:
                runs.append(run)
    return _to_spans(groups[0], page.rotation), _to_spans(groups[1], page.rotation)


def _to_spans(runs: list["_Run"], page_rotation: int) -> list[TextSpan]:
    spans: list[TextSpan] = []
    for run in runs:
        text = unicodedata.normalize("NFC", run.text).strip()
        if not text:
            continue
        dx, dy = run.direction
        # dir ở hệ trang gốc; /Rotate xoay theo chiều kim đồng hồ → trừ để ra góc ngược chiều kim đồng hồ.
        rotation = (math.degrees(math.atan2(-dy, dx)) - page_rotation) % 360
        spans.append(
            TextSpan.model_construct(
                text=text,
                polygon=_rect_polygon(run.box.x0, run.box.y0, run.box.x1, run.box.y1),
                font=run.font or None,
                size=round(run.size, 3),
                rotation=round(rotation, 2),
                layer=run.layer,
            )
        )
    return spans


class _Run:
    """Một dòng chữ đang gom: một hoặc nhiều lượt vẽ chữ liền nhau."""

    __slots__ = ("text", "box", "font", "size", "direction", "layer", "first", "last", "_font_len")

    def __init__(self, text: str, box: pymupdf.Rect, font: str, size: float, direction: tuple[float, float],
                 layer: str | None, first: tuple, last: tuple) -> None:
        self.text, self.box, self.font, self.size = text, box, font, size
        self.direction, self.layer, self.first, self.last = direction, layer, first, last
        self._font_len = len(text)

    def append(self, other: "_Run", space: bool) -> None:
        self.text += (" " if space else "") + other.text
        self.box |= other.box
        self.last = other.last
        if len(other.text) > self._font_len:  # giữ font của phần dài nhất
            self.font, self._font_len = other.font, len(other.text)


def _gap(prev: _Run, cur: _Run) -> float | None:
    """Khoảng hở (point, dọc theo dòng) nếu `cur` là phần tiếp của `prev`; None nếu là hai dòng chữ khác nhau.

    Phần tiếp: cùng layer / cỡ / hướng, ký tự đầu của `cur` nằm sát sau ký tự cuối của `prev` trên cùng dòng.
    Tính ở hệ tọa độ PDF gốc (bbox ký tự và `dir` cùng hệ) nên đúng với chữ xoay.
    """
    if prev.layer != cur.layer:
        return None
    size = max(prev.size, cur.size)
    if size <= 0 or abs(prev.size - cur.size) > SPLIT_SIZE_TOLERANCE * size:
        return None
    (px, py), (cx, cy) = prev.direction, cur.direction
    if px * cx + py * cy < 0.99:
        return None
    a, b = prev.last, cur.first
    across = abs(((b[0] + b[2]) - (a[0] + a[2])) / 2 * py - ((b[1] + b[3]) - (a[1] + a[3])) / 2 * px)
    if across > SPLIT_MAX_OFFSET * size:
        return None
    end = max(x * px + y * py for x in (a[0], a[2]) for y in (a[1], a[3]))
    start = min(x * px + y * py for x in (b[0], b[2]) for y in (b[1], b[3]))
    gap = start - end
    return gap if -SPLIT_MAX_OVERLAP * size <= gap <= SPLIT_MAX_GAP * size else None


def extract_paths(page: pymupdf.Page) -> list[VectorPath]:
    """Nét vẽ của trang. Một drawing của PDF có thể gồm nhiều nét rời → tách theo tính liền mạch.

    Trang nặng tới ~316k drawing → dùng tuple thuần, tránh đối tượng pymupdf.Point / Pydantic.
    """
    matrix = page.rotation_matrix
    rotate = matrix != pymupdf.Identity
    a, b, c, d, e, f = matrix
    paths: list[VectorPath] = []
    for drawing in page.get_cdrawings():
        kind = drawing.get("type", "s")
        stroke = drawing.get("color")
        color = _hex(stroke if stroke is not None and "s" in kind else drawing.get("fill"))
        dashes = drawing.get("dashes") or ""
        common = {
            "filled": "f" in kind,
            "stroke_width": drawing.get("width"),
            "color": color,
            "dashed": bool(dashes) and not dashes.startswith("[]"),
            "layer": drawing.get("layer") or None,
        }
        for points, closed in _subpaths(drawing["items"], drawing.get("closePath", False)):
            if rotate:
                points = [(a * x + c * y + e, b * x + d * y + f) for x, y in points]
            paths.append(VectorPath(points=points, closed=closed, **common))
    return paths


XY = tuple[float, float]


def _subpaths(items: list, close_path: bool) -> list[tuple[list[XY], bool]]:
    result: list[tuple[list[XY], bool]] = []
    current: list[XY] = []

    def flush() -> None:
        if len(current) >= 2:
            result.append((list(current), close_path or _same(current[0], current[-1])))
        current.clear()

    for item in items:
        op = item[0]
        if op == "re":
            flush()
            x0, y0, x1, y1 = item[1]
            result.append(([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True))
            continue
        if op == "qu":
            flush()
            ul, ur, ll, lr = item[1]  # thứ tự Quad của PyMuPDF
            result.append(([tuple(ul), tuple(ur), tuple(lr), tuple(ll)], True))
            continue
        start = tuple(item[1])
        if current and not _same(current[-1], start):
            flush()
        if not current:
            current.append(start)
        if op == "l":
            current.append(tuple(item[2]))
        elif op == "c":
            current.extend(_bezier(start, item[2], item[3], item[4]))
    flush()
    return result


def _bezier(p0: XY, c1: XY, c2: XY, p3: XY) -> list[XY]:
    out = []
    for i in range(1, BEZIER_SEGMENTS + 1):
        t = i / BEZIER_SEGMENTS
        u = 1 - t
        k0, k1, k2, k3 = u**3, 3 * u * u * t, 3 * u * t * t, t**3
        out.append(
            (
                k0 * p0[0] + k1 * c1[0] + k2 * c2[0] + k3 * p3[0],
                k0 * p0[1] + k1 * c1[1] + k2 * c2[1] + k3 * p3[1],
            )
        )
    return out


def _same(p: XY, q: XY, eps: float = 1e-3) -> bool:
    return abs(p[0] - q[0]) < eps and abs(p[1] - q[1]) < eps


@lru_cache(maxsize=1024)
def _hex(rgb: tuple | None) -> str | None:
    if not rgb or len(rgb) != 3:
        return None
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)
