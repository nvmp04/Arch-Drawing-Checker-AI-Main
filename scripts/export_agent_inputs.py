"""Xuất đúng đầu vào API (system, bản tóm tắt, lược đồ, prompt từng rule) để một agent Claude Code sạch đóng vai model.

    python scripts/export_agent_inputs.py "<pdf>" data/ai-agent/run2

Agent đọc 4 file trong thư mục, ghi answers/<khóa>.json; sau đó: scripts/import_agent_answers.py <thư mục>.
Khóa = mã băm (model + system + bản tóm tắt + prompt + lược đồ) → đổi prompt là ra khóa mới, không đè lượt cũ.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

from run_ai_eval import load_digest  # noqa: E402

from drawing_checker.config import get_settings  # noqa: E402
from drawing_checker.features.rules.service import load_mock_rules  # noqa: E402
from drawing_checker.features.semantic.service import PROMPT_VERSION, RESULT_SCHEMA, SYSTEM_PROMPT, build_request  # noqa: E402

MODEL = "claude-opus-5-5"


def main() -> None:
    pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
    (out / "answers").mkdir(parents=True, exist_ok=True)
    # --no-table-grid: bản tóm tắt chỉ chữ (giống lượt agent 1–2) — để so sánh với bản có lưới bảng.
    dossier, digest, _ = load_digest(pdf, get_settings().ai_include_numeric, "--no-table-grid" not in sys.argv)
    rules = load_mock_rules(ROOT / "samples/criteria/ruleset-4sao.json")
    (out / "system.txt").write_text(SYSTEM_PROMPT, encoding="utf-8")
    (out / "digest.txt").write_text(digest.text, encoding="utf-8")
    (out / "schema.json").write_text(json.dumps(RESULT_SCHEMA, ensure_ascii=False, indent=1), encoding="utf-8")
    with (out / "requests.jsonl").open("w", encoding="utf-8") as f:
        for n, rule in enumerate(rules, 1):
            request = build_request(rule, list(range(len(rule.requirement_lines))), digest, None, [])
            f.write(json.dumps({"n": n, "key": request.key(MODEL), "prompt": request.prompt}, ensure_ascii=False) + "\n")
    (out / "meta.json").write_text(json.dumps({"dossier": dossier, "pdf": pdf.name, "promptVersion": PROMPT_VERSION,
                                               "model": MODEL, "rules": len(rules)}, indent=1), encoding="utf-8")
    print(f"Hồ sơ {dossier} · {len(rules)} rule · prompt {PROMPT_VERSION} → {out}")


if __name__ == "__main__":
    main()
