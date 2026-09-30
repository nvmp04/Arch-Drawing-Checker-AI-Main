"""Gọi webhook BE: POST {callbackUrl} với header x-internal-token (hợp đồng BE v0 ③)."""

import asyncio
import logging

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

RETRY_DELAYS = (0.5, 1.0, 2.0)  # 5xx / lỗi mạng: thử lại tối đa 3 lần


class CallbackRejected(Exception):
    """BE từ chối vĩnh viễn (400 sai hợp đồng, 401 sai token) — lỗi phía MAIN, không retry."""


class JobAborted(Exception):
    """BE báo job không còn hiệu lực (404 hồ sơ mất, 409 người dùng đã chạy lại / hủy) — dừng job."""


class BackendClient:
    def __init__(self, callback_token: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._token = callback_token
        self._transport = transport

    async def send_callback(self, callback_url: str, payload: BaseModel) -> None:
        """Gửi tiến độ / kết quả. BE idempotent theo (reviewId, stage) nên retry an toàn.

        BE không nhận trường thừa → serialize by_alias, bỏ trường None.
        """
        body = payload.model_dump(mode="json", by_alias=True, exclude_none=True)
        headers = {"x-internal-token": self._token}
        async with httpx.AsyncClient(transport=self._transport, timeout=10.0) as client:
            for attempt, delay in enumerate((*RETRY_DELAYS, None)):
                try:
                    response = await client.post(callback_url, json=body, headers=headers)
                except httpx.TransportError as exc:
                    error: str = repr(exc)
                else:
                    code = response.status_code
                    if code < 300:
                        return
                    if code in (404, 409):
                        raise JobAborted(f"callback {code}: {response.text}")
                    if code < 500:
                        raise CallbackRejected(f"callback {code}: {response.text}")
                    error = f"HTTP {code}"
                if delay is None:
                    raise ConnectionError(f"callback thất bại sau {attempt + 1} lần: {error}")
                logger.warning("Callback lỗi (%s), thử lại sau %.1fs", error, delay)
                await asyncio.sleep(delay)
