"""Thử AI (Claude) đọc tiêu chí trên một bộ bản vẽ — chạy tay, ngoài luồng BE. Mặc định KHÔNG gọi API (chạy khô).

1) Chạy khô — ước tính chi phí, ghi bản tóm tắt chữ gửi AI để xem trước (miễn phí):
    python scripts/run_ai_eval.py "D:/Downloads/tieuchuan/PN2.DN-Ban ve mau demo test AI.pdf" --codes 5

2) Gọi Claude thật (TỐN TIỀN — cần MAIN_ANTHROPIC_API_KEY trong .env; hỏi xác nhận, hoặc --yes):
    python scripts/run_ai_eval.py <pdf> --codes 5 --live
    python scripts/run_ai_eval.py <pdf> --codes 5.1 --live --repeat 10      # đo độ ổn định (K lần độc lập)

3) Phát lại lần gọi thật đã ghi (miễn phí). --calls-dir: kho khác, vd. câu trả lời của agent Claude Code
   (scripts/import_agent_answers.py):
    python scripts/run_ai_eval.py <pdf> --max-rules 0 --replay --calls-dir data/ai-agent/calls

Mỗi lần chạy có kết quả → một mục trong viewer debug (http://localhost:8000/debug/inspect/, cần MAIN đang chạy để
lưu kết quả duyệt): tab "Kiểm tra" có nút Đúng / Sai / Sai vị trí cho từng dòng. Kết quả duyệt lưu
data/reviews/<mã hồ sơ>.jsonl và được dùng để CHẤM TỰ ĐỘNG mọi lần chạy sau (độ chính xác in ở cuối).
Hạn mức tháng (MAIN_AI_MONTHLY_BUDGET_USD) và trần mỗi lần chạy (MAIN_AI_MAX_USD_PER_RUN) luôn được áp.
"""

import argparse
import hashlib
import json
import pickle
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")  # log tiếng Việt của MAIN

from drawing_checker.common.enums import ChtkCategory, HouseType  # noqa: E402
from drawing_checker.config import get_settings  # noqa: E402
from drawing_checker.features.analyses.service import _dossier_payload, checks_payload  # noqa: E402
from drawing_checker.features.benchmark.reviews import ReviewStore, score  # noqa: E402
from drawing_checker.features.extraction.service import ExtractionService  # noqa: E402
from drawing_checker.features.findings.service import FindingsService  # noqa: E402
from drawing_checker.features.ingest.inspector import IngestInspector  # noqa: E402
from drawing_checker.features.ingest.service import IngestService  # noqa: E402
from drawing_checker.features.rules.service import CheckReport, load_mock_rules  # noqa: E402
from drawing_checker.features.semantic.budget import PRICES, UsageLedger, estimate_tokens  # noqa: E402
from drawing_checker.features.geometry.service import GeometryService  # noqa: E402
from drawing_checker.features.semantic.digest import build_digest  # noqa: E402
from drawing_checker.features.semantic.provider import CallStore, ClaudeProvider, ReplayProvider  # noqa: E402
from drawing_checker.features.semantic.service import SemanticService, build_request, outcome_of  # noqa: E402
from drawing_checker.features.sheets.service import SheetService  # noqa: E402

ASSUMED_OUTPUT_TOKENS = 2500  # mỗi lần gọi, gồm token suy nghĩ — giả định, số thật xem sổ chi tiêu
COMPARE_MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]
DIGEST_CACHE_VERSION = 3


