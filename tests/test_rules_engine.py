"""Rule engine không AI: phân tích ngưỡng, so sánh, trích thực thể, checker, quy tắc trạng thái."""

from pathlib import Path

import pytest

from drawing_checker.common.enums import ChtkCategory, ComparisonOperator, FindingStatus, HouseType
from drawing_checker.common.geometry import Point, Polygon, Precision
from drawing_checker.features.extraction.service import ExtractionService
from drawing_checker.features.findings.schemas import LineResult
from drawing_checker.features.findings.service import FindingsService
from drawing_checker.features.ingest.schemas import DrawingPage, TextSpan
from drawing_checker.features.rules.evaluator import compare, describe
from drawing_checker.features.rules.interpreter import RuleInterpreter, ValueParseError
from drawing_checker.features.rules.service import UNSUPPORTED_REASON, RulesService, load_mock_rules

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
RULES = load_mock_rules(SAMPLES / "criteria" / "ruleset-4sao.json")
parse = RuleInterpreter().parse_value


# ------------------------------------------------------------------ lõi


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("150mm", {"unit": "mm", "min": 150, "max": 150}),
        ("3.3m", {"unit": "mm", "min": 3300, "max": 3300}),
        ("2m", {"unit": "mm", "min": 2000}),
        ("18%", {"unit": "%", "max": 18}),
        ("1.2m - 2.6m", {"unit": "mm", "min": 1200, "max": 2600}),
        ("2.8 x 5.6m", {"unit": "mm", "pair": [2800, 5600]}),
        ("17, 18, 21, 22, 25", {"unit": "", "options": [17, 18, 21, 22, 25]}),
    ],
)
def test_parse_value(raw: str, expected: dict) -> None:
    value = parse(raw)
    for key, v in expected.items():
        assert getattr(value, key) == v


def test_parse_value_rejects_text() -> None:
    with pytest.raises(ValueParseError):
        parse("theo danh mục")


def test_every_rule_value_in_sample_ruleset_parses() -> None:
    for rule in RULES:
        if rule.value:
            parse(rule.value)


def test_compare_and_describe() -> None:
    assert compare(ComparisonOperator.GTE, parse("150mm"), 250)
    assert not compare(ComparisonOperator.GTE, parse("4.0m"), 3999)
    assert compare(ComparisonOperator.LTE, parse("180mm"), 180)
    assert compare(ComparisonOperator.BETWEEN, parse("1.2m - 2.6m"), 2000)
    assert not compare(ComparisonOperator.IN_LIST, parse("17, 18, 21, 22, 25"), 20)
    assert describe(ComparisonOperator.GTE, parse("3.4m")) == "≥ 3400 mm"
    assert describe(ComparisonOperator.IN_LIST, parse("17, 18, 21")) == "∈ {17, 18, 21}"


def test_finalize_never_fails_below_threshold_nor_approves() -> None:
    low = LineResult(ruleId="r", lineIndex=0, status=FindingStatus.FAIL, confidence=0.75, reason="x")
    high = LineResult(ruleId="r", lineIndex=0, status=FindingStatus.FAIL, confidence=0.9, reason="x")
    approved = LineResult(ruleId="r", lineIndex=0, status=FindingStatus.APPROVED, confidence=1, reason="x")
    out = FindingsService(0.8).finalize([low, high, approved])
    assert [r.status for r in out] == [FindingStatus.WARNING, FindingStatus.FAIL, FindingStatus.PENDING]


# ------------------------------------------------------------------ trích thực thể + checker trên trang tổng hợp


def span(text: str, x: float, y: float, w: float = 30, h: float = 7, layer: str | None = None) -> TextSpan:
    pts = [Point(x=x, y=y), Point(x=x + w, y=y), Point(x=x + w, y=y + h), Point(x=x, y=y + h)]
    return TextSpan(text=text, polygon=Polygon(points=pts, precision=Precision.BBOX), layer=layer)


