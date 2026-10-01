"""Bắt tay BE ↔ MAIN v0 (arch-drawing-checker-backend/docs/contracts/be-main.md) với BE giả lập."""

import asyncio
import json
from pathlib import Path

import httpx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from drawing_checker.app import app
from drawing_checker.features.analyses.router import get_analyses_service
from drawing_checker.features.analyses.schemas import DispatchRequest, DispatchResult
from drawing_checker.features.analyses.service import AnalysesService
from drawing_checker.infrastructure import backend_client
from drawing_checker.infrastructure.backend_client import BackendClient
from drawing_checker.infrastructure.job_runner import JobRunner
from drawing_checker.infrastructure.pdf_fetcher import PdfFetcher

REVIEW_ID = "b61be92e-8d5f-4452-b875-566bde9a1aa6"
PDF_URL = f"http://be/api/v1/internal/reviews/{REVIEW_ID}/file?expires=1790000000&signature=abc"
CALLBACK_URL = "http://be/api/v1/internal/analysis/callback"
CALLBACK_FIELDS = {"reviewId", "externalJobId", "stage", "state", "percent", "pageCount", "errorMessage", "findings"}

DISPATCH_BODY = {
    "reviewId": REVIEW_ID,
    "pdfUrl": PDF_URL,
    "houseType": "townhouse",
    "categories": ["facade", "stair-ramp"],
    "rules": [],
    "callbackUrl": CALLBACK_URL,
}


def make_pdf(pages: int = 3, password: str | None = None) -> bytes:
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page()
    if password:
        return doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
    return doc.tobytes()


class FakeBackend:
    """BE giả lập: phục vụ PDF qua URL có chữ ký, nhận callback, kiểm header + trường thừa."""

    def __init__(self, pdf: bytes | None = None, pdf_error: tuple[int, str] | None = None, callback_statuses=()):
        self.pdf = pdf if pdf is not None else make_pdf()
        self.pdf_error = pdf_error
        self.callback_statuses = list(callback_statuses)
        self.callbacks: list[dict] = []
        self.pdf_requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            self.pdf_requests.append(request)
            assert str(request.url) == PDF_URL  # dùng nguyên văn
            if self.pdf_error:
                code, error_code = self.pdf_error
                return httpx.Response(code, json={"error": {"statusCode": code, "code": error_code}})
            return httpx.Response(200, content=self.pdf, headers={"Content-Type": "application/pdf"})
        assert str(request.url) == CALLBACK_URL
        assert request.headers["x-internal-token"] == "cb-token"
        body = json.loads(request.content)
        assert set(body) <= CALLBACK_FIELDS, f"trường thừa: {set(body) - CALLBACK_FIELDS}"
        self.callbacks.append(body)
        status = self.callback_statuses.pop(0) if self.callback_statuses else 204
        return httpx.Response(status)


MOCK_RULESET = Path(__file__).resolve().parent.parent / "samples" / "criteria" / "ruleset-4sao.json"


def make_service(
    fake: FakeBackend, tmp_path: Path, inspect_dir: Path | None = None, mock_ruleset: Path | None = None
) -> AnalysesService:
    transport = httpx.MockTransport(fake.handler)
    return AnalysesService(
        backend=BackendClient("cb-token", transport=transport),
        fetcher=PdfFetcher(tmp_path, transport=transport),
        runner=JobRunner(),
        inspect_dir=inspect_dir,
        inspect_dpi=20,
        mock_ruleset=mock_ruleset,
    )


def run_job(
    fake: FakeBackend, tmp_path: Path, inspect_dir: Path | None = None, mock_ruleset: Path | None = None
) -> tuple[AnalysesService, str]:
    async def scenario() -> tuple[AnalysesService, str]:
        service = make_service(fake, tmp_path, inspect_dir, mock_ruleset)
        result = await service.dispatch(DispatchRequest.model_validate(DISPATCH_BODY))
        while any(not t.done() for t in asyncio.all_tasks() if t is not asyncio.current_task()):
            await asyncio.sleep(0.01)
        return service, result.external_job_id

    return asyncio.run(scenario())


def stages(fake: FakeBackend) -> list[tuple]:
    return [(c["stage"], c["state"], c["percent"]) for c in fake.callbacks]


@pytest.fixture(autouse=True)
def fast_retry(monkeypatch):
    monkeypatch.setattr(backend_client, "RETRY_DELAYS", (0, 0, 0))


def test_happy_path_ingests_pages_and_reports_progress(tmp_path: Path) -> None:
    fake = FakeBackend(pdf=make_pdf(pages=4))
    work, inspect = tmp_path / "work", tmp_path / "inspect"
    service, job_id = run_job(fake, work, inspect)

    assert stages(fake) == [
        ("extract", "running", 5),  # nhận việc
        ("extract", "running", 10),  # đã tải PDF
        ("extract", "running", 30), ("extract", "running", 50), ("extract", "running", 70),  # từng trang
        ("extract", "completed", 90),
        ("aggregate", "completed", 100),
    ]
    assert all(c["reviewId"] == REVIEW_ID and c["externalJobId"] == job_id for c in fake.callbacks)
    assert fake.callbacks[-2]["pageCount"] == 4
    assert fake.callbacks[-1]["findings"] == []
    assert "findings" not in fake.callbacks[0] and "errorMessage" not in fake.callbacks[0]
    assert "authorization" not in fake.pdf_requests[0].headers  # chữ ký nằm trong URL
    assert not list(work.iterdir())  # đã dọn PDF tạm
    assert asyncio.run(service.get_status(job_id)).percent == 100

    # Viewer debug của job: 4 trang dữ liệu + ảnh, meta, danh sách lần chạy.
    job_dir = inspect / job_id
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "completed" and meta["reviewId"] == REVIEW_ID and meta["houseType"] == "townhouse"
    assert [p["n"] for p in meta["pages"]] == [1, 2, 3, 4]
    assert (job_dir / "index.html").exists() and (job_dir / "p004.js").exists() and (job_dir / "p004.jpg").exists()
    assert job_id in (inspect / "index.html").read_text(encoding="utf-8")


