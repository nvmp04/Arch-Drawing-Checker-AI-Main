"""findings v1: quy đổi tọa độ point → % (Q-01), bbox chính, hạ fail, cờ không áp dụng."""

from drawing_checker.common.enums import FindingStatus
from drawing_checker.common.geometry import Polygon
from drawing_checker.features.findings.schemas import Evidence, EvidenceRole, LineResult
from drawing_checker.features.findings.service import FindingsService, to_percent
from drawing_checker.features.rules.schemas import RuleInput

RULE = RuleInput(ruleId="r1", code="3.1", title="Cầu thang", requirementLines=["Bậc cao ≤ 170", "Rộng ≥ 1.1m"])


def _ev(page: int, x: float, y: float, w: float, h: float) -> Evidence:
    return Evidence(pageNumber=page, polygon=Polygon.from_bbox(x, y, w, h), role=EvidenceRole.MEASUREMENT, text="170")


def test_to_percent_uses_displayed_page_size_and_clips() -> None:
    box = to_percent(Polygon.from_bbox(100, 50, 200, 100), (1000, 500))
    assert (box.x, box.y, box.width, box.height) == (10, 10, 20, 20)
    clipped = to_percent(Polygon.from_bbox(900, 450, 200, 100), (1000, 500))
    assert clipped.x + clipped.width == 100 and clipped.y + clipped.height == 100
    assert to_percent(Polygon.from_bbox(0, 0, 1, 1), None) is None


def test_to_backend_main_box_unions_evidence_on_first_page() -> None:
    results = [
        LineResult(ruleId="r1", lineIndex=0, status=FindingStatus.FAIL, confidence=0.6, reason="Bậc 180",
                   evidence=[_ev(2, 100, 100, 100, 100), _ev(2, 300, 300, 100, 100), _ev(3, 0, 0, 10, 10)]),
        LineResult(ruleId="r1", lineIndex=1, status=FindingStatus.UNKNOWN, confidence=0, reason="chưa hỗ trợ"),
    ]
    out = FindingsService().to_backend("job-1", results, [RULE], {2: (1000, 1000), 3: (500, 500)})
    a, b = out
    assert a.main_result_id == "job-1:r1:0:0" and a.rule.requirement_line == "Bậc cao ≤ 170" and a.rule.code == "3.1"
    assert a.status == FindingStatus.WARNING  # fail dưới 0.8 bị hạ
    assert a.page_number == 2 and (a.bounding_box.x, a.bounding_box.width) == (10, 30)
    assert [e.page_number for e in a.evidence] == [2, 2, 3]
    assert b.page_number is None and b.bounding_box is None and b.applicability.value == "unknown"
    body = b.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert "pageNumber" not in body and "severity" not in body and body["evidence"] == []


def test_not_applicable_flag() -> None:
    r = LineResult(ruleId="r1", lineIndex=0, status=FindingStatus.PENDING, confidence=0.9, reason="[AI x] Không áp dụng: …")
    out = FindingsService().to_backend("j", [r], [RULE], {}, is_not_applicable=lambda _: True)
    assert out[0].applicability.value == "not-applicable"
    assert out[0].status == FindingStatus.UNKNOWN  # hiện là "Không xác định", không có mục riêng


def test_several_results_per_line_get_distinct_ids() -> None:
    rs = [LineResult(ruleId="r1", lineIndex=0, status=FindingStatus.PASS, confidence=0.9, reason=str(i)) for i in range(2)]
    ids = [f.main_result_id for f in FindingsService().to_backend("j", rs, [RULE], {})]
    assert ids == ["j:r1:0:0", "j:r1:0:1"]
