"""Bảng khai báo rule → checker. MOCK cho bước diễn giải luật (Q-07) — đợt thử rule engine không AI.

Khóa rule (`rule_key`): mã rule (vd. "3.4"); dòng biến thể `code = null` dùng "<parentCode>*"
(vd. "1.8*") — biến thể theo loại nhà đã được lọc trước bằng `houseTypes`, nên cùng khóa là đủ.
Không dùng `rule.id`: BE sinh UUID mới mỗi lần nạp Excel.

Mỗi rule: {chỉ số dòng | "*": {checker, target, attribute, params?, note?}}.
- `note`: điều kiện áp dụng không kiểm được từ bản vẽ → kết quả tối đa `pending`.
- Dòng / rule không có trong bảng → `unknown` "chưa hỗ trợ" (đo độ phủ).

Phạm vi đợt đầu (người dùng chốt 2026-09-30): các họ đã chứng minh ở research-log §4.
Đợt 2 (2026-10-01): 5.1 trần ngoài nhà — tiêu chí vật liệu, tìm theo phạm vi rule (D-17).
"""

from drawing_checker.features.rules.schemas import RuleInput


def _ceiling(**params: str) -> dict:
    """Dòng tiêu chí trần ngoài nhà (5.1.x) — một checker nhóm xét mọi vật liệu trần tìm được (D-17)."""
    return {"checker": "exterior_ceiling", "target": "trần ngoài nhà", "attribute": "vật liệu", "params": params}


def _catalog(opening: str, mechanism: str) -> dict:
    """Dòng danh mục kích thước cửa; (opening, mechanism) để checker ghép đúng loại cửa trong bảng thống kê."""
    return {"checker": "opening_catalog", "target": "cửa trong bảng thống kê", "attribute": "cao × rộng",
            "params": {"opening": opening, "mechanism": mechanism}}


PLAN_TABLE: dict[str, dict[int | str, dict]] = {
    # 1.8 Chênh cote giữa tầng 1 (trệt) với cote vỉa hè
    "1.8*": {0: {"checker": "ground_floor_above_sidewalk", "target": "tầng 1 so với vỉa hè", "attribute": "chênh cao độ"}},
    # 2.1 Chiều cao tầng (cao độ sàn tầng trên − cao độ sàn tầng này)
    "2.1.1*": {0: {"checker": "storey_height", "params": {"storey": "basement"}, "target": "tầng hầm", "attribute": "chiều cao tầng"}},
    "2.1.2*": {0: {"checker": "storey_height", "params": {"storey": "1"}, "target": "tầng 1", "attribute": "chiều cao tầng"}},
    "2.1.3": {0: {"checker": "storey_height", "params": {"storey": "2-3"}, "target": "tầng 2, 3", "attribute": "chiều cao tầng"}},
    "2.1.4": {0: {"checker": "storey_height", "params": {"storey": "attic"}, "target": "tầng tum", "attribute": "chiều cao tầng"}},
    # 3.x Thang bộ
    "3.2": {0: {"checker": "stair_tread", "target": "bậc thang", "attribute": "chiều rộng bậc"}},
    "3.2*": {0: {"checker": "stair_tread", "target": "bậc thang", "attribute": "chiều rộng bậc",
                 "note": "Chỉ áp dụng khi được nêu trong Báo cáo NCKT — không kiểm được từ bản vẽ."}},
    "3.4": {0: {"checker": "stair_riser", "target": "bậc thang", "attribute": "chiều cao bậc"}},
    "3.5": {0: {"checker": "stair_count", "target": "thang từng tầng", "attribute": "số bậc"}},
    # 1.4.x Danh mục kích thước cửa: mọi dòng là một mục của danh mục
    "1.4.1": {"*": _catalog("door", "swing")},
    "1.4.2": {"*": _catalog("door", "sliding")},
    "1.4.3": {"*": _catalog("window", "swing")},
    "1.4.4": {"*": _catalog("window", "sliding")},
    "1.4.5": {"*": _catalog("window", "fixed")},
    # 5.1 Trần ngoài nhà (D-17, đợt 2): vật liệu trần. Dòng khung / bước khung / ty treo (5.1.1 dòng 2–4) chưa hỗ trợ.
    "5.1.1": {0: _ceiling(region="sea"), 1: _ceiling(region="plain")},
    "5.1.2": {0: _ceiling(finish="plaster"), 1: _ceiling(finish="paint")},
}


def rule_key(rule: RuleInput) -> str:
    return rule.code if rule.code else f"{rule.parent_code}*"
