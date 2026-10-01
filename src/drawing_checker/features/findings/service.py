from drawing_checker.common.enums import FindingStatus
from drawing_checker.features.findings.schemas import LineResult, RawFinding


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

    def to_backend(self, results: list[LineResult]) -> list[RawFinding]:
        """Chuyển sang payload BE (bbox bao ngoài từ polygon chính + evidence đầy đủ). Chờ hợp đồng v1."""
        raise NotImplementedError
