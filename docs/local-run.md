# Chạy cả hệ thống trên máy để thử tính năng (FE + BE + MAIN)

> Dùng trong lúc chưa có máy chủ (Oracle). Mặc định MAIN **không gọi AI** (`MAIN_AI_PROVIDER=off`) — chỉ đọc bản vẽ + rule engine.

## Mở 3 cửa sổ terminal

| # | Thư mục | Lệnh | Địa chỉ |
|---|---|---|---|
| 1 | `D:\Downloads\arch-drawing-checker-main` | `python -m uvicorn drawing_checker.app:app --port 8000` | MAIN: http://localhost:8000/health · viewer debug: http://localhost:8000/debug/inspect/ |
| 2 | `D:\Downloads\arch-drawing-checker-backend` | `npm run dev` | BE: http://localhost:4000/api/v1/health · Swagger: http://localhost:4000/docs |
| 3 | `D:\Downloads\arch-drawing-checker-ai` | `npm run dev` | **Web: http://localhost:3000/demo/reviews** |

Thứ tự không bắt buộc, nhưng MAIN phải chạy trước khi tạo hồ sơ (nếu không, hồ sơ chuyển "lỗi" — bấm **Chạy lại** sau khi bật MAIN).

Cấu hình đã khớp sẵn: token BE ↔ MAIN dùng giá trị mặc định ở cả hai bên (MAIN không cần `.env`); FE trỏ `http://localhost:4000/api/v1` (`.env.local`).

## Dữ liệu nằm ở đâu (trên máy)

- Hồ sơ: CSDL nhúng `arch-drawing-checker-backend/.data/pglite` (không phải Neon — Neon chỉ dùng trên máy chủ, `.env.production`).
- PDF: `arch-drawing-checker-backend/storage/review-pdfs/demo/sha256/<mã băm>.pdf`.
- Kết quả đọc bản vẽ của MAIN: `arch-drawing-checker-main/data/inspect/<job>/`.
- Xóa sạch để thử lại từ đầu: tắt BE rồi xóa `.data/` và `storage/` trong repo backend.
- **BE báo `DrizzleQueryError: Failed query: CREATE SCHEMA IF NOT EXISTS "drizzle"` (hoặc PGlite `Aborted()`) khi khởi động** = CSDL nhúng `.data/pglite` bị hỏng do BE bị tắt đột ngột lúc đang ghi (gặp 2026-10-19). Sửa: tắt BE, đổi tên `.data/pglite` (vd. `.data/pglite-broken-<ngày>`), chạy lại BE → tạo CSDL mới (mất danh sách hồ sơ thử; PDF trong `storage/` vẫn còn, tải lại là xong). Tắt BE bằng **Ctrl+C một lần rồi chờ** thoát hẳn, tránh đóng cửa sổ terminal khi BE đang xử lý.

## Kịch bản thử

1. **Tạo hồ sơ**: `/demo/reviews` → "Thẩm định mới" → chọn PDF (vd. `D:\Downloads\tieuchuan\PN2.DN-Ban ve mau demo test AI.pdf`), điền tên, phân khu, bộ tiêu chuẩn, loại nhà, nhóm → Tải lên.
2. **Tiến độ thật**: trang xử lý cập nhật mỗi 1,5 giây theo MAIN (PN2 ~40–100 giây) → "Xem kết quả".
3. **Xem bản vẽ + kết quả**: trang hồ sơ hiện đúng PDF vừa tải lên và **kết quả kiểm tra theo từng dòng tiêu chí** (findings v1): khung khoanh trên bản vẽ, lý do. AI tắt thì phần lớn dòng là "Không xác định" (chưa hỗ trợ). Chi tiết kỹ thuật vẫn xem ở viewer debug của MAIN.
4. **File trùng**: tải lại **cùng file** (đổi tên file cũng được) → hộp thoại "File trùng với hồ sơ đã có" → thử **Mở hồ sơ** và **Kiểm tra lại**.
5. **Danh sách**: `/demo/reviews` hiện các hồ sơ thật, mới nhất trước.
6. **Lỗi + chạy lại**: tắt MAIN, tạo hồ sơ với một PDF khác → trang xử lý báo lỗi → bật MAIN → **Chạy lại**.
7. **Hạn mức** (tùy chọn): đặt `MAX_REVIEWS_PER_WORKSPACE=1` trong `.env` của backend, khởi động lại BE, tạo hồ sơ thứ hai → báo hết hạn mức.

## Giới hạn hiện tại

- Nút Xác nhận / Ghi chú chỉ lưu trên trang (tải lại là mất) — chưa lưu BE (giai đoạn 3).
- Chưa có đăng nhập (sẽ có trước khi đưa lên máy chủ).
- Phân khu / bộ tiêu chuẩn ở form vẫn là danh mục demo (giai đoạn 2).

## Bật AI (Claude) cho luồng web — TỐN TIỀN (D-22)

Trong `.env` của MAIN: `MAIN_AI_PROVIDER=claude`, `MAIN_ANTHROPIC_API_KEY=...`, tùy chọn `MAIN_AI_MODEL` (mặc định `claude-opus-5-5`). Khởi động lại MAIN. Mỗi lần tạo hồ sơ / **Kiểm tra lại** là một lần gọi AI thật, tối đa `MAIN_AI_MAX_USD_PER_RUN` (1 USD); cả tháng tối đa `MAIN_AI_MONTHLY_BUDGET_USD` (5 USD). Kết quả AI xem ở viewer debug, tab "Kiểm tra" (web chưa hiện — findings v1). Tắt lại: `MAIN_AI_PROVIDER=off`.
Thử AI ngoài web (khuyên dùng trước): `scripts/run_ai_eval.py` — xem `docs/progress/08-claude-integration.md`.
