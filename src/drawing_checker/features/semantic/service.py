"""AI đọc tiêu chí và tìm bằng chứng trên bản vẽ (D-22). Mỗi rule một lần gọi; kết quả theo requirementLine.

Luồng mỗi rule: câu tiêu chí (nguyên văn) + bản tóm tắt chữ của hồ sơ (cache) → model trả JSON theo lược đồ cố định:
cổng áp dụng, mẫu M1–M7, phạm vi, yêu cầu, giá trị thấy được, trạng thái, mã khối chữ làm bằng chứng → code HẬU KIỂM:
- mã khối không tồn tại bị loại; kết luận Đạt / Không đạt / Cảnh báo mà không còn bằng chứng hợp lệ → Cần kiểm tra;
- M6 (tham chiếu ngoài bản vẽ), M7 (chủ quan) → luôn Cần kiểm tra (check-templates.md);
- không bao giờ `approved`; Không đạt dưới ngưỡng tin cậy do `findings.finalize` hạ xuống.

Ngữ nghĩa câu tiêu chí KHÔNG nằm trong code: prompt chỉ mô tả cách làm việc + mẫu kiểm tra, câu tiêu chí gửi
nguyên văn mỗi lần (D-18 — sửa câu tiêu chí thì kết quả đổi theo).
"""

import logging
from dataclasses import dataclass, field

from drawing_checker.common.enums import ChtkCategory, FindingStatus, HouseType
from drawing_checker.features.findings.schemas import Evidence, EvidenceRole, LineResult
from drawing_checker.features.rules.schemas import RuleInput
from drawing_checker.features.semantic.budget import BudgetExceeded
from drawing_checker.features.semantic.digest import DossierDigest
from drawing_checker.features.semantic.provider import LlmProvider, LlmRequest

logger = logging.getLogger(__name__)

PROMPT_VERSION = "judge-rule/v2"  # v2 (2026-10-19): đầu ra rút gọn để giảm token ra
MAX_EVIDENCE = 5
INVALID_CITATION_PENALTY = 0.2
ABSENCE_CONFIDENCE_CAP = 0.6  # M4 "không được có" mà không thấy: Đạt nhưng tin cậy thấp (check-templates M4)