def test_mock_ruleset_runs_rule_engine_and_writes_checks(tmp_path: Path) -> None:
    fake = FakeBackend(pdf=make_pdf(pages=2))
    _, job_id = run_job(fake, tmp_path / "work", tmp_path / "inspect", MOCK_RULESET)
    assert fake.callbacks[-1] == {**fake.callbacks[-1], "stage": "aggregate", "findings": []}  # BE vẫn chưa nhận findings
    job_dir = tmp_path / "inspect" / job_id
    checks = (job_dir / "checks.js").read_text(encoding="utf-8")
    assert checks.startswith("window.__ingestChecks(") and '"houseType":"townhouse"' in checks
    meta = json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["checks"]["rulesTotal"] == 92 and meta["checks"]["source"].startswith("mock")


def test_failed_job_is_recorded_in_viewer_index(tmp_path: Path) -> None:
    fake = FakeBackend(pdf=make_pdf(password="x"))
    _, job_id = run_job(fake, tmp_path / "work", tmp_path / "inspect")
    meta = json.loads((tmp_path / "inspect" / job_id / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "failed" and "mã hóa" in meta["error"]


@pytest.mark.parametrize(
    ("pdf_error", "message"),
    [((403, "SIGNED_URL_EXPIRED"), "hết hạn"), ((404, "REVIEW_NOT_FOUND"), "Không tìm thấy hồ sơ")],
)
def test_pdf_download_error_reports_failed(tmp_path: Path, pdf_error, message) -> None:
    fake = FakeBackend(pdf_error=pdf_error)
    run_job(fake, tmp_path)
    assert stages(fake) == [("extract", "running", 5), ("extract", "failed", 5)]
    assert message in fake.callbacks[-1]["errorMessage"]


@pytest.mark.parametrize(
    ("pdf", "message"),
    [(make_pdf(password="x"), "PDF bị mã hóa"), (b"%PDF-1.7 garbage", "Không đọc được"), (b"<html>", "không phải PDF")],
)
def test_unreadable_pdf_reports_failed(tmp_path: Path, pdf: bytes, message: str) -> None:
    fake = FakeBackend(pdf=pdf)
    run_job(fake, tmp_path)
    assert fake.callbacks[-1]["state"] == "failed"
    assert message in fake.callbacks[-1]["errorMessage"]
    assert not list(tmp_path.iterdir())


def test_callback_5xx_is_retried(tmp_path: Path) -> None:
    fake = FakeBackend(callback_statuses=[503, 502])
    run_job(fake, tmp_path)
    assert stages(fake)[:3] == [("extract", "running", 5)] * 3
    assert stages(fake)[-1] == ("aggregate", "completed", 100)


@pytest.mark.parametrize("status", [409, 404, 400, 401])
def test_callback_rejection_stops_job_without_retry(tmp_path: Path, status: int) -> None:
    fake = FakeBackend(callback_statuses=[status])
    service, job_id = run_job(fake, tmp_path)
    assert len(fake.callbacks) == 1
    assert asyncio.run(service.get_status(job_id)).state == "failed"


# --- API (FastAPI) ---------------------------------------------------------


class StubService:
    def __init__(self) -> None:
        self.cancelled: list[str] = []

    async def dispatch(self, request: DispatchRequest) -> DispatchResult:
        return DispatchResult(externalJobId="job-1", stage="extract")

    async def cancel(self, job_id: str) -> None:
        from drawing_checker.features.analyses.service import JobNotFound

        if job_id != "job-1":
            raise JobNotFound(job_id)
        self.cancelled.append(job_id)


@pytest.fixture
def api():
    stub = StubService()
    app.dependency_overrides[get_analyses_service] = lambda: stub
    yield TestClient(app), stub
    app.dependency_overrides.clear()


AUTH = {"Authorization": "Bearer change-me-ai-token"}


def test_dispatch_returns_202_with_job_id(api) -> None:
    client, _ = api
    response = client.post("/v1/analyses", json=DISPATCH_BODY, headers=AUTH)
    assert response.status_code == 202
    assert response.json() == {"externalJobId": "job-1", "stage": "extract"}


def test_dispatch_accepts_rules_with_null_fields(api) -> None:
    client, _ = api
    rule = {"ruleId": "r1", "code": None, "checkType": None, "operator": None, "value": None}
    response = client.post("/v1/analyses", json={**DISPATCH_BODY, "rules": [rule]}, headers=AUTH)
    assert response.status_code == 202


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer sai"}, {"Authorization": "change-me-ai-token"}])
def test_dispatch_requires_bearer_token(api, headers) -> None:
    client, _ = api
    assert client.post("/v1/analyses", json=DISPATCH_BODY, headers=headers).status_code == 401


def test_dispatch_rejects_bad_body(api) -> None:
    client, _ = api
    assert client.post("/v1/analyses", json={"reviewId": REVIEW_ID}, headers=AUTH).status_code == 422


def test_cancel(api) -> None:
    client, stub = api
    assert client.delete("/v1/analyses/job-1", headers=AUTH).status_code == 204
    assert stub.cancelled == ["job-1"]
    assert client.delete("/v1/analyses/unknown", headers=AUTH).status_code == 404
    assert client.delete("/v1/analyses/job-1").status_code == 401
