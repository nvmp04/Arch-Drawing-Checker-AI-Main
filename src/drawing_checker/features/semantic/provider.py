"""Cổng gọi model ngôn ngữ — MỘT giao diện, nhiều nhà cung cấp (D-22). Đổi model / nhà cung cấp không đụng chỗ khác.

- `ClaudeProvider`: gọi Anthropic API thật (tốn tiền). Chỉ bật bằng cấu hình `MAIN_AI_PROVIDER=claude`.
- `ReplayProvider`: phát lại câu trả lời đã ghi của lần gọi thật — miễn phí, dùng khi sửa code đọc bản vẽ / hậu kiểm.
  KHÔNG dùng khi đo độ ổn định (online-rollout.md).
- `FakeProvider`: model giả cho test.

Mỗi lần gọi thật ghi một bản ghi `data/ai/calls/<khóa>.json` (yêu cầu + trả lời + token + USD) — vừa để phát lại,
vừa là nhật ký AI của vòng duyệt (D-20). Phần ngữ cảnh lớn (bản tóm tắt hồ sơ) lưu một lần theo mã băm.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from drawing_checker.features.semantic.budget import (
    BudgetExceeded,
    Usage,
    UsageLedger,
    cost_usd,
    estimate_tokens,
    price_of,
)

logger = logging.getLogger(__name__)

# Model có fallback phía máy chủ khi bị bộ lọc an toàn từ chối (skill claude-api). Haiku không có.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
NO_EFFORT_MODELS = {"claude-haiku-4-5"}  # model không nhận output_config.effort
EXPECTED_OUTPUT_TOKENS = 4000  # dự phòng khi ước tính chi phí trước khi gọi (gồm token suy nghĩ)


@dataclass
class LlmRequest:
    task: str  # "judge-rule" — để thống kê chi phí theo việc
    system: str  # hướng dẫn cố định
    context: str  # ngữ cảnh lớn dùng chung nhiều lần gọi (bản tóm tắt hồ sơ) — được cache
    prompt: str  # phần riêng của lần gọi
    schema: dict  # JSON Schema của câu trả lời (structured outputs)
    max_tokens: int = 16000

    def key(self, model: str) -> str:
        h = hashlib.sha256()
        for part in (model, self.system, self.context, self.prompt, json.dumps(self.schema, sort_keys=True)):
            h.update(part.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()[:32]


@dataclass
class LlmResponse:
    data: dict | None  # JSON đã parse; None khi lỗi
    model: str  # model thực sự trả lời (khác model yêu cầu nếu bị chuyển fallback)
    call_id: str
    usage: Usage = field(default_factory=Usage)
    usd: float = 0.0
    stop_reason: str | None = None
    error: str | None = None  # lỗi tiếng Việt cho người đọc
    replayed: bool = False


class LlmProvider(Protocol):
    name: str
    model: str

    def complete(self, request: LlmRequest) -> LlmResponse: ...

    def estimate_usd(self, request: LlmRequest) -> float: ...


CACHE_TTL_SECONDS = 280  # cache 5 phút của API, trừ hao


def _estimate(model: str, request: LlmRequest, context_warm: bool = False) -> float:
    """Ước tính thận trọng để chặn trước khi gọi: ngữ cảnh tính giá ghi cache, hoặc giá đọc cache nếu vừa gửi."""
    p = price_of(model)
    fresh = estimate_tokens(request.system) + estimate_tokens(request.prompt)
    context = estimate_tokens(request.context) * (p.cache_read if context_warm else p.input * 1.25)
    return (fresh * p.input + context + EXPECTED_OUTPUT_TOKENS * p.output) / 1_000_000


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


class FakeProvider:
    """Model giả: `handler(request) -> dict`. Không mạng, không tiền."""

    name = "fake"

    def __init__(self, handler: Callable[[LlmRequest], dict], model: str = "fake-model") -> None:
        self._handler = handler
        self.model = model
        self.requests: list[LlmRequest] = []

    def complete(self, request: LlmRequest) -> LlmResponse:
        self.requests.append(request)
        return LlmResponse(data=self._handler(request), model=self.model, call_id=request.key(self.model),
                           stop_reason="end_turn")

    def estimate_usd(self, request: LlmRequest) -> float:
        return 0.0


class CallStore:
    """Bản ghi các lần gọi thật: `<dir>/<khóa>.json` + `<dir>/context/<sha>.txt`."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory

    def path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def load(self, key: str) -> dict | None:
        p = self.path(key)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def save(self, key: str, request: LlmRequest, response: LlmResponse) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        context_sha = hashlib.sha256(request.context.encode("utf-8")).hexdigest()[:32]
        context_path = self._dir / "context" / f"{context_sha}.txt"
        if not context_path.exists():
            context_path.parent.mkdir(parents=True, exist_ok=True)
            context_path.write_text(request.context, encoding="utf-8")
        record = {
            "key": key, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task": request.task, "model": response.model,
            "request": {"system": request.system, "contextSha": context_sha, "prompt": request.prompt,
                        "schema": request.schema, "maxTokens": request.max_tokens},
            "response": {"data": response.data, "stopReason": response.stop_reason, "error": response.error},
            "usage": response.usage.__dict__, "usd": response.usd,
        }
        self.path(key).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


