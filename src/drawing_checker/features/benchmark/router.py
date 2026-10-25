"""API ghi / đọc kết quả duyệt từ viewer debug — chỉ đăng ký khi MAIN_INSPECT_ENABLED.

Không xác thực trên máy dev; đặt MAIN_REVIEW_PASSWORD thì app.py đòi đăng nhập và ghi tên người chấm.
"""

from fastapi import APIRouter, HTTPException, Request

from drawing_checker.config import get_settings
from drawing_checker.features.benchmark.reviews import PgReviewStore, ReviewInput, ReviewStore

router = APIRouter(prefix="/debug/reviews", tags=["debug"])


def _store() -> ReviewStore | PgReviewStore:
    settings = get_settings()
    url = settings.reviews_database_url.get_secret_value() if settings.reviews_database_url else ""
    if url:
        return PgReviewStore(url)
    return ReviewStore(settings.reviews_dir)


@router.get("/{dossier}")
def list_reviews(dossier: str) -> list[dict]:
    try:
        return list(_store().latest(dossier).values())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dossier}", status_code=201)
def add_review(dossier: str, review: ReviewInput, request: Request) -> dict:
    review.reviewer = getattr(request.state, "reviewer", None)
    try:
        return _store().append(dossier, review)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