SYSTEM_PROMPT = """Bạn là kỹ sư thẩm tra hồ sơ thiết kế kiến trúc nhà ở thấp tầng tại Việt Nam. Nhiệm vụ: đối chiếu \
TỪNG DÒNG yêu cầu của một tiêu chí với hồ sơ bản vẽ và kết luận có đạt hay không, kèm bằng chứng.

NGUỒN DỮ LIỆU
- Ngữ cảnh (sau phần hướng dẫn này) là CHỮ trích trực tiếp từ PDF vector của bộ bản vẽ, theo từng trang, kèm khung tên, \
tiêu đề hình/bảng, bảng viết tắt của chính hồ sơ và mã layer CAD. Bạn không nhìn thấy hình vẽ.
- Mỗi dòng chữ có MÃ KHỐI dạng "p5-12" (trang 5). Bằng chứng phải là các mã khối có thật trong ngữ cảnh, chép đúng từng ký tự.
- Khối chữ trong bảng xếp theo hàng; dòng trống ngăn cách các vùng khác nhau của trang. Một ô nhiều dòng có thể bị tách \
thành nhiều khối liên tiếp.
- Các khối chỉ gồm con số (giá trị kích thước) đã bị lược bỏ. Nếu yêu cầu cần một số đo mà chữ không ghi rõ, đừng suy đoán.
- Tên layer chỉ là gợi ý, có thể sai; không kết luận chỉ dựa vào tên layer.
- Chữ viết tắt hiểu theo bảng viết tắt của hồ sơ (vd. BTCT = bê tông cốt thép). Mã như "F1.2", "DR-01" là mã ký hiệu, không phải viết tắt.

QUY TRÌNH CHO MỖI DÒNG YÊU CẦU
1. Cổng áp dụng: dòng có áp dụng cho hồ sơ này không (loại nhà, điều kiện "nếu có…", biến thể, hạng mục có tồn tại trên \
bản vẽ không). Không áp dụng → status "not_applicable". Dòng không thuộc phạm vi bản vẽ (thủ tục, vận hành, khuyến cáo) \
cũng là "not_applicable".
2. Chọn mẫu kiểm tra:
   M1 so ngưỡng số · M2 giá trị thuộc danh mục cho phép · M3 phải có thành phần/lớp cấu tạo (kèm thông số) · \
M4 không được có thành phần/hạng mục · M5 vật liệu/quy cách thuộc loại cho phép · M6 tham chiếu tài liệu ngoài bản vẽ \
("theo PD CĐT", "xem BVKC", "theo danh mục vật tư") · M7 đánh giá chủ quan (thẩm mỹ, "đơn giản") · none nếu không mẫu nào khớp.
3. Xác định phạm vi (bộ phận/vị trí công trình) và yêu cầu cụ thể của dòng — đọc ĐÚNG câu chữ, đặc biệt các từ phủ định \
("không", "không được", "không thực hiện").
4. Tìm trong ngữ cảnh chỗ thể hiện đúng phạm vi đó (bảng thống kê cấu tạo, bảng vật liệu hoàn thiện, ghi chú, tiêu đề trang).
5. Kết luận:
   - "pass": thấy đúng đối tượng trong đúng phạm vi và thỏa yêu cầu.
   - "fail": thấy đối tượng, thuộc tính GHI RÕ và trái yêu cầu (M3: có mô tả cấu tạo của phạm vi nhưng thiếu thành phần; \
M4: có thể hiện thành phần bị cấm).
   - "warning": có dấu hiệu trái yêu cầu nhưng chưa chắc (ghi chú mơ hồ, "hoặc tương đương", lệch rất nhỏ).
   - "needs_review": không đủ căn cứ — không tìm thấy phạm vi/đối tượng, bản vẽ không ghi thuộc tính, M6, M7, hoặc bạn không chắc.
   Không tìm thấy KHÔNG có nghĩa là vi phạm. Không ghi KHÔNG có nghĩa là ghi sai.
   Dòng gồm nhiều yêu cầu: có yêu cầu trái → fail; còn yêu cầu không xác định → needs_review; tất cả thỏa → pass.
6. confidence (0–1): mức thấp nhất giữa độ chắc khi hiểu câu tiêu chí, khi xác định phạm vi trên bản vẽ và khi đọc dữ liệu.

ĐẦU RA — NGẮN GỌN (mọi chữ viết ra đều tốn chi phí; không lặp lại câu tiêu chí)
- Trả đúng một kết quả cho mỗi line_index được hỏi.
- evidence_ids: các mã khối làm căn cứ (tối đa 5, ưu tiên khối ghi trực tiếp giá trị). Rỗng nếu không có.
- pages_to_review: chỉ ghi khi evidence_ids rỗng mà vẫn có trang nên xem; ngược lại để rỗng.
- scope, requirement, found: mỗi trường tối đa 12 từ; found rỗng nếu không thấy.
- applicability_reason: chỉ ghi (tối đa 15 từ) khi applicability khác "applies"; ngược lại để rỗng.
- reason: tối đa 2 câu, ≤ 40 từ, nêu đã thấy gì (trang) và vì sao kết luận.
- Dòng not_applicable: scope, requirement, found, reason để rỗng — lý do ghi ở applicability_reason."""

RESULT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line_index": {"type": "integer"},
                    "applicability": {"type": "string", "enum": ["applies", "not_applicable", "unknown"]},
                    "applicability_reason": {"type": "string"},
                    "template": {"type": "string", "enum": ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "none"]},
                    "scope": {"type": "string"},
                    "requirement": {"type": "string"},
                    "found": {"type": "string"},
                    "status": {"type": "string",
                               "enum": ["pass", "fail", "warning", "needs_review", "not_applicable"]},
                    "confidence": {"type": "number"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "pages_to_review": {"type": "array", "items": {"type": "integer"}},
                    "reason": {"type": "string"},
                },
                "required": ["line_index", "applicability", "applicability_reason", "template", "scope",
                             "requirement", "found", "status", "confidence", "evidence_ids", "pages_to_review",
                             "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["lines"],
    "additionalProperties": False,
}

STATUS_MAP = {
    "pass": FindingStatus.PASS,
    "fail": FindingStatus.FAIL,
    "warning": FindingStatus.WARNING,
    "needs_review": FindingStatus.PENDING,
    "not_applicable": FindingStatus.PENDING,
}
ALWAYS_REVIEW_TEMPLATES = {"M6", "M7"}
NOT_APPLICABLE_PREFIX = "Không áp dụng"


@dataclass
class AiRun:
    results: list[LineResult] = field(default_factory=list)
    lines: list[dict] = field(default_factory=list)  # bản ghi thô từng dòng (để chấm điểm / đo ổn định)
    calls: list[dict] = field(default_factory=list)  # mỗi lần gọi: rule, model, USD, lỗi
    spent_usd: float = 0.0
    stopped: str | None = None  # lý do dừng giữa chừng (hết trần chi phí…)


