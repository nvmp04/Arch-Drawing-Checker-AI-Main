"""Ghi kết quả ingest thành viewer HTML tĩnh để người đánh giá bằng mắt (công cụ debug).

Mỗi lần chạy (một job từ BE, hoặc một lần chạy script) là một thư mục:
    <root>/<run_id>/index.html   viewer (mở trực tiếp hoặc qua MAIN: /debug/inspect/<run_id>/)
    <root>/<run_id>/pNNN.js      dữ liệu trang (chữ, nét vẽ theo layer, thống kê)
    <root>/<run_id>/pNNN.jpg     ảnh nền — CHỈ để đối chiếu, MAIN không trả ảnh cho BE (D-07)
    <root>/<run_id>/meta.json    thông tin lần chạy (job, hồ sơ, trạng thái, thống kê từng trang)
    <root>/index.html            danh sách các lần chạy, mới nhất trước
"""

import html
import json
import time
from collections import Counter
from pathlib import Path

from drawing_checker.features.ingest.schemas import DrawingPage

VIEWER_TEMPLATE = Path(__file__).with_name("inspector_viewer.html")
TITLE_KEYS = ("MẶT BẰNG", "MẶT ĐỨNG", "MẶT CẮT", "CHI TIẾT", "BẢNG", "THỐNG KÊ", "TL:", "TL 1/")


class IngestInspector:
    def __init__(self, root: Path, run_id: str, info: dict | None = None) -> None:
        self.root = root
        self.run_id = run_id
        self.dir = root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._started = time.perf_counter()
        self.meta: dict = {
            "runId": run_id,
            "createdAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "running",
            "pageCount": None,
            "dpi": 0,
            "pages": [],
            **(info or {}),
        }
        self._save_meta()

    def start(self, page_count: int, dpi: int) -> None:
        self.meta.update(pageCount=page_count, dpi=dpi)
        self._save_meta()

    def write_page(self, page: DrawingPage, jpeg: bytes | None = None) -> dict:
        """Ghi dữ liệu một trang; trả thống kê của trang."""
        data, stats = _page_payload(page)
        n = page.page_number
        (self.dir / f"p{n:03d}.js").write_text(
            f"window.__ingestPage({json.dumps(data, ensure_ascii=False, separators=(',', ':'))});", encoding="utf-8"
        )
        if jpeg:
            (self.dir / f"p{n:03d}.jpg").write_bytes(jpeg)
        self.meta["pages"].append(stats)
        return stats

    def write_checks(self, payload: dict) -> None:
        """Kết quả rule engine cho tab "Kiểm tra" (payload do `analyses` dựng — ingest không phụ thuộc rules)."""
        (self.dir / "checks.js").write_text(
            f"window.__ingestChecks({json.dumps(payload, ensure_ascii=False, separators=(',', ':'))});",
            encoding="utf-8",
        )
        self.meta["checks"] = {"source": payload.get("source"), **payload.get("coverage", {})}
        self._save_meta()

    def finish(self, status: str = "completed", error: str | None = None) -> Path:
        """Chốt lần chạy: ghi viewer (kể cả khi lỗi giữa chừng — xem được các trang đã xong)."""
        self.meta.update(status=status, totalSeconds=round(time.perf_counter() - self._started, 1))
        if error:
            self.meta["error"] = error
        self.meta["pages"].sort(key=lambda p: p["n"])
        self._save_meta()
        if self.meta["pages"]:
            viewer = VIEWER_TEMPLATE.read_text(encoding="utf-8").replace(
                "/*__META__*/null", json.dumps(self.meta, ensure_ascii=False)
            )
            (self.dir / "index.html").write_text(viewer, encoding="utf-8")
        write_runs_index(self.root)
        return self.dir / "index.html"

    def _save_meta(self) -> None:
        (self.dir / "meta.json").write_text(json.dumps(self.meta, ensure_ascii=False, indent=1), encoding="utf-8")
        write_runs_index(self.root)


def _page_payload(page: DrawingPage) -> tuple[dict, dict]:
    layers: dict[str | None, int] = {}
    fonts: dict[str | None, int] = {}

    def idx(table: dict, key) -> int:
        return table.setdefault(key, len(table))

    text_rows = []
    for span in page.texts:
        p = span.polygon.points
        text_rows.append(
            [_r(p[0].x), _r(p[0].y), _r(p[2].x), _r(p[2].y), span.text,
             idx(fonts, span.font), span.size, span.rotation, idx(layers, span.layer)]
        )
    # Nét vẽ gom theo layer: s = nét hở, c = nét kín, f = vùng tô. Mỗi nét là mảng phẳng x,y,x,y…
    by_layer: dict[int, dict[str, list]] = {}
    for path in page.paths:
        group = by_layer.setdefault(idx(layers, path.layer), {"s": [], "c": [], "f": []})
        key = "f" if path.filled else "c" if path.closed else "s"
        group[key].append([_r(c) for xy in path.points for c in xy])

    stats = {
        "n": page.page_number,
        "title": _guess_title(page),
        "texts": len(page.texts),
        "chars": sum(len(s.text.replace(" ", "")) for s in page.texts),
        "paths": len(page.paths),
        "points": sum(len(p.points) for p in page.paths),
        "closed": sum(p.closed for p in page.paths),
        "filled": sum(p.filled for p in page.paths),
        "dashed": sum(p.dashed for p in page.paths),
        "layers": len({p.layer for p in page.paths} | {s.layer for s in page.texts}),
        "textMs": page.timings.get("textMs", 0),
        "pathsMs": page.timings.get("pathsMs", 0),
        "rotations": dict(Counter(str(round(s.rotation)) for s in page.texts).most_common(6)),
    }
    data = {
        "n": page.page_number,
        "w": _r(page.width),
        "h": _r(page.height),
        "rotation": page.rotation,
        "stats": stats,
        "layers": [name or "(không có layer)" for name in layers],
        "fonts": [name or "?" for name in fonts],
        "texts": text_rows,
        "paths": {str(k): v for k, v in by_layer.items()},
    }
    return data, stats


