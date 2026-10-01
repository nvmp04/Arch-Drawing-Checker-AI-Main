"""Hồi quy trên bộ bản vẽ mẫu PN2 thật (bỏ qua nếu máy không có file — PDF không commit).

Kết quả kỳ vọng đối chiếu tay với bản vẽ + comment người kiểm tra (research-log §4, §7).
"""

from pathlib import Path

import pytest

from drawing_checker.common.enums import ChtkCategory, FindingStatus, HouseType
from drawing_checker.features.extraction.service import ExtractionService
from drawing_checker.features.findings.service import FindingsService
from drawing_checker.features.ingest.service import IngestService
from drawing_checker.features.rules.service import RulesService, load_mock_rules

PDF = Path("D:/Downloads/tieuchuan/PN2.DN-Ban ve mau demo test AI.pdf")
RULESET = Path(__file__).resolve().parent.parent / "samples" / "criteria" / "ruleset-4sao.json"

pytestmark = pytest.mark.skipif(not PDF.exists(), reason="Không có PDF mẫu PN2 trên máy này")


@pytest.fixture(scope="module")
def results() -> dict[str, list]:
    doc = IngestService().open(PDF)
    entities = [e for page in doc.pages for e in ExtractionService().extract(page)]
    report = RulesService().check(load_mock_rules(RULESET), HouseType.SHOPHOUSE, list(ChtkCategory), entities)
    rules = {r.rule_id: r for r in report.rules}
    out: dict[str, list] = {}
    for r in FindingsService().finalize(report.results):
        rule = rules[r.rule_id]
        out.setdefault(rule.code or f"{rule.parent_code}*", []).append(r)
    return out


@pytest.mark.parametrize(
    ("key", "status", "extracted"),
    [
        ("1.8*", FindingStatus.PASS, "250 mm"),  # +0.250 − ±0.000
        ("2.1.2*", FindingStatus.PASS, "4200 mm"),  # +4.450 − 0.250
        ("2.1.3", FindingStatus.PASS, "3400 mm"),
        ("3.2", FindingStatus.PASS, "250 mm"),
        ("3.2*", FindingStatus.PENDING, "250 mm"),
        ("3.4", FindingStatus.PASS, "168 mm"),
        ("3.5", FindingStatus.PASS, "25 bậc"),
        ("2.1.1*", FindingStatus.UNKNOWN, None),
        ("2.1.4", FindingStatus.UNKNOWN, None),
    ],
)
def test_expected_line_results(results, key, status, extracted) -> None:
    r = results[key][0]
    assert (r.status, r.extracted_value) == (status, extracted)


def test_level_inconsistency_on_page_41_is_flagged(results) -> None:
    assert "trang 41" in results["2.1.3"][0].reason


def test_doors_not_in_catalog_match_reviewer_comments(results) -> None:
    """Người kiểm tra comment trang 31, 47: kích thước cửa không theo CHTK."""
    doors = [r for key in ("1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5") for r in results.get(key, [])]
    assert len(doors) == 7  # DR-01..06 + WD-01; mục không mã (cửa thăm mái) bỏ qua
    assert all(r.status == FindingStatus.FAIL for r in doors)
    assert {e.page_number for r in doors for e in r.evidence} == {47, 48}


def test_exterior_ceiling_cemboard_matches_reviewer_comments(results) -> None:
    """Người kiểm tra comment trần ngoài nhà ở trang 4, 6, 44 (cemboard thay vì thạch cao chống ẩm 9mm)."""
    cemboard = next(r for r in results["5.1.1"] if r.extracted_value and "cemboard" in r.extracted_value)
    assert cemboard.status == FindingStatus.FAIL
    assert {4, 6, 44} <= {e.page_number for e in cemboard.evidence}