class SemanticService:
    def __init__(self, provider: LlmProvider, max_usd_per_run: float = 1.0) -> None:
        self._provider = provider
        self._max_usd_per_run = max_usd_per_run

    def judge_rules(
        self,
        rules: list[RuleInput],
        digest: DossierDigest,
        house_type: HouseType | None,
        categories: list[ChtkCategory],
        only_lines: dict[str, set[int]] | None = None,
    ) -> AiRun:
        """Kiểm các dòng của từng rule bằng AI. only_lines: rule_id → các dòng cần AI (None = mọi dòng)."""
        run = AiRun()
        for rule in rules:
            wanted = sorted(only_lines.get(rule.rule_id, set())) if only_lines is not None else \
                list(range(len(rule.requirement_lines)))
            if not wanted:
                continue
            request = build_request(rule, wanted, digest, house_type, categories)
            if run.stopped is None:
                estimate = self._provider.estimate_usd(request)
                if run.spent_usd + estimate > self._max_usd_per_run:
                    run.stopped = (f"Dừng gọi AI: ước tính {run.spent_usd + estimate:.3f} USD vượt trần mỗi lần chạy "
                                   f"{self._max_usd_per_run:.2f} USD (MAIN_AI_MAX_USD_PER_RUN).")
            if run.stopped is not None:
                run.results.extend(_unknown(rule, wanted, run.stopped))
                continue
            try:
                response = self._provider.complete(request)
            except BudgetExceeded as exc:
                run.stopped = str(exc)
                run.results.extend(_unknown(rule, wanted, run.stopped))
                continue
            run.spent_usd += response.usd
            run.calls.append({"rule": _rule_label(rule), "ruleId": rule.rule_id, "model": response.model,
                              "usd": round(response.usd, 6), "error": response.error, "callId": response.call_id,
                              "replayed": response.replayed, "usage": response.usage.__dict__})
            if response.data is None:
                run.results.extend(_unknown(rule, wanted, f"AI lỗi: {response.error}"))
                continue
            results, records = interpret_response(rule, wanted, response.data, digest, response.model)
            for record in records:
                record["callId"] = response.call_id
            run.results.extend(results)
            run.lines.extend(records)
        return run


def build_request(
    rule: RuleInput, wanted: list[int], digest: DossierDigest, house_type: HouseType | None,
    categories: list[ChtkCategory],
) -> LlmRequest:
    parts = [
        "HỒ SƠ ĐANG KIỂM",
        f"- Loại nhà người dùng chọn: {house_type.value if house_type else 'không rõ'}",
        f"- Nhóm tiêu chí người dùng chọn: {', '.join(c.value for c in categories) or 'tất cả'}",
        "",
        "TIÊU CHÍ",
        f"- Mã: {rule.code or '(dòng biến thể)'}" + (f" — thuộc mục {rule.parent_code}" if rule.parent_code else ""),
    ]
    if rule.headings:
        parts.append(f"- Đề mục: {' > '.join(rule.headings)}")
    if rule.title:
        parts.append(f"- Tên: {rule.title}")
    if rule.house_types:
        parts.append(f"- Áp dụng cho loại nhà: {', '.join(h.value for h in rule.house_types)}")
    if rule.value:
        parts.append(f"- Giá trị chuẩn (cột riêng của bộ tiêu chí): {rule.operator.value + ' ' if rule.operator else ''}"
                     f"{rule.value}")
    parts.append("- Các dòng yêu cầu (line_index: nội dung):")
    for i in wanted:
        parts.append(f"  {i}: {rule.requirement_lines[i]}")
    parts.append("")
    parts.append(f"Trả kết quả cho các line_index: {', '.join(str(i) for i in wanted)}.")
    return LlmRequest(task="judge-rule", system=SYSTEM_PROMPT, context=digest.text, prompt="\n".join(parts),
                      schema=RESULT_SCHEMA)


def interpret_response(
    rule: RuleInput, wanted: list[int], data: dict, digest: DossierDigest, model: str
) -> tuple[list[LineResult], list[dict]]:
    """Hậu kiểm câu trả lời của AI → LineResult. Không tin AI ở chỗ code kiểm được (mã khối, mẫu M6/M7)."""
    by_index: dict[int, dict] = {}
    for item in data.get("lines", []):
        if isinstance(item, dict) and isinstance(item.get("line_index"), int) and item["line_index"] in wanted:
            by_index.setdefault(item["line_index"], item)

    results, records = [], []
    for i in wanted:
        item = by_index.get(i)
        if item is None:
            results.append(_unknown(rule, [i], "AI không trả kết quả cho dòng này.")[0])
            continue
        result, record = _line_result(rule, i, item, digest, model)
        results.append(result)
        records.append(record)
    return results, records


