# 01 · Bắt tay BE ↔ MAIN v0 (2026-09-28)

Theo hợp đồng `arch-drawing-checker-backend/docs/contracts/be-main.md` (v0). Quyết định: `decisions.md` D-13.

## Đã làm

- Môi trường: venv hết bị chặn → `.venv` là cách chạy chính (`AGENTS.md` §5). *(Từ 2026-09-30: bỏ venv, chạy bằng Python hệ thống.)*
- `common/security.py`: kiểm `Authorization: Bearer <MAIN_SERVICE_TOKEN>` (so sánh hằng thời gian), sai → 401.
- `infrastructure/backend_client.py`: gửi callback với `x-internal-token`, body by_alias + bỏ None; retry 5xx/lỗi mạng (0.5/1/2 s); `JobAborted` cho 404/409, `CallbackRejected` cho 400/401.
- `infrastructure/pdf_fetcher.py`: tải theo luồng, kiểm `%PDF-`, ánh xạ lỗi BE (`SIGNED_URL_EXPIRED`…) sang thông báo tiếng Việt.
- `infrastructure/job_runner.py`: asyncio task in-process, hủy được.
- `features/ingest/service.py`: `count_pages` (mở từ bytes — PyMuPDF giữ handle file khi mở lỗi, Windows không xóa được file tạm).
- `features/analyses/`: dispatch → 202 ngay; pipeline v0 `extract` running 5 → completed 30 + `pageCount` → `aggregate` completed 100 `findings: []`; lỗi → `failed` + `errorMessage`; GET trạng thái; DELETE hủy (204/404).
- `tests/test_handshake.py`: BE giả lập bằng `httpx.MockTransport` — luồng chuẩn, PDF hết hạn/không tìm thấy, PDF mã hóa/hỏng/không phải PDF, retry 5xx, dừng khi 409/404/400/401, xác thực, 422, hủy.

## Kiểm chứng

- `pytest`: 21 passed.
- Với BE thật (cổng 4000) theo §7 hợp đồng: upload `D:\Downloads\PN2-DN-01.pdf` (20MB) → MAIN 202 → hồ sơ `completed`, 100%, `pageCount: 48`, ~0.8 s.

## Còn treo

- Hợp đồng v1: findings thật + nội dung rule (L-01…L-04, Q-09).
- Job lưu trong bộ nhớ (mất khi khởi động lại MAIN); chưa giới hạn số job song song.
- Nhãn bước trong BE vẫn ghi "OCR", "VLM" (L-05).
