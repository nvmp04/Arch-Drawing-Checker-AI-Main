"""Tải PDF từ URL có chữ ký do BE cấp về thư mục làm việc (hợp đồng BE v0 ②)."""

from pathlib import Path

import httpx

# Thông báo tiếng Việt hiển thị thẳng cho người dùng (errorMessage của callback failed).
_ERROR_MESSAGES = {
    "SIGNED_URL_EXPIRED": "Liên kết tải bản vẽ đã hết hạn. Vui lòng chạy lại phân tích.",
    "SIGNED_URL_INVALID": "Liên kết tải bản vẽ không hợp lệ. Vui lòng chạy lại phân tích.",
    "REVIEW_NOT_FOUND": "Không tìm thấy hồ sơ trên máy chủ.",
}


class PdfFetchError(Exception):
    """Không tải được PDF. `str(exc)` là thông báo tiếng Việt cho người dùng."""


class PdfFetcher:
    def __init__(self, work_dir: Path, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._work_dir = work_dir
        self._transport = transport

    async def fetch(self, pdf_url: str, job_id: str) -> Path:
        """Tải theo luồng (file ~20MB, có thể tới 100MB), kiểm magic bytes `%PDF-`.

        `pdf_url` dùng nguyên văn — chữ ký nằm trong query, không gửi header xác thực.
        """
        self._work_dir.mkdir(parents=True, exist_ok=True)
        target = self._work_dir / f"{job_id}.pdf"
        timeout = httpx.Timeout(30.0, read=120.0)
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=timeout) as client:
                async with client.stream("GET", pdf_url) as response:
                    if response.status_code != 200:
                        await response.aread()
                        raise PdfFetchError(_describe_error(response))
                    with target.open("wb") as file:
                        async for chunk in response.aiter_bytes():
                            file.write(chunk)
        except httpx.TransportError as exc:
            target.unlink(missing_ok=True)
            raise PdfFetchError("Không kết nối được máy chủ để tải bản vẽ.") from exc
        except BaseException:
            target.unlink(missing_ok=True)
            raise

        with target.open("rb") as file:
            magic = file.read(5)
        if magic != b"%PDF-":
            target.unlink(missing_ok=True)
            raise PdfFetchError("File tải về không phải PDF.")
        return target


def _describe_error(response: httpx.Response) -> str:
    try:
        code = response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        code = None
    return _ERROR_MESSAGES.get(code, f"Không tải được bản vẽ (HTTP {response.status_code}).")