def main() -> None:
    args = parse_args()
    settings = get_settings()
    rules = select_rules(load_mock_rules(args.rules), args)
    if not rules:
        sys.exit("Không có rule nào khớp bộ lọc.")
    n_lines = sum(len(r.requirement_lines) for r in rules)
    print(f"Rule chọn: {len(rules)} rule / {n_lines} dòng: {', '.join(label(r) for r in rules[:15])}"
          + (" …" if len(rules) > 15 else ""))

    table_grid = not args.no_table_grid
    if args.replay and table_grid:
        print("Lưu ý: bản tóm tắt CÓ lưới bảng. Lượt agent 1–2 (2026-10-09, 10-19) dùng bản chỉ chữ → phát lại các lượt "
              "đó cần thêm --no-table-grid, nếu không mọi lần gọi đều không khớp kho.")
    dossier, digest, index = load_digest(args.pdf, settings.ai_include_numeric, table_grid)
    out = settings.ai_dir / "eval" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "digest.txt").write_text(digest.text, encoding="utf-8")
    house_type = HouseType(args.house_type) if args.house_type else None
    print(f"Hồ sơ {dossier} · bản tóm tắt {len(digest.text):,} ký tự ≈ {estimate_tokens(digest.text):,} token "
          f"(ước lượng), {digest.stats} → {out / 'digest.txt'}")
    print_estimates(rules, digest, house_type, settings.ai_model)

    if not (args.live or args.replay):
        print("\nChạy khô: KHÔNG gọi API. Thêm --live để gọi Claude thật (tốn tiền), --replay để phát lại.")
        return

    model = args.model or settings.ai_model
    store = CallStore(args.calls_dir or settings.ai_dir / "calls")
    ledger = UsageLedger(settings.ai_dir / "usage.jsonl", settings.ai_monthly_budget_usd)
    if args.live:
        print(f"\nModel: {model} · effort {settings.ai_effort} · đã dùng tháng này {ledger.month_spent():.3f} / "
              f"{ledger.budget:.2f} USD · trần mỗi lần chạy {settings.ai_max_usd_per_run:.2f} USD · "
              f"{args.repeat} lần chạy")
        if not args.yes:
            try:
                confirmed = input("Gõ YES để gọi Claude API thật (tốn tiền): ").strip() == "YES"
            except EOFError:  # chạy không có bàn phím (vd. tiền tố "!" trong Claude Code)
                sys.exit("Không hỏi xác nhận được (không có bàn phím) — chưa gọi API. "
                         "Tự chạy lại với --yes nếu bạn chắc chắn muốn gọi.")
            if not confirmed:
                sys.exit("Đã hủy, không gọi API.")
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        provider = ClaudeProvider(model, settings.ai_effort, ledger, store, api_key=key)
    else:
        provider = ReplayProvider(store, model)
    semantic = SemanticService(provider, settings.ai_max_usd_per_run)
    findings = FindingsService(settings.confidence_threshold)
    categories = [ChtkCategory(c) for c in args.categories.split(",")] if args.categories else []
    reviews = ReviewStore(settings.reviews_dir).latest(dossier)

    runs = []
    for k in range(1, args.repeat + 1):
        started = time.time()
        ai = semantic.judge_rules(rules, digest, house_type, categories)
        final = findings.finalize(ai.results)
        run = {
            "run": k, "model": model, "source": "live" if args.live else f"replay:{store._dir}",
            "seconds": round(time.time() - started, 1), "usd": round(ai.spent_usd, 4), "stopped": ai.stopped,
            "calls": ai.calls, "lines": ai.lines, "results": [r.model_dump(by_alias=True, mode="json") for r in final],
        }
        predicted = {(r.rule_id, r.line_index): outcome_of(r) for r in final}
        run["outcomes"] = dict(Counter(predicted.values()))
        if reviews:
            run["score"] = score(predicted, reviews)
        (out / f"run-{k}.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
        runs.append((run, ai, final, predicted))
        errors = sum(1 for c in ai.calls if c["error"])
        print(f"Lần {k}: {len(ai.calls)} lần gọi ({errors} lỗi), {ai.spent_usd:.4f} USD, {run['seconds']} s, "
              f"kết luận {run['outcomes']}" + (f" — {ai.stopped}" if ai.stopped else ""))
        if errors:
            print("  Lỗi đầu tiên:", next(c["error"] for c in ai.calls if c["error"]))
        if ai.stopped:
            break

    summary = {"dossier": dossier, "model": model, "runs": len(runs), "usd": round(sum(r[0]["usd"] for r in runs), 4),
               "monthSpentUsd": round(ledger.month_spent(), 4)}
    if len(runs) > 1:
        summary["stability"] = stability([r[3] for r in runs])
        print_stability(summary["stability"])
    if reviews:
        summary["score"] = runs[0][0]["score"]
        print_score(summary["score"])
    else:
        print("\nChưa có kết quả duyệt cho hồ sơ này → chưa chấm được. Duyệt trên viewer rồi chạy lại với --replay.")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    if not args.no_viewer:
        run, ai, final, _ = runs[0]
        viewer = write_viewer(args.pdf, settings, dossier, index, rules, ai, final, model, run["source"],
                              house_type, categories)
        print(f"\nViewer: http://localhost:8000/debug/inspect/{viewer}/#tab=checks  (MAIN phải đang chạy để lưu duyệt)")
    print(f"Tổng: {summary['usd']:.4f} USD lần này · tháng này {summary['monthSpentUsd']:.3f} USD · kết quả: {out}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pdf", type=Path)
    p.add_argument("--rules", type=Path, default=ROOT / "samples/criteria/ruleset-4sao.json")
    p.add_argument("--codes", help="lọc theo tiền tố mã rule, vd. 5.1,5.2,1.4.3")
    p.add_argument("--max-rules", type=int, default=10, help="số rule tối đa (mặc định 10 để rẻ; 0 = không giới hạn)")
    p.add_argument("--house-type", choices=[h.value for h in HouseType], help="loại nhà (lọc rule + gửi AI)")
    p.add_argument("--categories", help="nhóm tiêu chí, vd. finishing,structure")
    p.add_argument("--model", help="ghi đè MAIN_AI_MODEL")
    p.add_argument("--live", action="store_true", help="gọi Claude API thật (TỐN TIỀN)")
    p.add_argument("--replay", action="store_true", help="phát lại các lần gọi thật đã ghi (miễn phí)")
    p.add_argument("--calls-dir", type=Path, help="kho bản ghi để phát lại (mặc định data/ai/calls)")
    p.add_argument("--yes", action="store_true", help="không hỏi xác nhận trước khi gọi API")
    p.add_argument("--repeat", type=int, default=1, help="số lần chạy độc lập (đo độ ổn định)")
    p.add_argument("--no-viewer", action="store_true", help="không xuất viewer (tiết kiệm ~1–2 phút)")
    p.add_argument("--no-table-grid", action="store_true",
                   help="bản tóm tắt chỉ dựa vào vị trí chữ, không dùng lưới bảng (mốc so sánh; phát lại lượt agent 1–2)")
    args = p.parse_args()
    if args.live and args.replay:
        p.error("chọn --live hoặc --replay, không cả hai")
    return args


def select_rules(rules, args):
    if args.codes:
        prefixes = [c.strip() for c in args.codes.split(",") if c.strip()]
        rules = [r for r in rules if any((r.code or r.parent_code or "").startswith(px) for px in prefixes)]
    if args.house_type:
        rules = [r for r in rules if not r.house_types or HouseType(args.house_type) in r.house_types]
    if args.max_rules:
        rules = rules[: args.max_rules]
    return rules


def label(rule) -> str:
    return rule.code or f"{rule.parent_code}*"


def dossier_of(pdf: Path) -> str:
    return hashlib.sha256(pdf.read_bytes()).hexdigest()[:16]


def load_digest(pdf: Path, include_numeric: bool, table_grid: bool = True):
    """Ingest + mục lục hồ sơ → (mã hồ sơ, bản tóm tắt, mục lục). Lưu đệm theo mã băm PDF (ingest PN2 ~60 s).

    table_grid: in chữ trong bảng theo hàng / ô (lưới kẻ từ nét vẽ, `geometry`); False = mốc chỉ dựa vào vị trí chữ.
    """
    dossier = dossier_of(pdf)
    cache = get_settings().ai_dir / "digest-cache" / \
        f"{dossier}-{int(include_numeric)}-g{int(table_grid)}-v{DIGEST_CACHE_VERSION}.pkl"
    if cache.exists():
        digest, index = pickle.loads(cache.read_bytes())
        return dossier, digest, index
    print("Đang đọc bản vẽ (lần đầu ~1 phút)…")
    sheets_service, extraction = SheetService(), ExtractionService()
    pages, sheets, abbreviations, entities, tables = [], [], [], [], {}
    geometry = GeometryService()
    with IngestService().reader(pdf) as reader:
        for n in range(1, reader.page_count + 1):
            page = reader.read(n)
            pages.append((n, page.texts))
            sheets.append(sheets_service.analyze(page))
            abbreviations.extend(sheets_service.abbreviations(page))
            entities.extend(extraction.extract(page))
            if table_grid:
                tables[n] = geometry.tables(page)
    index = sheets_service.build_index(sheets, abbreviations, entities)
    digest = build_digest(pages, index, include_numeric, tables if table_grid else None)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps((digest, index)))
    return dossier, digest, index


