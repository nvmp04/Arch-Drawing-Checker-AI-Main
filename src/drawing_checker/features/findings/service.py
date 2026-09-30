from drawing_checker.features.findings.schemas import LineResult, RawFinding


class FindingsService:
    def finalize(self, results: list[LineResult]) -> list[LineResult]:
        """Áp quy tắc trạng thái: không APPROVED; confidence < ngưỡng thì không được FAIL."""
        raise NotImplementedError

    def to_backend(self, results: list[LineResult]) -> list[RawFinding]:
        """Chuyển sang payload BE (bbox bao ngoài từ polygon chính + evidence đầy đủ)."""
        raise NotImplementedError
