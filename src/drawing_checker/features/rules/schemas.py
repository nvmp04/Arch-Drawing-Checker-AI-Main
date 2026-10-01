"""Rule nhận từ BE và kế hoạch kiểm tra nội bộ. Schema JSON gốc: docs/criteria-json.md."""

from pydantic import BaseModel, Field

from drawing_checker.common.enums import CheckType, ChtkCategory, ComparisonOperator, HouseType


class RuleInput(BaseModel):
    """Một rule trong dispatch. BE hiện chỉ gửi 5 trường đầu (L-01) — các trường nội dung là tùy chọn."""

    rule_id: str = Field(alias="ruleId")
    code: str | None = None  # null với dòng biến thể (Q-04)
    check_type: CheckType | None = Field(default=None, alias="checkType")  # D-08
    operator: ComparisonOperator | None = None
    value: str | None = None  # chuỗi thô có đơn vị (Q-03)
    # MAIN cần — đề xuất BE gửi thêm (L-01):
    parent_code: str | None = Field(default=None, alias="parentCode")
    headings: list[str] = []
    title: str | None = None
    category: ChtkCategory | None = None
    requirement: str | None = None
    requirement_lines: list[str] = Field(default=[], alias="requirementLines")
    house_types: list[HouseType] = Field(default=[], alias="houseTypes")

    model_config = {"populate_by_name": True}


class NormalizedValue(BaseModel):
    """Giá trị ngưỡng đã chuẩn hóa: độ dài về mm, độ dốc %, số đếm không đơn vị ("")."""

    unit: str
    min: float | None = None
    max: float | None = None
    options: list[float] | None = None  # in-list
    pair: list[float] | None = None  # "2.8 x 5.6m" → [2800, 5600]: từng chiều so theo toán tử
    raw: str = ""  # chuỗi gốc, để hiển thị


class CheckPlan(BaseModel):
    """Kế hoạch kiểm tra một requirementLine — đầu ra của bước diễn giải luật (Q-07)."""

    rule_id: str
    line_index: int
    text: str
    check_type: CheckType | None = None  # chưa hiện thực
    target: str | None = None  # đối tượng: "cửa đi", "bậc thang", "phòng khách"…
    attribute: str | None = None  # thuộc tính: cao, rộng, dày, vật liệu…
    operator: ComparisonOperator | None = None
    value: NormalizedValue | None = None
    page_kinds: list[str] = []  # loại trang cần tìm
    # Mock bước diễn giải (Q-07): bảng khai báo trong rules/plan_table.py chọn checker cho dòng này.
    checker: str | None = None  # None = chưa hỗ trợ → kết quả unknown
    params: dict[str, str | int | float] = {}
    note: str | None = None  # điều kiện áp dụng không kiểm được từ bản vẽ → kết quả pending
