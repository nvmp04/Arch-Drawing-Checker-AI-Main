import json
from pathlib import Path

from fastapi.testclient import TestClient

from drawing_checker.app import app
from drawing_checker.features.rules.schemas import RuleInput

client = TestClient(app)
SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_business_routes_are_stubs() -> None:
    assert client.get("/v1/capabilities").status_code == 501


def test_sample_ruleset_fits_rule_input() -> None:
    """Rule từ JSON mẫu của BE phải đọc được bằng hợp đồng MAIN (id → ruleId)."""
    data = json.loads((SAMPLES / "criteria" / "ruleset-4sao.json").read_text(encoding="utf-8"))
    rules = [r for s in data["data"][0]["sections"] for r in s["rules"]]
    parsed = [RuleInput.model_validate({**r, "ruleId": r["id"]}) for r in rules]
    assert len(parsed) == 92