def write_viewer(pdf, settings, dossier, index, rules, ai, final, model, source, house_type, categories) -> str:
    """Một mục viewer debug: ảnh + chữ + nét từng trang, tab Hồ sơ, tab Kiểm tra (kết quả AI + nút duyệt)."""
    run_id = f"eval-{datetime.now():%Y%m%d-%H%M%S}-{model}"
    inspector = IngestInspector(settings.inspect_dir, run_id, {"source": f"run_ai_eval ({source})",
                                                              "file": pdf.name, "dossier": dossier})
    print("Đang xuất viewer (ảnh + nét vẽ 48 trang, ~1–2 phút)…")
    with IngestService().reader(pdf) as reader:
        inspector.start(reader.page_count, settings.inspect_dpi)
        for n in range(1, reader.page_count + 1):
            jpeg = reader.render_jpeg(n, settings.inspect_dpi) if settings.inspect_dpi > 0 else None
            inspector.write_page(reader.read(n), jpeg)
    inspector.write_dossier(_dossier_payload(index))
    lines = sum(len(r.requirement_lines) for r in rules)
    report = CheckReport(rules=rules, results=final, coverage={
        "rulesTotal": len(rules), "rulesApplicable": len(rules), "linesApplicable": lines, "linesSupported": lines,
        "linesUnsupported": 0, "byStatus": dict(Counter(r.status.value for r in final)),
    })
    report.coverage["ai"] = {"lines": lines, "calls": len(ai.calls), "usd": round(ai.spent_usd, 4),
                             "errors": sum(1 for c in ai.calls if c["error"]), "stopped": ai.stopped}
    inspector.write_checks(checks_payload(report, final, f"AI {model} · {source}",
                                          house_type.value if house_type else None, [c.value for c in categories],
                                          [], ai, dossier))
    inspector.finish("completed")
    return run_id