def section_page(n: int = 38, ground: str = "+0.250", third: str = "+7.850") -> DrawingPage:
    """Cột cao độ mặt cắt như PN2: nhãn ở trên, số ngay dưới ~11pt."""
    column = [("ĐỈNH MÁI", "+12.250", 67), ("MÁI", "+11.250", 123), ("TẦNG 3", third, 317),
              ("TẦNG 2", "+4.450", 510), ("TẦNG 1", ground, 748), ("VỈA HÈ", "±0.000", 781)]
    texts = []
    for label, value, y in column:
        texts += [span(label, 1380, y), span(value, 1385, y + 11)]
    texts.append(span("TẦNG 2,3", 800, 1055))  # chú thích không kèm số → bỏ qua
    return DrawingPage(page_number=n, width=1445, height=1162, rotation=0, texts=texts)


def stair_page() -> DrawingPage:
    risers = ["18 BẬC x 168=3024", "7 BẬC x 168=1176", "6 BẬC x 162=973", "8 BẬC x 162=1293", "7 BẬC x 162=1133"]
    texts = [span(t, 1325, 300 + 60 * i, layer="A-dim") for i, t in enumerate(risers)]
    texts += [span("17 BẬC x 250=4250", 293, 328, layer="A-dim"), span("5 BẬC x 250=1250", 105, 165, layer="A-dim")]
    return DrawingPage(page_number=42, width=1445, height=1162, rotation=0, texts=texts)


def door_page() -> DrawingPage:
    texts = [span("KÝ HIỆU", 72, 27), span("DR-01", 339, 27), span("DR-03", 667, 27), span("WD-01", 910, 27),
             span("4800w x 3000h", 195, 584, 80), span("1100w x 2800h", 550, 584, 80), span("700w x 1500h", 821, 584, 80),
             span("Cửa Khung nhôm trượt, 2 cánh cố định", 194, 631, 150),
             span("Cửa Khung nhôm mở", 550, 629, 100), span("Cửa sổ Khung nhôm bật", 821, 630, 100),
             span("VỊ TRÍ", 72, 944), span("Cửa đi sảnh chính", 194, 944, 90), span("Cửa đi sau nhà", 550, 944, 90)]
    return DrawingPage(page_number=47, width=1445, height=1162, rotation=0, texts=texts)


def run(pages: list[DrawingPage], house: HouseType = HouseType.SHOPHOUSE):
    entities = [e for p in pages for e in ExtractionService().extract(p)]
    report = RulesService().check(RULES, house, list(ChtkCategory), entities)
    results = FindingsService().finalize(report.results)
    rules = {r.rule_id: r for r in report.rules}
    by_key: dict[str, list[LineResult]] = {}
    for r in results:
        rule = rules[r.rule_id]
        by_key.setdefault(rule.code or f"{rule.parent_code}*", []).append(r)
    return report, by_key


def test_extraction_pairs_level_labels_with_values() -> None:
    levels = [e for e in ExtractionService().extract(section_page()) if e.kind.value == "level"]
    assert {str(e.attributes["key"]): e.value for e in levels} == {
        "roof_top": 12250, "roof": 11250, "storey:3": 7850, "storey:2": 4450, "storey:1": 250, "sidewalk": 0}


def test_level_and_storey_checks() -> None:
    _, r = run([section_page()])
    assert r["1.8*"][0].status == FindingStatus.PASS and r["1.8*"][0].extracted_value == "250 mm"
    assert r["2.1.2*"][0].status == FindingStatus.PASS and r["2.1.2*"][0].extracted_value == "4200 mm"
    assert r["2.1.3"][0].status == FindingStatus.PASS and "sát ngưỡng" in r["2.1.3"][0].reason
    assert r["2.1.1*"][0].status == FindingStatus.UNKNOWN  # không có tầng hầm
    assert r["2.1.4"][0].status == FindingStatus.UNKNOWN  # không có tầng tum
    assert {e.page_number for e in r["1.8*"][0].evidence} == {38}


def test_house_type_selects_variant_threshold() -> None:
    _, r = run([section_page(ground="+0.300")], HouseType.TOWNHOUSE)  # townhouse cần ≥ 450 mm
    assert r["1.8*"][0].status == FindingStatus.FAIL
    assert r["1.8*"][0].standard_value == "≥ 450 mm"


def test_conflicting_levels_are_flagged() -> None:
    _, r = run([section_page(38), section_page(39), section_page(41, third="+7.800")])
    assert "chỗ ghi khác" in r["2.1.3"][0].reason and "trang 41" in r["2.1.3"][0].reason