def _guess_title(page: DrawingPage) -> str:
    """Tiêu đề tạm cho danh sách trang — chỉ để dễ tìm, KHÔNG phải phân loại trang (việc của `sheets`)."""
    candidates = [s for s in page.texts if any(k in s.text.upper() for k in TITLE_KEYS) and len(s.text) < 90]
    return max(candidates, key=lambda s: (s.size or 0, len(s.text))).text if candidates else ""


def _r(v: float) -> float:
    return round(v, 2)


def _checks_cell(checks: dict | None) -> str:
    if not checks:
        return "—"
    by = checks.get("byStatus", {})
    parts = [f"<span class='ok'>{by.get('pass', 0)} đạt</span>", f"<span class='bad'>{by.get('fail', 0)} lệch</span>"]
    if by.get("warning"):
        parts.append(f"<span class='warn'>{by['warning']} cảnh báo</span>")
    if by.get("pending"):
        parts.append(f"{by['pending']} chờ người")
    if by.get("unknown"):
        parts.append(f"{by['unknown']} không thấy dữ liệu")
    return (" · ".join(parts) + f"<br><small>{checks.get('linesSupported', 0)}/{checks.get('linesApplicable', 0)}"
            f" dòng có checker · {html.escape(str(checks.get('source') or ''))}</small>")


def write_runs_index(root: Path) -> None:
    """Trang danh sách các lần chạy (đọc meta.json của từng thư mục)."""
    runs = []
    for meta_file in root.glob("*/meta.json"):
        try:
            runs.append(json.loads(meta_file.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    runs.sort(key=lambda m: m.get("createdAt", ""), reverse=True)
    rows = []
    for m in runs:
        pages = m.get("pages", [])
        link = f'<a href="{html.escape(m["runId"])}/index.html">mở viewer</a>' if pages else "—"
        rows.append(
            "<tr>"
            f"<td>{html.escape(m.get('createdAt', ''))}</td>"
            f"<td>{html.escape(m.get('source', ''))}</td>"
            f"<td><code>{html.escape(m['runId'])}</code><br><small>{html.escape(m.get('reviewId', '') or '')}</small></td>"
            f"<td>{html.escape(m.get('houseType', '') or '')}</td>"
            f"<td class='st {html.escape(m.get('status', ''))}'>{html.escape(m.get('status', ''))}"
            f"{'<br><small>' + html.escape(m['error']) + '</small>' if m.get('error') else ''}</td>"
            f"<td>{len(pages)} / {m.get('pageCount') or '?'}</td>"
            f"<td>{sum(p['texts'] for p in pages):,}</td><td>{sum(p['paths'] for p in pages):,}</td>"
            f"<td>{m.get('totalSeconds', '…')}</td><td>{_checks_cell(m.get('checks'))}</td><td>{link}</td>"
            "</tr>"
        )
    body = "".join(rows) or "<tr><td colspan='11'>Chưa có lần chạy nào.</td></tr>"
    (root / "index.html").write_text(
        f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Ingest Runs</title>
<style>
body{{margin:0;padding:16px;background:#f4f4f2;color:#1d1d1b;font:13px/1.4 system-ui,"Segoe UI",sans-serif}}
h1{{font-size:16px;margin:0 0 4px}} p{{color:#6b6b66;margin:0 0 12px}}
table{{border-collapse:collapse;background:#fff;width:100%}} th,td{{padding:6px 10px;border-bottom:1px solid #deded9;text-align:left;vertical-align:top}}
th{{font-size:12px;color:#6b6b66;text-transform:uppercase}} td{{font-variant-numeric:tabular-nums}}
.st.completed,.ok{{color:#1a7f37}} .bad{{color:#c62828}} .warn{{color:#b26a00}}
.st.completed{{color:#1a7f37}} .st.failed{{color:#c62828}} .st.running{{color:#2f6fdb}} small{{color:#6b6b66}}
</style></head><body>
<h1>Kết quả ingest theo lần chạy</h1>
<p>Mỗi job BE gửi sang (hoặc mỗi lần chạy script) là một dòng. Tải lại trang để cập nhật.</p>
<table><thead><tr><th>Thời điểm</th><th>Nguồn</th><th>Job / hồ sơ</th><th>Loại nhà</th><th>Trạng thái</th>
<th>Trang</th><th>Chữ</th><th>Nét</th><th>Giây</th><th>Kiểm tra</th><th></th></tr></thead><tbody>{body}</tbody></table>
</body></html>""",
        encoding="utf-8",
    )
