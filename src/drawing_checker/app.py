import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from drawing_checker import __version__
from drawing_checker.config import get_settings
from drawing_checker.features.analyses.router import router as analyses_router
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
    app.include_router(health_router)
    app.include_router(capabilities_router)
    app.include_router(analyses_router)

    settings = get_settings()
    if settings.inspect_enabled:
        # Viewer debug kết quả ingest theo job — KHÔNG xác thực, chỉ dùng khi phát triển.
        settings.inspect_dir.mkdir(parents=True, exist_ok=True)
        write_runs_index(settings.inspect_dir)
        app.mount("/debug/inspect", StaticFiles(directory=settings.inspect_dir, html=True), name="inspect")
    return app


app = create_app()
