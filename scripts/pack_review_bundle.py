"""Đóng gói MAIN + một (vài) lượt viewer để đưa lên máy Oracle cho đối tác chấm (docs/deploy-review.md).

    python scripts/pack_review_bundle.py eval-20261019-005535-claude-opus-5-5
    → dist/review-bundle.tar.gz

KHÔNG đóng gói data/reviews: kết quả chấm sống trên máy chủ, giải nén bản cập nhật không được đè lên.
"""

import argparse
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ["pyproject.toml", "README.md", "src", "samples/criteria/ruleset-4sao.json", "deploy"]


def _skip(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    name = info.name.replace("\\", "/")
    if "__pycache__" in name or name.endswith(".pyc") or ".egg-info" in name:
        return None
    return info


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="tên thư mục trong data/inspect (lượt viewer cần chấm)")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "review-bundle.tar.gz")
    args = ap.parse_args()

    for run in args.runs:
        if not (ROOT / "data" / "inspect" / run / "checks.js").exists():
            print(f"Không thấy lượt viewer có kết quả kiểm tra: data/inspect/{run}", file=sys.stderr)
            return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.out, "w:gz") as tar:
        for item in CODE:
            tar.add(ROOT / item, arcname=item, filter=_skip)
        for run in args.runs:
            tar.add(ROOT / "data" / "inspect" / run, arcname=f"data/inspect/{run}", filter=_skip)
    print(f"Đã tạo {args.out} ({args.out.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
