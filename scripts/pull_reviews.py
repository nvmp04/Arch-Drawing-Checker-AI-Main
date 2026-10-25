"""Kéo kết quả chấm từ Neon Postgres (bản trên Render, D-24) về data/reviews/<mã hồ sơ>.jsonl.

    python scripts/pull_reviews.py            # đọc MAIN_REVIEWS_DATABASE_URL từ .env / biến môi trường

Ghi lại toàn bộ file từ CSDL (CSDL giữ đủ lịch sử). File cũ khác nội dung được giữ thành <mã>.jsonl.bak.
"""

import json
import sys
from collections import defaultdict

from drawing_checker.config import get_settings
from drawing_checker.features.benchmark.reviews import PgReviewStore


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    settings = get_settings()
    if settings.reviews_database_url is None:
        print("Chưa đặt MAIN_REVIEWS_DATABASE_URL (chuỗi kết nối Neon) trong .env.", file=sys.stderr)
        return 1
    url = settings.reviews_database_url.get_secret_value().strip()
    if "…" in url or "<" in url or "neon.tech" not in url:
        print("MAIN_REVIEWS_DATABASE_URL trong .env chưa phải chuỗi kết nối thật. Vào console.neon.tech → project →\n"
              "Connect → chép nguyên chuỗi postgresql://neondb_owner:...@ep-...neon.tech/neondb?sslmode=require", file=sys.stderr)
        return 1
    import psycopg

    by_dossier: dict[str, list[dict]] = defaultdict(list)
    try:
        for dossier, row in PgReviewStore(url).rows():
            by_dossier[dossier].append(row)
    except psycopg.OperationalError as exc:
        print(f"Không kết nối được Neon: {str(exc).splitlines()[0]}\n"
              "Kiểm tra lại chuỗi kết nối (chép lại từ Neon → Connect) và mạng.", file=sys.stderr)
        return 1
    if not by_dossier:
        print("CSDL chưa có kết quả chấm nào.")
        return 0
    settings.reviews_dir.mkdir(parents=True, exist_ok=True)
    for dossier, rows in by_dossier.items():
        path = settings.reviews_dir / f"{dossier}.jsonl"
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        if path.exists() and path.read_text(encoding="utf-8").strip() and path.read_text(encoding="utf-8") != text:
            path.replace(path.with_suffix(".jsonl.bak"))
        path.write_text(text, encoding="utf-8")
        people = sorted({r.get("reviewer") or "?" for r in rows})
        lines = len({(r["ruleId"], r["lineIndex"]) for r in rows})
        print(f"{path}: {len(rows)} lần chấm · {lines} dòng tiêu chí · người chấm: {', '.join(people)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
