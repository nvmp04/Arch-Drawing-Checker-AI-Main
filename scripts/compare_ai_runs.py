"""So hai lần chạy AI (file run-<k>.json do run_ai_eval.py ghi): độ nhất quán kết luận + độ dài đầu ra.

    python scripts/compare_ai_runs.py data/ai/eval/<lần A>/run-1.json data/ai/eval/<lần B>/run-1.json [answersA answersB]

Hai lần khác prompt thì đây KHÔNG phải đo độ ổn định thuần (online-rollout.md) — chỉ cho biết đổi prompt làm đổi
bao nhiêu kết luận. Tùy chọn: hai thư mục answers/ của agent để so độ dài đầu ra (đại diện cho token ra).
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def outcomes(run: dict) -> dict[tuple[str, int], str]:
    out = {}
    for r in run["results"]:
        na = r["status"] == "pending" and "] Không áp dụng:" in r["reason"]
        out[(r["ruleId"], r["lineIndex"])] = "n/a" if na else r["status"]
    return out


def main() -> None:
    a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    b = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    oa, ob = outcomes(a), outcomes(b)
    keys = sorted(set(oa) & set(ob))
    same = sum(oa[k] == ob[k] for k in keys)
    severe = [k for k in keys if {oa[k], ob[k]} == {"pass", "fail"}]
    changes = Counter(f"{oa[k]}→{ob[k]}" for k in keys if oa[k] != ob[k])
    codes = {(x["ruleId"], x["lineIndex"]): x["code"] for x in a["lines"] + b["lines"]}
    print(f"{len(keys)} dòng chung · cùng kết luận {same} ({same / len(keys):.0%}) · lật Đạt↔Không đạt: {len(severe)}")
    print("A:", dict(Counter(oa.values())), "\nB:", dict(Counter(ob.values())))
    for change, n in changes.most_common():
        print(f"  {change}: {n}")
    for k in severe:
        print("  lật nghiêm trọng:", codes.get(k), "dòng", k[1])
    if len(sys.argv) > 4:
        for label, d in (("A", sys.argv[3]), ("B", sys.argv[4])):
            files = list(Path(d).glob("*.json"))
            chars = sum(len(f.read_text(encoding="utf-8")) for f in files)
            print(f"Đầu ra {label}: {len(files)} file, {chars:,} ký tự JSON")


if __name__ == "__main__":
    main()
