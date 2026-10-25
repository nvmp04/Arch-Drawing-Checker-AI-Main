from functools import lru_cache
from pathlib import Path

from typing import Literal

from pydantic import SecretStr
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
    # Chế độ chấm cho đối tác (máy Oracle): đặt mật khẩu → /debug/* đòi đăng nhập Basic (tên đăng nhập = tên
    # người chấm, ghi vào mỗi dòng duyệt). Để trống = không xác thực (chỉ máy dev).
    review_password: SecretStr | None = None
    # Chỉ mở viewer + API chấm (tắt API nhận việc từ BE). Dùng cùng review_password khi đưa lên mạng.
    review_only: bool = False
    # Bộ rule MOCK khi BE gửi `rules: []` (hợp đồng v0) — đợt thử rule engine. Để trống để tắt.
    mock_ruleset: Path | None = Path("samples/criteria/ruleset-4sao.json")

    # --- AI (D-22). MẶC ĐỊNH TẮT: gọi Claude tốn tiền, chỉ người dùng tự bật (AGENTS.md §6). ---
    # off: không AI · claude: gọi Anthropic API thật · replay: phát lại các lần gọi thật đã ghi (miễn phí)
    ai_provider: Literal["off", "claude", "replay"] = "off"
    ai_model: str = "claude-opus-5-5"  # đổi: claude-sonnet-5-5 (rẻ ~2×), claude-haiku-5-5 (rẻ ~40×)
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    ai_monthly_budget_usd: float = 5.0  # hàng rào phía MAIN; đặt thêm giới hạn chi tiêu trong Anthropic Console
    ai_max_usd_per_run: float = 1.0  # trần chi phí MỘT lần kiểm một hồ sơ
    ai_dir: Path = Path("data/ai")  # sổ chi tiêu + bản ghi các lần gọi (phát lại, nhật ký D-20)
    # Kết quả người duyệt chấm trên viewer (đáp án dùng lại cho mọi lần chạy) — tách khỏi ai_dir.
    reviews_dir: Path = Path("data/reviews")
    # Có giá trị → kết quả chấm lưu vào Postgres (Neon) thay cho file — bắt buộc trên Render (D-24).
    reviews_database_url: SecretStr | None = None
    ai_include_numeric: bool = False  # gửi cả khối chữ chỉ có số (kích thước) — tăng ~60% token
    anthropic_api_key: SecretStr | None = None  # để trống → SDK tự đọc ANTHROPIC_API_KEY


@lru_cache
def get_settings() -> Settings:
    return Settings()
