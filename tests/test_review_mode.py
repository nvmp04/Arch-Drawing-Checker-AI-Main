"""Chế độ chấm cho đối tác: mật khẩu chung + tên đăng nhập = người chấm; chỉ mở viewer + API chấm."""

import base64
from pathlib import Path
import json

from fastapi.testclient import TestClient

from drawing_checker.common.security import basic_auth_user
from drawing_checker.config import get_settings

DOSSIER = "0123456789abcdef"
BODY = {"ruleId": "r1", "lineIndex": 0, "verdict": "correct", "predicted": "pass", "expected": "pass"}


def _basic(user: str, password: str) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode()
    return {"Authorization": f"Basic {token}"}


def test_basic_auth_user():
    assert basic_auth_user(_basic("Tuấn", "pw")["Authorization"], "pw") == "Tuấn"
    assert basic_auth_user(_basic("tuan", "sai")["Authorization"], "pw") is None
    assert basic_auth_user(_basic("  ", "pw")["Authorization"], "pw") is None
    assert basic_auth_user("Basic !!!", "pw") is None
    assert basic_auth_user("Bearer abc", "pw") is None
    assert basic_auth_user(None, "pw") is None


def _app(monkeypatch, tmp_path):
    monkeypatch.setenv("MAIN_REVIEW_PASSWORD", "pw")
    monkeypatch.setenv("MAIN_REVIEW_ONLY", "true")
    monkeypatch.setenv("MAIN_REVIEWS_DIR", str(tmp_path / "reviews"))
    monkeypatch.setenv("MAIN_INSPECT_DIR", str(tmp_path / "inspect"))
    get_settings.cache_clear()
    from drawing_checker.app import create_app

    return TestClient(create_app())


def test_review_mode(monkeypatch, tmp_path):
    try:
        client = _app(monkeypatch, tmp_path)
        assert client.get("/health").status_code == 200  # không cần đăng nhập
        assert client.get("/debug/inspect/").status_code == 401
        assert client.post(f"/debug/reviews/{DOSSIER}", json=BODY).status_code == 401
        assert client.get("/debug/inspect/", headers=_basic("an", "sai")).status_code == 401
        assert client.get("/debug/inspect/", headers=_basic("an", "pw")).status_code == 200

        # Tên người chấm lấy từ đăng nhập, trình duyệt gửi tên khác cũng bị thay.
        res = client.post(f"/debug/reviews/{DOSSIER}", json={**BODY, "reviewer": "giả"},
                          headers=_basic("Kỹ sư An", "pw"))
        assert res.status_code == 201 and res.json()["reviewer"] == "Kỹ sư An"
        row = json.loads((tmp_path / "reviews" / f"{DOSSIER}.jsonl").read_text(encoding="utf-8"))
        assert row["reviewer"] == "Kỹ sư An"

        root = client.get("/", follow_redirects=False)
        assert root.status_code == 307 and root.headers["location"] == "/debug/inspect/"
        # review_only: API nhận việc từ BE không mở.
        assert client.post("/v1/analyses", json={}).status_code == 404
    finally:
        get_settings.cache_clear()


def test_review_only_requires_password(monkeypatch):
    import pytest

    monkeypatch.delenv("MAIN_REVIEW_PASSWORD", raising=False)
    monkeypatch.setenv("MAIN_REVIEW_ONLY", "true")
    monkeypatch.chdir(Path(__file__).parent)  # không đọc .env của repo
    get_settings.cache_clear()
    from drawing_checker.app import create_app

    try:
        with pytest.raises(RuntimeError):
            create_app()
    finally:
        get_settings.cache_clear()


def test_pg_store_selected(monkeypatch):
    from drawing_checker.features.benchmark import router
    from drawing_checker.features.benchmark.reviews import PgReviewStore, ReviewStore

    monkeypatch.setenv("MAIN_REVIEWS_DATABASE_URL", "")  # đè giá trị trong .env (nếu có)
    get_settings.cache_clear()
    assert isinstance(router._store(), ReviewStore)
    monkeypatch.setenv("MAIN_REVIEWS_DATABASE_URL", "postgresql://u:p@localhost/db")
    get_settings.cache_clear()
    try:
        assert isinstance(router._store(), PgReviewStore)  # chưa kết nối khi khởi tạo
    finally:
        get_settings.cache_clear()
