"""Chạy ingest trên một PDF cục bộ (không qua BE) và xuất viewer — tiện khi thử nhanh một file.

Luồng thật (BE gửi việc → MAIN) tự ghi viewer cho từng job; xem tại http://localhost:8000/debug/inspect/.

    .venv/Scripts/python.exe scripts/inspect_ingest.py "D:/Downloads/tieuchuan/PN2.DN-Ban ve mau demo test AI.pdf"
    .venv/Scripts/python.exe scripts/inspect_ingest.py bản_vẽ.pdf --pages 4,12,37-39 --dpi 150 --open

Kết quả ghi vào cùng thư mục với các job (mặc định data/inspect/, không commit).
"""

import argparse
import re
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from drawing_checker.config import get_settings  # noqa: E402
from drawing_checker.features.ingest.inspector import IngestInspector  # noqa: E402
from drawing_checker.features.ingest.service import IngestService  # noqa: E402


def parse_pages(spec: str | None, page_count: int) -> list[int]:
    if not spec:
        return list(range(1, page_count + 1))
    pages: set[int] = set()
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        pages.update(range(int(lo), int(hi or lo) + 1))
    return sorted(p for p in pages if 1 <= p <= page_count)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingest một PDF cục bộ và xuất viewer HTML.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--pages", help="vd. 1-5,12,39 (mặc định: tất cả)")
    parser.add_argument("--dpi", type=int, default=settings.inspect_dpi, help="ảnh nền; 0 = không render")
    parser.add_argument("--out", type=Path, default=ROOT / settings.inspect_dir, help="thư mục gốc chứa các lần chạy")
    parser.add_argument("--open", action="store_true", help="mở trình duyệt khi xong")
    args = parser.parse_args()

    slug = re.sub(r"[^\w.-]+", "-", args.pdf.stem).strip("-")[:40]
    run_id = f"local-{time.strftime('%Y%m%d-%H%M%S')}-{slug}"
    inspector = IngestInspector(args.out, run_id, {"source": "script", "fileName": args.pdf.name})

    with IngestService().reader(args.pdf) as reader:
        pages = parse_pages(args.pages, reader.page_count)
        inspector.start(reader.page_count, args.dpi)
        print(f"{args.pdf.name}: {reader.page_count} trang, xuất {len(pages)} trang → {inspector.dir}")
        print(f"{'trang':>5} {'chữ':>6} {'ký tự':>7} {'nét':>8} {'tô':>6} {'layer':>5} {'t.chữ':>7} {'t.nét':>7}  tiêu đề")
        for n in pages:
            page = reader.read(n)
            s = inspector.write_page(page, reader.render_jpeg(n, args.dpi) if args.dpi > 0 else None)
            print(f"{n:>5} {s['texts']:>6} {s['chars']:>7} {s['paths']:>8} {s['filled']:>6} {s['layers']:>5} "
                  f"{s['textMs']:>5}ms {s['pathsMs']:>5}ms  {s['title'][:50]}")
    index = inspector.finish()
    print(f"Xong trong {inspector.meta['totalSeconds']}s — mở {index}")
    if args.open:
        webbrowser.open(index.resolve().as_uri())


if __name__ == "__main__":
    main()
