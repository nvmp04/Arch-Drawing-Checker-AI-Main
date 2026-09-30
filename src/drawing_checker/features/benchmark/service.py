"""Chấm điểm kết quả MAIN với comment thật của người kiểm tra (samples/ground-truth/)."""

from pathlib import Path

from pydantic import BaseModel

from drawing_checker.features.findings.schemas import LineResult


class BenchmarkReport(BaseModel):
    matched: int
    missed: int
    extra: int
    precision: float
    recall: float


class BenchmarkService:
    def run(self, results: list[LineResult], ground_truth: Path) -> BenchmarkReport:
        raise NotImplementedError