def print_estimates(rules, digest, house_type, current_model: str) -> None:
    """Chi phí ước tính: lần gọi đầu ghi cache bản tóm tắt, các lần sau đọc cache."""
    requests = [build_request(r, list(range(len(r.requirement_lines))), digest, house_type, []) for r in rules]
    context = estimate_tokens(digest.text)
    fresh = sum(estimate_tokens(q.system) + estimate_tokens(q.prompt) for q in requests)
    print(f"\nƯớc tính ({len(requests)} lần gọi; giả định {ASSUMED_OUTPUT_TOKENS} token ra / lần; chưa đo thật):")
    for model in dict.fromkeys([current_model, *COMPARE_MODELS]):
        p = PRICES.get(model)
        if p is None:
            continue
        inp, out, read = p.input, p.output, p.cache_read
        if p.long_prompt_threshold and context > p.long_prompt_threshold:
            inp, out, read = p.long_input, p.long_output, read * (p.long_input / p.input)
        usd = (fresh * inp + context * inp * 1.25 + context * read * (len(requests) - 1)
               + ASSUMED_OUTPUT_TOKENS * out * len(requests)) / 1_000_000
        mark = " ← MAIN_AI_MODEL" if model == current_model else ""
        print(f"  {model:20s} ≈ {usd:.3f} USD / lần chạy{mark}")


def stability(runs: list[dict]) -> dict:
    keys = set.intersection(*(set(r) for r in runs))
    k = len(runs)
    absolute = agreement = flips = 0.0
    for key in keys:
        values = [r[key] for r in runs]
        absolute += len(set(values)) == 1
        agreement += Counter(values).most_common(1)[0][1] / k
        flips += {"pass", "fail"} <= set(values)
    n = len(keys) or 1
    return {"runs": k, "lines": len(keys), "absolute": round(absolute / n, 3), "agreement": round(agreement / n, 3),
            "severeFlips": int(flips)}


def print_score(s: dict) -> None:
    if not s["reviewed"]:
        print("\nCác dòng đã duyệt không trùng dòng nào của lần chạy này.")
        return
    print(f"\nĐộ chính xác trên {s['reviewed']} dòng đã duyệt: {s['correct']}/{s['reviewed']} = {s['accuracy']:.0%} · "
          f"lỗi nghiêm trọng (Đạt↔Không đạt): {s['severeErrors']} · đúng kết luận nhưng sai vị trí: {s['locationWrong']}")
    for k, n in s["confusion"].items():
        print(f"  đáp án→hệ thống {k}: {n}")


def print_stability(s: dict) -> None:
    print(f"\nĐộ ổn định ({s['runs']} lần, {s['lines']} dòng): tuyệt đối {s['absolute']:.0%} · "
          f"đồng thuận TB {s['agreement']:.0%} · lật Đạt↔Không đạt: {s['severeFlips']}")


if __name__ == "__main__":
    main()
