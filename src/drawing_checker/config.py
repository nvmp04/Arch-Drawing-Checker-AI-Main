from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường tiền tố MAIN_ (xem .env.example)."""

    model_config = SettingsConfigDict(env_prefix="MAIN_", env_file=".env", extra="ignore")

    # Token BE gửi khi gọi MAIN (khớp AI_SERVICE_TOKEN bên BE).
    service_token: str = "change-me-ai-token"
    # Token MAIN gửi trong header x-internal-token khi gọi callback BE.
    callback_token: str = "change-me-callback-token"
    # Khớp CONFIDENCE_THRESHOLD của BE/FE: dưới ngưỡng không được trả `fail`.
    confidence_threshold: float = 0.8
    work_dir: Path = Path("data/work")
    # Viewer debug kết quả ingest của từng job, phục vụ tại /debug/inspect/ (KHÔNG xác thực — tắt khi triển khai).
    inspect_enabled: bool = True
    inspect_dir: Path = Path("data/inspect")
    inspect_dpi: int = 110  # ảnh nền viewer; 0 = không render


@lru_cache
def get_settings() -> Settings:
    return Settings()
