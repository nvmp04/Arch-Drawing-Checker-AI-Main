"""Nhập câu trả lời do một agent Claude Code "đóng vai model" (không tốn credit API) thành bản ghi phát lại.

Agent sạch (không có lịch sử hội thoại) nhận đúng system + bản tóm tắt + prompt từng rule như API, ghi
`<run>/answers/<khóa>.json`. Script này lưu chúng vào kho phát lại riêng (mặc định data/ai-agent/calls) với
`source: claude-code-agent`, để chạy toàn bộ pipeline bằng --replay:

    python scripts/import_agent_answers.py data/ai-agent/run1
    python scripts/run_ai_eval.py "<pdf>" --max-rules 0 --replay --calls-dir data/ai-agent/calls

Khác với gọi API: không có structured outputs ép lược đồ (hậu kiểm vẫn chạy), nhiều rule trong một lượt đọc.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from drawing_checker.features.rules.service import load_mock_rules  # noqa: E402
from drawing_checker.features.semantic.digest import DossierDigest  # noqa: E402
from drawing_checker.features.semantic.provider import CallStore, LlmResponse  # noqa: E402
from drawing_checker.features.semantic.service import build_request  # noqa: E402

MODEL = "claude-opus-5-5"


def main() -> None:
    run = Path(sys.argv[1])
    store_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data/ai-agent/calls"
    # Khóa bản ghi chỉ phụ thuộc chữ của bản tóm tắt → dựng lại từ đúng file agent đã đọc.
    digest = DossierDigest(text=(run / "digest.txt").read_text(encoding="utf-8"))
    store = CallStore(store_dir)
    ok, missing, bad = 0, [], []
    for rule in load_mock_rules(ROOT / "samples/criteria/ruleset-4sao.json"):
        request = build_request(rule, list(range(len(rule.requirement_lines))), digest, None, [])
        key = request.key(MODEL)
        path = run / "answers" / f"{key}.json"
        if not path.exists():
            missing.append(rule.code or rule.parent_code)
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data.get("lines"), list)
        except (json.JSONDecodeError, AssertionError, AttributeError):
            bad.append(rule.code or rule.parent_code)
            continue
        store.save(key, request, LlmResponse(data=data, model=MODEL, call_id=key, stop_reason="end_turn"))
        record = json.loads(store.path(key).read_text(encoding="utf-8"))
        record["source"] = "claude-code-agent"
        store.path(key).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        ok += 1
    print(f"Đã nhập {ok} câu trả lời → {store_dir}. Thiếu: {missing or 'không'}. Lỗi JSON: {bad or 'không'}.")


if __name__ == "__main__":
    main()
