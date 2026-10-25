from collections.abc import Callable

from drawing_checker.common.enums import FindingStatus
from drawing_checker.common.geometry import Polygon
from drawing_checker.features.findings.schemas import (
    Applicability,
    BackendEvidence,
    BoundingBox,
    LineResult,
    RawFinding,
    RuleSnapshot,
)
from drawing_checker.features.rules.schemas import RuleInput

PageSizes = dict[int, tuple[float, float]]  # trang → (rộng, cao) point, trang đã xoay


class FindingsService:
    def __init__(self, confidence_threshold: float = 0.8) -> None:
        self._threshold = confidence_threshold

    def finalize(self, results: list[LineResult]) -> list[LineResult]:
        """Áp quy tắc trạng thái: không APPROVED; confidence < ngưỡng thì không được FAIL (→ WARNING)."""
        out = []
        for r in results:
            if r.status == FindingStatus.APPROVED:
                r = r.model_copy(update={"status": FindingStatus.PENDING,
                                         "reason": r.reason + " (MAIN không được tự xác nhận — chuyển pending.)"})
            if r.status == FindingStatus.FAIL and r.confidence < self._threshold:
                r = r.model_copy(update={"status": FindingStatus.WARNING,
                                         "reason": r.reason + f" (Độ tin cậy {r.confidence:.2f} < {self._threshold} — hạ xuống cảnh báo.)"})
            out.append(r)
        return out

    def to_backend(
        self,
        job_id: str,
        results: list[LineResult],
        rules: list[RuleInput],
        page_sizes: PageSizes,
        is_not_applicable: Callable[[LineResult], bool] = lambda _: False,
    ) -> list[RawFinding]:
        """Kết quả theo dòng → `RawFindingV1`: tọa độ point → % trang (Q-01), bbox chính = bao các bằng chứng
        cùng trang với bằng chứng đầu tiên. Gửi mọi kết quả, kể cả không áp dụng / chưa hỗ trợ.

        Không áp dụng → trạng thái `unknown` ("Không xác định" trên web, người dùng 2026-10-19 — không tách mục
        riêng); lý do "Không áp dụng: …" giữ nguyên, `applicability` chỉ là thông tin kèm theo.

        Một dòng có thể có nhiều kết quả (checker danh mục cửa: một kết quả / cửa) → `mainResultId` thêm số thứ tự.
        """
        by_id = {r.rule_id: r for r in rules}
        seen: dict[tuple[str, int], int] = {}
        out = []
        for r in self.finalize(results):
            k = seen.get((r.rule_id, r.line_index), 0)
            seen[(r.rule_id, r.line_index)] = k + 1
            rule = by_id.get(r.rule_id)
            evidence = [
                BackendEvidence(pageNumber=e.page_number, boundingBox=box, role=e.role, text=e.text)
                for e in r.evidence
                if (box := to_percent(e.polygon, page_sizes.get(e.page_number))) is not None
            ]
            page, box = None, None
            if evidence:
                page = evidence[0].page_number
                box = _union([e.bounding_box for e in evidence if e.page_number == page])
            status = r.status
            if is_not_applicable(r):
                applicability = Applicability.NOT_APPLICABLE
                status = FindingStatus.UNKNOWN
            elif r.status == FindingStatus.UNKNOWN:
                applicability = Applicability.UNKNOWN
            else:
                applicability = Applicability.APPLIES
            out.append(RawFinding(
                mainResultId=f"{job_id}:{r.rule_id}:{r.line_index}:{k}",
                ruleId=r.rule_id,
                lineIndex=r.line_index,
                rule=_snapshot(rule, r.line_index),
                status=status,
                applicability=applicability,
                confidence=r.confidence,
                extractedValue=r.extracted_value,
                standardValue=r.standard_value,
                reason=r.reason,
                pageNumber=page,
                boundingBox=box,
                evidence=evidence,
            ))
        return out


def to_percent(polygon: Polygon, size: tuple[float, float] | None) -> BoundingBox | None:
    """Polygon (point, trang đã xoay, gốc trên-trái) → bbox % 0–100 cùng trang; cắt phần tràn ra ngoài trang."""
    if size is None or size[0] <= 0 or size[1] <= 0:
        return None
    x, y, w, h = polygon.bounding_box()
    x0 = _clip(x / size[0] * 100)
    y0 = _clip(y / size[1] * 100)
    x1 = _clip((x + w) / size[0] * 100)
    y1 = _clip((y + h) / size[1] * 100)
    return BoundingBox(x=round(x0, 3), y=round(y0, 3), width=round(x1 - x0, 3), height=round(y1 - y0, 3))


def _union(boxes: list[BoundingBox]) -> BoundingBox:
    x0 = min(b.x for b in boxes)
    y0 = min(b.y for b in boxes)
    x1 = max(b.x + b.width for b in boxes)
    y1 = max(b.y + b.height for b in boxes)
    return BoundingBox(x=x0, y=y0, width=round(min(x1, 100) - x0, 3), height=round(min(y1, 100) - y0, 3))


def _clip(v: float) -> float:
    return max(0.0, min(100.0, v))


def _snapshot(rule: RuleInput | None, line_index: int) -> RuleSnapshot:
    if rule is None:
        return RuleSnapshot()
    lines = rule.requirement_lines
    return RuleSnapshot(code=rule.code, parentCode=rule.parent_code, title=rule.title or "",
                        requirementLine=lines[line_index] if line_index < len(lines) else "")
