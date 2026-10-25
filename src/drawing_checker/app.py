import logging

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from drawing_checker import __version__
from drawing_checker.common.security import basic_auth_user
from drawing_checker.config import get_settings
from drawing_checker.features.analyses.router import router as analyses_router
from drawing_checker.features.benchmark.router import router as reviews_router
from drawing_checker.features.capabilities.router import router as capabilities_router
from drawing_checker.features.health.router import router as health_router
from drawing_checker.features.ingest.inspector import write_runs_index


def _configure_logging() -> None:
    """Uvicorn chỉ cấu hình logger của nó — bật log INFO cho package để thấy tiến trình job."""
    logger = logging.getLogger("drawing_checker")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


def create_app() -> FastAPI:
    _configure_logging()
    app = FastAPI(
        title="Arch Drawing Checker — MAIN",
        description="Lõi AI phân tích bản vẽ PDF vector, đối chiếu tiêu chí CHTK. Khung xương — xem AGENTS.md.",
        version=__version__,
    )
    settings = get_settings()
    app.include_router(health_router)
    if not settings.review_only:
        app.include_router(capabilities_router)
        app.include_router(analyses_router)
    else:
        if settings.review_password is None:
            raise RuntimeError("MAIN_REVIEW_ONLY=true cần MAIN_REVIEW_PASSWORD — không mở viewer ra mạng khi chưa có mật khẩu.")

        @app.get("/", include_in_schema=False)
        def _root() -> RedirectResponse:
            return RedirectResponse("/debug/inspect/")

    if settings.review_password is not None:
        password = settings.review_password.get_secret_value()

        @app.middleware("http")
        async def _review_login(request: Request, call_next):
            # Chế độ chấm cho đối tác: mọi đường /debug/* cần mật khẩu chung; tên đăng nhập = người chấm.
            if not request.url.path.startswith("/debug"):
                return await call_next(request)
            user = basic_auth_user(request.headers.get("authorization"), password)
            if user is None:
                return PlainTextResponse("Cần đăng nhập: tên của bạn + mật khẩu chung.", status_code=401,
                                         headers={"WWW-Authenticate": 'Basic realm="cham-ket-qua", charset="UTF-8"'})
            request.state.reviewer = user
            return await call_next(request)

    if settings.inspect_enabled:
        # Viewer debug kết quả ingest theo job + API ghi kết quả duyệt — KHÔNG xác thực, chỉ dùng khi phát triển.
        app.include_router(reviews_router)
        settings.inspect_dir.mkdir(parents=True, exist_ok=True)
        write_runs_index(settings.inspect_dir)
        app.mount("/debug/inspect", StaticFiles(directory=settings.inspect_dir, html=True), name="inspect")
    return app


app = create_app()
