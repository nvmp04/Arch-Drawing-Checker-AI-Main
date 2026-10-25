"""AI đọc tiêu chí (D-22) — chỉ dùng model giả / client giả, KHÔNG gọi API thật (AGENTS.md §6)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from drawing_checker.common.enums import FindingStatus, HouseType
from drawing_checker.common.geometry import Point, Polygon, Precision
from drawing_checker.config import Settings
from drawing_checker.features.ingest.schemas import TextSpan
from drawing_checker.features.rules.schemas import RuleInput
from drawing_checker.features.semantic.budget import BudgetExceeded, Usage, UsageLedger, cost_usd
from drawing_checker.features.semantic.digest import build_digest
from drawing_checker.features.semantic.factory import build_semantic
from drawing_checker.features.semantic.provider import CallStore, ClaudeProvider, FakeProvider, ReplayProvider
from drawing_checker.features.semantic.service import SemanticService, build_request
from drawing_checker.features.sheets.schemas import DocumentIndex, DossierProfile, SheetInfo, TitleBlock


def span(text: str, x: float, y: float, layer: str | None = None, size: float = 2.5) -> TextSpan:
    pts = [Point(x=x, y=y), Point(x=x + 40, y=y), Point(x=x + 40, y=y + size), Point(x=x, y=y + size)]
    return TextSpan(text=text, polygon=Polygon(points=pts, precision=Precision.BBOX), size=size, layer=layer)


def make_digest(include_numeric: bool = False):
    pages = [
        (5, [span("BẢNG THỐNG KÊ CẤU TẠO SÀN", 10, 10, "A-TEXT"), span("SÀN MÁI", 10, 20),
             span("LỚP CHỐNG THẤM GỐC PU", 60, 20, "xr|A-Ano Text"), span("4650", 10, 30, "A-dim")]),
        (7, [span("TRẦN THẠCH CAO", 10, 10)]),
    ]
    index = DocumentIndex(
        sheets=[SheetInfo(page_number=5, title_block=TitleBlock(name="CHI TIẾT CẤU TẠO", scale="1/NTS")),
                SheetInfo(page_number=7)],
        profile=DossierProfile(page_count=2, items=["MẪU NHÀ SH1"]),
    )
    return build_digest(pages, index, include_numeric=include_numeric)


def make_rule(lines: list[str], code: str = "5.4.1") -> RuleInput:
    return RuleInput(ruleId="r1", code=code, title="Chống thấm sàn mái", requirementLines=lines)


def answer(index: int, **kw) -> dict:
    item = {"line_index": index, "applicability": "applies", "applicability_reason": "", "template": "M3",
            "scope": "sàn mái", "requirement": "có lớp chống thấm gốc PU", "found": "", "status": "pass",
            "confidence": 0.9, "evidence_ids": [], "pages_to_review": [], "reason": "Thấy lớp chống thấm."}
    item.update(kw)
    return item


# ------------------------------------------------------------------ bản tóm tắt


def test_digest_has_block_ids_layers_and_skips_numbers():
    d = make_digest()
    assert "p5-2 L2 LỚP CHỐNG THẤM GỐC PU" in d.text
    assert "L2=A-Ano Text" in d.text  # bỏ tiền tố xref
    assert "4650" not in d.text and d.stats["blocksSkippedNumeric"] == 1
    assert "p5-3" in d.blocks  # khối số vẫn có mã (trích dẫn được nếu bật include_numeric)
    assert "tên: CHI TIẾT CẤU TẠO" in d.text and "(không đọc được khung tên)" in d.text
    assert "4650" in make_digest(include_numeric=True).text


def test_digest_is_deterministic():
    assert make_digest().text == make_digest().text


# ------------------------------------------------------------------ hậu kiểm


def run(rule, reply, digest=None):
    provider = FakeProvider(lambda req: reply)
    out = SemanticService(provider).judge_rules([rule], digest or make_digest(), HouseType.TOWNHOUSE, [])
    return out, provider


def test_valid_evidence_becomes_polygon():
    out, _ = run(make_rule(["Lớp chống thấm gốc PU"]), {"lines": [answer(0, evidence_ids=["p5-2"])]})
    r = out.results[0]
    assert r.status == FindingStatus.PASS
    assert r.evidence[0].page_number == 5 and r.evidence[0].text == "LỚP CHỐNG THẤM GỐC PU"
    assert r.reason.startswith("[AI · M3]")


def test_invented_citation_is_dropped_and_verdict_downgraded():
    out, _ = run(make_rule(["x"]), {"lines": [answer(0, status="fail", evidence_ids=["p9-99"])]})
    r = out.results[0]
    assert r.status == FindingStatus.PENDING and not r.evidence
    assert "không tồn tại" in r.reason and r.confidence == pytest.approx(0.7)


def test_external_reference_and_subjective_always_need_review():
    out, _ = run(make_rule(["a", "b"]), {"lines": [answer(0, template="M6", evidence_ids=["p5-2"]),
                                                   answer(1, template="M7", status="fail", evidence_ids=["p5-2"])]})
    assert [r.status for r in out.results] == [FindingStatus.PENDING, FindingStatus.PENDING]


def test_forbidden_absent_passes_with_capped_confidence():
    out, _ = run(make_rule(["Không xử lý chống mối"]), {"lines": [answer(0, template="M4", confidence=0.95)]})
    assert out.results[0].status == FindingStatus.PASS and out.results[0].confidence == 0.6


def test_not_applicable_and_missing_lines():
    out, _ = run(make_rule(["a", "b"]), {"lines": [answer(0, status="not_applicable",
                                                          applicability_reason="hồ sơ không có hầm")]})
    assert out.results[0].status == FindingStatus.PENDING and "Không áp dụng: hồ sơ không có hầm" in out.results[0].reason
    assert out.results[1].status == FindingStatus.UNKNOWN


def test_never_approved_and_confidence_clamped():
    out, _ = run(make_rule(["a"]), {"lines": [answer(0, status="approved", confidence=7, evidence_ids=["p5-2"])]})
    assert out.results[0].status == FindingStatus.PENDING and out.results[0].confidence == 1.0


def test_criterion_text_is_sent_verbatim_so_editing_it_changes_the_request():
    """D-18: ý nghĩa câu tiêu chí không nằm trong code — sửa câu thì yêu cầu gửi AI đổi theo."""
    d = make_digest()
    a = build_request(make_rule(["Sàn bê tông cốt thép"]), [0], d, None, [])
    b = build_request(make_rule(["Không thi công sàn btct"]), [0], d, None, [])
    assert "Sàn bê tông cốt thép" in a.prompt and "Không thi công sàn btct" in b.prompt
    assert a.key("m") != b.key("m") and a.system == b.system


def test_only_requested_lines_are_sent():
    provider = FakeProvider(lambda req: {"lines": [answer(1, evidence_ids=["p5-2"])]})
    out = SemanticService(provider).judge_rules([make_rule(["a", "b", "c"])], make_digest(), None, [], {"r1": {1}})
    assert [r.line_index for r in out.results] == [1]
    assert "1: b" in provider.requests[0].prompt and "0: a" not in provider.requests[0].prompt


def test_run_cap_stops_calls():
    class Pricey(FakeProvider):
        def estimate_usd(self, request):
            return 1.5

    provider = Pricey(lambda req: {"lines": [answer(0, evidence_ids=["p5-2"])]})
    rules = [make_rule(["a"]), RuleInput(ruleId="r2", code="5.4.2", requirementLines=["b"])]
    out = SemanticService(provider, max_usd_per_run=1.0).judge_rules(rules, make_digest(), None, [])
    assert not provider.requests  # ước tính 1.5 USD > trần 1.0 → không gọi
    assert out.stopped and [r.status for r in out.results] == [FindingStatus.UNKNOWN] * 2


# ------------------------------------------------------------------ chi phí + client giả


def test_cost_and_monthly_budget(tmp_path: Path):
    assert cost_usd("claude-opus-5-5", Usage(input_tokens=1_000_000)) == pytest.approx(4.0)
    assert cost_usd("claude-opus-5-5", Usage(cache_read_tokens=1_000_000, output_tokens=1_000_000)) == pytest.approx(20.2)
    assert cost_usd("unknown-model", Usage(input_tokens=1_000_000)) == pytest.approx(10.0)  # giá cao nhất
    ledger = UsageLedger(tmp_path / "usage.jsonl", monthly_budget_usd=5.0)
    ledger.record("claude-opus-5-5", Usage(), 4.5, "judge-rule", "k")
    assert ledger.month_spent() == pytest.approx(4.5)
    ledger.ensure_can_spend(0.4)
    with pytest.raises(BudgetExceeded):
        ledger.ensure_can_spend(0.6)


class FakeClient:
    """Đóng vai anthropic.Anthropic: ghi lại tham số, trả message giả."""

    def __init__(self, data: dict) -> None:
        self.calls: list[dict] = []
        message = SimpleNamespace(
            model="claude-opus-5-5", stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text=json.dumps(data, ensure_ascii=False))],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=60000,
                                  cache_read_input_tokens=0),
        )
        create = lambda **kw: (self.calls.append(kw), message)[1]  # noqa: E731
        self.messages = SimpleNamespace(create=create)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=create))


def test_claude_provider_request_shape_ledger_and_replay(tmp_path: Path):
    reply = {"lines": [answer(0, evidence_ids=["p5-2"])]}
    client = FakeClient(reply)
    ledger = UsageLedger(tmp_path / "usage.jsonl", 5.0)
    store = CallStore(tmp_path / "calls")
    provider = ClaudeProvider("claude-opus-5-5", "medium", ledger, store, client=client)
    out = SemanticService(provider).judge_rules([make_rule(["a"])], make_digest(), None, [])

    kw = client.calls[0]
    assert kw["model"] == "claude-opus-5-5" and kw["fallbacks"] == "default"
    assert kw["system"][1]["cache_control"] == {"type": "ephemeral"}  # bản tóm tắt được cache
    assert kw["output_config"]["format"]["type"] == "json_schema" and kw["output_config"]["effort"] == "medium"
    assert out.results[0].status == FindingStatus.PASS
    assert ledger.month_spent() == pytest.approx(cost_usd("claude-opus-5-5", Usage(1000, 500, 60000, 0)))

    replay = ReplayProvider(store, "claude-opus-5-5")
    again = SemanticService(replay).judge_rules([make_rule(["a"])], make_digest(), None, [])
    assert again.results[0].status == FindingStatus.PASS and again.calls[0]["replayed"] and again.spent_usd == 0
    missing = SemanticService(replay).judge_rules([make_rule(["khác"])], make_digest(), None, [])
    assert missing.results[0].status == FindingStatus.UNKNOWN and "Chưa có bản ghi" in missing.results[0].reason


def test_budget_exceeded_blocks_call(tmp_path: Path):
    client = FakeClient({"lines": []})
    ledger = UsageLedger(tmp_path / "usage.jsonl", 0.01)
    provider = ClaudeProvider("claude-opus-5-5", "medium", ledger, CallStore(tmp_path / "calls"), client=client)
    out = SemanticService(provider, max_usd_per_run=100).judge_rules([make_rule(["a"])], make_digest(), None, [])
    assert not client.calls and "Vượt hạn mức" in out.stopped


def test_ai_is_off_by_default():
    assert Settings(_env_file=None).ai_provider == "off"
    assert build_semantic(Settings(_env_file=None)) is None


# ------------------------------------------------------------------ pipeline


def test_pipeline_ai_fills_only_unsupported_lines(tmp_path: Path):
    """Rule engine giữ dòng nó kiểm được; AI chỉ thay các dòng "chưa hỗ trợ"; kết quả ghi viewer kèm chi phí."""
    from drawing_checker.features.analyses.schemas import DispatchRequest
    from drawing_checker.features.analyses.service import AnalysesService
    from drawing_checker.features.ingest.inspector import IngestInspector

    provider = FakeProvider(lambda req: {"lines": [answer(0, evidence_ids=["p5-2"])]})
    service = AnalysesService(backend=None, fetcher=None, runner=None, semantic=SemanticService(provider))
    request = DispatchRequest.model_validate({
        "reviewId": "rv", "pdfUrl": "http://x", "houseType": "townhouse", "categories": [], "callbackUrl": "http://cb",
        "rules": [{"ruleId": "r1", "code": "9.9.9", "requirementLines": ["Lớp chống thấm gốc PU"]}],
    })
    digest_pages = [(5, [span("LỚP CHỐNG THẤM GỐC PU", 60, 20)])]
    index = DocumentIndex(sheets=[SheetInfo(page_number=5)], profile=DossierProfile(page_count=1))
    inspector = IngestInspector(tmp_path, "job-1", {})
    service._run_checks("job-1", request, [], inspector, index, digest_pages)

    checks = (tmp_path / "job-1" / "checks.js").read_text(encoding="utf-8")
    assert "[AI · M3]" in checks and '"calls"' in checks
    assert len(provider.requests) == 1 and "0: Lớp chống thấm gốc PU" in provider.requests[0].prompt


# ------------------------------------------------------------------ duyệt kết quả + chấm điểm


def test_review_api_appends_latest_wins_and_scores(tmp_path: Path, monkeypatch):
    from fastapi.testclient import TestClient

    from drawing_checker.config import get_settings
    from drawing_checker.features.benchmark.reviews import ReviewStore, score
    from drawing_checker.features.benchmark.router import router
    from fastapi import FastAPI

    monkeypatch.setenv("MAIN_REVIEWS_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    dossier = "0123456789abcdef"
    body = {"ruleId": "r1", "lineIndex": 0, "verdict": "wrong", "predicted": "pass", "expected": "fail"}
    assert client.post(f"/debug/reviews/{dossier}", json=body).status_code == 201
    assert client.post(f"/debug/reviews/{dossier}", json={**body, "verdict": "correct", "expected": "pass"}).status_code == 201
    assert client.post("/debug/reviews/../etc", json=body).status_code in (400, 404)
    assert client.post(f"/debug/reviews/{dossier}", json={**body, "expected": "approved"}).status_code == 422
    latest = client.get(f"/debug/reviews/{dossier}").json()
    assert len(latest) == 1 and latest[0]["expected"] == "pass"  # lần bấm sau thắng
    assert len((tmp_path / f"{dossier}.jsonl").read_text(encoding="utf-8").splitlines()) == 2  # chỉ thêm
    get_settings.cache_clear()

    reviews = ReviewStore(tmp_path).latest(dossier)
    s = score({("r1", 0): "fail"}, reviews)
    assert s["reviewed"] == 1 and s["correct"] == 0 and s["severeErrors"] == 1


def test_outcome_marks_not_applicable():
    from drawing_checker.features.semantic.service import outcome_of

    out, _ = run(make_rule(["a", "b"]), {"lines": [answer(0, status="not_applicable"),
                                                   answer(1, status="fail", evidence_ids=["p5-2"])]})
    assert [outcome_of(r) for r in out.results] == ["n/a", "fail"]