def test_stair_risers_identified_by_matching_storey_heights() -> None:
    _, r = run([section_page(), stair_page()])
    assert r["3.4"][0].status == FindingStatus.PASS and r["3.4"][0].extracted_value == "168 mm"
    assert "25 bậc" in r["3.5"][0].reason and "21 bậc" in r["3.5"][0].reason
    assert r["3.5"][0].status == FindingStatus.PASS
    assert r["3.2"][0].extracted_value == "250 mm" and r["3.2"][0].status == FindingStatus.PASS
    assert r["3.2*"][0].status == FindingStatus.PENDING  # điều kiện "Báo cáo NCKT" không kiểm được


def test_stair_without_levels_is_unknown_not_guessed() -> None:
    _, r = run([stair_page()])
    assert r["3.4"][0].status == FindingStatus.UNKNOWN


def test_door_catalog() -> None:
    _, r = run([door_page()])
    door_results = {res.extracted_value: res for key in ("1.4.1", "1.4.2", "1.4.3") for res in r.get(key, [])}
    assert door_results["3000 × 4800"].status == FindingStatus.FAIL  # DR-01 lùa, không có trong danh mục
    assert door_results["2800 × 1100"].status == FindingStatus.PASS  # DR-03 mở 2800 × 1100
    assert door_results["1500 × 700"].status == FindingStatus.PASS  # WD-01 cửa sổ bật 1500 × 700
    assert any(e.role.value == "subject" and e.text == "DR-01" for e in door_results["3000 × 4800"].evidence)


def test_unmapped_lines_reported_as_unsupported() -> None:
    report, r = run([section_page()])
    unsupported = [x for rs in r.values() for x in rs if x.reason == UNSUPPORTED_REASON]
    assert len(unsupported) == report.coverage["linesUnsupported"] > 0
    assert all(x.status == FindingStatus.UNKNOWN for x in unsupported)


# ------------------------------------------------------------------ đọc bảng trên bản vẽ (không phụ thuộc bộ tiêu chí)


def ceiling_page(n: int = 44) -> DrawingPage:
    """Bảng "VẬT LIỆU HOÀN THIỆN TRẦN" như PN2 trang 44 (mô tả lệch dọc nhẹ so với mã)."""
    texts = [span("VẬT LIỆU HOÀN THIỆN", 1171, 905, 110, 11), span("TRẦN", 1292, 905, 25, 11),
             span("KÝ HIỆU", 1083, 927, 35), span("MÔ TẢ", 1231, 927, 25),
             span("FC-01", 1103, 945, 25), span("TRẦN CEMBOARD HOÀN THIỆN SƠN NƯỚC MÀU TRẮNG", 1137, 944, 190),
             span("FC-02", 1103, 961, 25), span("TRẦN BÊ TÔNG TRÁT VỮA HOÀN THIỆN SƠN NƯỚC", 1135, 962, 190),
             span("ĐÈN ỐP TRẦN NGOẠI THẤT", 826, 923, 100),  # thiết bị điện → không phải vật liệu trần
             span("HỆ KHUNG TRẦN", 300, 676, 60, 8), span("TẤM CEMBOARD", 300, 692, 60, 8),
             span("CHI TIẾT MẶT BẰNG MÁI ĐÓN", 200, 1105, 150)]
    return DrawingPage(page_number=n, width=1445, height=1162, rotation=0, texts=texts)


def test_finish_table_rows() -> None:
    entities = ExtractionService().extract(ceiling_page())
    rows = {e.label: e for e in entities if e.kind.value == "finish"}
    assert rows["FC-01"].attributes["description"] == "TRẦN CEMBOARD HOÀN THIỆN SƠN NƯỚC MÀU TRẮNG"
    assert rows["FC-02"].attributes["description"] == "TRẦN BÊ TÔNG TRÁT VỮA HOÀN THIỆN SƠN NƯỚC"
    assert rows["FC-01"].attributes["surface"] == "ceiling"


def test_door_table_glass_thickness_is_extracted() -> None:
    page = door_page()
    page.texts.append(span("Kính trong cường lực dày 8mm, mài cạnh", 194, 643, 150))
    doors = {e.label: e for e in ExtractionService().extract(page) if e.kind.value == "opening"}
    assert doors["DR-01"].attributes["glass_mm"] == 8 and "glass_mm" not in doors["DR-03"].attributes