class ReplayProvider:
    """Phát lại câu trả lời đã ghi. Chưa có bản ghi → lỗi (không tự gọi API)."""

    name = "replay"

    def __init__(self, store: CallStore, model: str) -> None:
        self._store = store
        self.model = model

    def complete(self, request: LlmRequest) -> LlmResponse:
        key = request.key(self.model)
        record = self._store.load(key)
        if record is None:
            return LlmResponse(data=None, model=self.model, call_id=key,
                               error="Chưa có bản ghi lần gọi thật cho yêu cầu này (chế độ phát lại không gọi API).")
        resp = record["response"]
        return LlmResponse(data=resp.get("data"), model=record.get("model", self.model), call_id=key,
                           usage=Usage(**record.get("usage", {})), usd=0.0, stop_reason=resp.get("stopReason"),
                           error=resp.get("error"), replayed=True)

    def estimate_usd(self, request: LlmRequest) -> float:
        return 0.0


class ClaudeProvider:
    """Anthropic Messages API: structured outputs + prompt caching + fallback khi bị từ chối. TỐN TIỀN."""

    name = "claude"

    def __init__(self, model: str, effort: str, ledger: UsageLedger, store: CallStore,
                 api_key: str | None = None, client: object | None = None) -> None:
        self.model = model
        self._effort = effort
        self._ledger = ledger
        self._store = store
        self._context_sent: dict[str, float] = {}  # mã băm ngữ cảnh → lần gửi gần nhất (ước tính trúng cache)
        if client is None:
            import anthropic  # nạp lười: chỉ cần khi bật AI thật

            client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self._client = client

    def estimate_usd(self, request: LlmRequest) -> float:
        sent = self._context_sent.get(_sha(request.context))
        return _estimate(self.model, request, context_warm=sent is not None and time.time() - sent < CACHE_TTL_SECONDS)

    def complete(self, request: LlmRequest) -> LlmResponse:
        import anthropic

        key = request.key(self.model)
        self._ledger.ensure_can_spend(self.estimate_usd(request))  # BudgetExceeded → bên gọi xử lý
        output_config: dict = {"format": {"type": "json_schema", "schema": request.schema}}
        if self.model not in NO_EFFORT_MODELS:
            output_config["effort"] = self._effort
        params = dict(
            model=self.model,
            max_tokens=request.max_tokens,
            system=[
                {"type": "text", "text": request.system},
                {"type": "text", "text": request.context, "cache_control": {"type": "ephemeral"}},
            ],
            messages=[{"role": "user", "content": request.prompt}],
            output_config=output_config,
        )
        try:
            if self.model in FALLBACK_MODELS:
                message = self._client.beta.messages.create(**params, betas=[FALLBACK_BETA], fallbacks="default")
            else:
                message = self._client.messages.create(**params)
        except anthropic.AuthenticationError:
            return self._failed(key, request, "Sai hoặc thiếu API key Anthropic (MAIN_ANTHROPIC_API_KEY).")
        except anthropic.RateLimitError:
            return self._failed(key, request, "Anthropic API báo quá giới hạn tốc độ / hạn mức (429).")
        except anthropic.BadRequestError as exc:
            if "credit balance" in str(exc.message).lower():
                return self._failed(key, request, "Tài khoản Anthropic hết credit — nạp ở Console → Plans & Billing.")
            return self._failed(key, request, f"Anthropic API từ chối yêu cầu (400): {exc.message}")
        except anthropic.APIStatusError as exc:
            return self._failed(key, request, f"Anthropic API lỗi {exc.status_code}.")
        except anthropic.APIConnectionError:
            return self._failed(key, request, "Không kết nối được Anthropic API.")

        self._context_sent[_sha(request.context)] = time.time()
        model = getattr(message, "model", None) or self.model
        u = message.usage
        usage = Usage(
            input_tokens=u.input_tokens or 0,
            output_tokens=u.output_tokens or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        )
        usd = cost_usd(model, usage)
        self._ledger.record(model, usage, usd, request.task, key)
        data, error = None, None
        if message.stop_reason == "refusal":
            error = "Model từ chối trả lời (bộ lọc an toàn)."
        elif message.stop_reason == "max_tokens":
            error = "Câu trả lời bị cắt (hết max_tokens)."
        else:
            text = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                error = "Câu trả lời không phải JSON hợp lệ."
        response = LlmResponse(data=data, model=model, call_id=key, usage=usage, usd=usd,
                               stop_reason=message.stop_reason, error=error)
        self._store.save(key, request, response)
        logger.info("AI %s %s: %d vào (+%d cache đọc, %d cache ghi), %d ra, %.4f USD", request.task, model,
                    usage.input_tokens, usage.cache_read_tokens, usage.cache_write_tokens, usage.output_tokens, usd)
        return response

    def _failed(self, key: str, request: LlmRequest, message: str) -> LlmResponse:
        logger.warning("AI %s lỗi: %s", request.task, message)
        return LlmResponse(data=None, model=self.model, call_id=key, error=message)


__all__ = ["BudgetExceeded", "CallStore", "ClaudeProvider", "FakeProvider", "LlmProvider", "LlmRequest",
           "LlmResponse", "ReplayProvider"]