def _line_result(rule: RuleInput, index: int, item: dict, digest: DossierDigest, model: str) -> tuple[LineResult, dict]:
    raw_status = item.get("status", "needs_review")
    template = item.get("template", "none")
    confidence = _clamp(item.get("confidence", 0.0))
    notes: list[str] = []

    ids = [str(x) for x in item.get("evidence_ids", [])]
    valid = [x for x in dict.fromkeys(ids) if x in digest.blocks][:MAX_EVIDENCE]
    invalid = [x for x in ids if x not in digest.blocks]
    if invalid:
        confidence = _clamp(confidence - INVALID_CITATION_PENALTY)
        notes.append(f"bỏ {len(invalid)} mã khối không tồn tại")

    status = STATUS_MAP.get(raw_status, FindingStatus.PENDING)
    if template in ALWAYS_REVIEW_TEMPLATES and status != FindingStatus.PENDING:
        notes.append(f"mẫu {template} luôn cần người kiểm tra")
        status = FindingStatus.PENDING
    if status in (FindingStatus.PASS, FindingStatus.FAIL, FindingStatus.WARNING) and not valid:
        if status == FindingStatus.PASS and template == "M4":
            confidence = min(confidence, ABSENCE_CONFIDENCE_CAP)
            notes.append("không thấy thành phần bị cấm (vắng bằng chứng)")
        else:
            notes.append(f"AI kết luận '{raw_status}' nhưng không có bằng chứng hợp lệ")
            status = FindingStatus.PENDING

    reason = str(item.get("reason", "")).strip()
    if raw_status == "not_applicable":
        reason = f"{NOT_APPLICABLE_PREFIX}: {item.get('applicability_reason') or reason}"
    pages = sorted({int(p) for p in item.get("pages_to_review", []) if isinstance(p, int) and p > 0})
    if pages and status == FindingStatus.PENDING:
        reason += f" Trang nên xem: {', '.join(map(str, pages))}."
    if notes:
        reason += f" (Hậu kiểm: {'; '.join(notes)}.)"

    evidence = [
        Evidence(pageNumber=b.page_number, polygon=b.polygon, role=EvidenceRole.ANNOTATION, text=b.text)
        for b in (digest.blocks[x] for x in valid)
    ]
    result = LineResult(
        ruleId=rule.rule_id,
        lineIndex=index,
        status=status,
        confidence=confidence,
        reason=f"[AI · {template}] {reason}".strip(),
        extractedValue=str(item.get("found", "")) or None,
        standardValue=str(item.get("requirement", "")) or None,
        evidence=evidence,
    )
    record = {
        "ruleId": rule.rule_id, "code": _rule_label(rule), "lineIndex": index, "model": model,
        "promptVersion": PROMPT_VERSION, "aiStatus": raw_status, "status": status.value,
        "template": template, "applicability": item.get("applicability"), "scope": item.get("scope"),
        "confidence": confidence, "evidence": valid, "invalidEvidence": invalid,
        "evidencePages": sorted({digest.blocks[x].page_number for x in valid}), "pagesToReview": pages,
        "callId": None,
    }
    return result, record


def outcome_of(result: LineResult) -> str:
    """Kết luận theo 4 trạng thái của đối tác + "n/a" (không áp dụng) + "unknown" — dùng để chấm / duyệt."""
    if result.status == FindingStatus.PENDING and result.reason.startswith("[AI") and             f"] {NOT_APPLICABLE_PREFIX}:" in result.reason:
        return "n/a"
    return {FindingStatus.PASS: "pass", FindingStatus.FAIL: "fail", FindingStatus.WARNING: "warning",
            FindingStatus.PENDING: "pending"}.get(result.status, "unknown")


def _unknown(rule: RuleInput, lines: list[int], reason: str) -> list[LineResult]:
    return [LineResult(ruleId=rule.rule_id, lineIndex=i, status=FindingStatus.UNKNOWN, confidence=0.0, reason=reason)
            for i in lines]


def _rule_label(rule: RuleInput) -> str:
    return rule.code or f"{rule.parent_code} ({rule.title})"


def _clamp(value: object) -> float:
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))