def test_semantic_lines_are_unsupported_not_hardcoded() -> None:
    """D-18: tiêu chí chữ / vật liệu / cấu tạo không được diễn giải bằng bảng viết tay → luôn "chưa hỗ trợ"."""
    _, r = run([ceiling_page(), assembly_page(), door_page()])
    for key in ("5.1.1", "5.1.2", "4.2.1*", "4.2.4", "4.2.5*", "4.5.3", "4.5.5*", "4.4.1", "1.4"):
        assert r[key] and all(x.reason == UNSUPPORTED_REASON for x in r[key]), key


def assembly_page(roof_waterproof: str = "LỚP CHỐNG THẤM GỐC PU CUỐN LÊN CHÂN", rebar: str = "D6@200") -> DrawingPage:
    """ "BẢNG THỐNG KÊ CẤU TẠO SÀN" như PN2 trang 5: mã, vị trí, các lớp (có lớp ghi trên hai dòng)."""
    texts = [span("KÍ HIỆU", 114, 52, 40, 12), span("VỊ TRÍ", 187, 52, 40, 12), span("CHI TIẾT", 332, 53, 50, 12),
             span("MÔ TẢ CÁC LỚP CẤU TẠO", 485, 52, 150, 12), span("TẦNG 1", 54, 130, 40, 12), span("MÁI", 54, 330, 30, 12)]
    rows = [
        ("F1.2", "SÀN NỘI THẤT", 170, ["SÀN BTCT( xem BVKC)", "LỚP BÊ TÔNG LÓT( xem BVKC)",
                                        "ĐẤT TỰ NHIÊN ĐẦM CHẶT XỬ LÍ", "CHỐNG MỐI ĐỒNG THỜI"]),
        ("F2.2", "BAN CÔNG", 250, ["GẠCH PORCELAIN CHỐNG TRƯỢT HOÀN THIỆN", "LỚP VỮA CÁN NỀN M75 ĐÁNH DỐC VỀ RÃNH THU",
                                   "LỚP CHỐNG THẤM CUỐN LÊN CHÂN TƯỜNG 300mm", "SÀN BTCT( xem BVKC)"]),
        ("F3.1", "SÀN MÁI", 330, ["LỚP VỮA TẠO PHẲNG DÀY 10MM", f"LỚP BÊ TÔNG ĐÁ MI M200, LƯỚI THÉP {rebar},",
                                  "DÀY MIN 50mm, TẠO DỐC 1.5% VỀ PHỄU THU", roof_waterproof, "TƯỜNG 300mm",
                                  "SÀN BTCT( xem BVKC)"]),
    ]
    for code, location, y, layers in rows:
        texts += [span(code, 126, y + 10, 20, 8), span(location, 172, y + 8, 70, 12)]
        texts += [span("·", 478, y + 10.5 * i, 3, 8) for i in range(len(layers))]
        texts += [span(layer, 486, y + 10.5 * i, 200, 8) for i, layer in enumerate(layers)]
    for t in texts:
        t.size = 8.0 if t.polygon.points[2].y - t.polygon.points[0].y < 10 else 14.0
    return DrawingPage(page_number=5, width=1445, height=1162, rotation=0, texts=texts)


def test_floor_assembly_table_rows_and_multiline_layers() -> None:
    layers = [e for e in ExtractionService().extract(assembly_page()) if e.attributes.get("table") == "floor-assembly"]
    roof = [e.text for e in layers if e.label == "F3.1"]
    assert roof == ["LỚP VỮA TẠO PHẲNG DÀY 10MM",
                    "LỚP BÊ TÔNG ĐÁ MI M200, LƯỚI THÉP D6@200, DÀY MIN 50mm, TẠO DỐC 1.5% VỀ PHỄU THU",
                    "LỚP CHỐNG THẤM GỐC PU CUỐN LÊN CHÂN TƯỜNG 300mm", "SÀN BTCT( xem BVKC)"]
    ground = next(e for e in layers if e.label == "F1.2")
    assert ground.attributes["location"] == "SÀN NỘI THẤT" and ground.attributes["group"] == "TẦNG 1"
    assert [e.text for e in layers if e.label == "F2.2"][0] == "GẠCH PORCELAIN CHỐNG TRƯỢT HOÀN THIỆN"
