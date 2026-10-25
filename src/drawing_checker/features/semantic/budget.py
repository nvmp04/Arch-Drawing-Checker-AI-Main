"""Giá model + sổ chi tiêu AI theo tháng. Chặn gọi khi vượt hạn mức (người dùng chốt 5 USD/tháng, 2026-10-09).

Sổ là file JSON Lines trên máy chạy MAIN (`data/ai/usage.jsonl`): mỗi lần gọi một dòng — thời điểm, model, token,
USD. Đây là hàng rào phía MAIN; hàng rào cứng vẫn là giới hạn chi tiêu đặt trong Anthropic Console.
"""

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Price:
    """USD / 1 triệu token. Ghi cache 5 phút = 1.25 × giá vào."""

    input: float
    output: float
    cache_read: float
    # Haiku 5.5: prompt > 100K token tính giá cao hơn.
    long_prompt_threshold: int | None = None
    long_input: float | None = None
    long_output: float | None = None


# Bảng giá Anthropic API (skill claude-api, cập nhật 2026-10-06). Model ngoài bảng → tính theo giá cao nhất (an toàn).
PRICES: dict[str, Price] = {
    "claude-opus-5-5": Price(4.0, 20.0, 0.20),
    "claude-opus-5": Price(5.0, 25.0, 0.50),
    "claude-opus-4-8": Price(5.0, 25.0, 0.50),
    "claude-sonnet-5-5": Price(2.0, 10.0, 0.20),
    "claude-sonnet-5": Price(2.0, 10.0, 0.20),
    "claude-haiku-5-5": Price(0.10, 0.50, 0.01, long_prompt_threshold=100_000, long_input=0.50, long_output=2.50),
    "claude-haiku-4-5": Price(1.0, 5.0, 0.10),
}
FALLBACK_PRICE = Price(10.0, 50.0, 1.0)


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def prompt_tokens(self) -> int:
        return self.input_tokens + self.cache_write_tokens + self.cache_read_tokens


def price_of(model: str) -> Price:
    return PRICES.get(model, FALLBACK_PRICE)


def cost_usd(model: str, usage: Usage) -> float:
    p = price_of(model)
    inp, out, read = p.input, p.output, p.cache_read
    if p.long_prompt_threshold is not None and usage.prompt_tokens > p.long_prompt_threshold:
        scale = (p.long_input or inp) / inp
        inp, out, read = p.long_input or inp, p.long_output or out, read * scale
    return (usage.input_tokens * inp + usage.cache_write_tokens * inp * 1.25
            + usage.cache_read_tokens * read + usage.output_tokens * out) / 1_000_000


class BudgetExceeded(RuntimeError):
    pass


class UsageLedger:
    def __init__(self, path: Path, monthly_budget_usd: float) -> None:
        self._path = path
        self._budget = monthly_budget_usd
        self._lock = threading.Lock()

    @property
    def budget(self) -> float:
        return self._budget

    def month_spent(self, now: datetime | None = None) -> float:
        month = (now or datetime.now(timezone.utc)).strftime("%Y-%m")
        if not self._path.exists():
            return 0.0
        total = 0.0
        for line in self._path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("at", "")).startswith(month):
                total += float(row.get("usd", 0.0))
        return total

    def ensure_can_spend(self, estimate_usd: float) -> None:
        spent = self.month_spent()
        if spent + estimate_usd > self._budget:
            raise BudgetExceeded(
                f"Vượt hạn mức AI tháng này: đã dùng {spent:.3f} USD + ước tính {estimate_usd:.3f} USD "
                f"> {self._budget:.2f} USD (MAIN_AI_MONTHLY_BUDGET_USD)."
            )

    def record(self, model: str, usage: Usage, usd: float, task: str, call_id: str) -> None:
        row = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": model, "task": task, "callId": call_id, "usd": round(usd, 6),
            "input": usage.input_tokens, "output": usage.output_tokens,
            "cacheWrite": usage.cache_write_tokens, "cacheRead": usage.cache_read_tokens,
        }
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")


def estimate_tokens(text: str) -> int:
    """Ước lượng thô khi chưa gọi API: tiếng Việt có dấu ~2 ký tự / token (thiên về cao). Số thật xem sổ chi tiêu."""
    return len(text) // 2 + 1
