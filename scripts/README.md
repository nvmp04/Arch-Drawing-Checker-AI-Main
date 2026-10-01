# scripts/

Script tiện ích cho phát triển. Chạy từ thư mục repo bằng `python`.

## Xem kết quả ingest

**Luồng thật (chính):** bật BE (4000) + MAIN (8000), tạo hồ sơ ở FE hoặc bằng `curl` (hợp đồng BE §7). Mỗi job MAIN nhận sẽ ghi một viewer; mở **http://localhost:8000/debug/inspect/** để xem danh sách lần chạy (trạng thái, số trang, chữ, nét, thời gian) và mở viewer từng job. Code: `src/drawing_checker/features/ingest/inspector.py` (D-15).

**Thử nhanh một PDF cục bộ (không qua BE):**

```bash
python scripts/inspect_ingest.py "D:/Downloads/tieuchuan/PN2.DN-Ban ve mau demo test AI.pdf"
python scripts/inspect_ingest.py bản_vẽ.pdf --pages 4,12,37-39 --dpi 150 --open
```

Ghi vào cùng thư mục `data/inspect/` (không commit), xuất hiện trong danh sách với nguồn `script`. Mở trực tiếp file `index.html` cũng được, không cần server.

Viewer:
- Danh sách trang bên trái (tiêu đề đoán tạm, số chữ / nét / layer). `index.html#p=39` mở thẳng trang 39.
- Canvas: ảnh nền (chỉnh độ mờ) + khung chữ + nét vẽ + vùng tô, màu theo layer CAD hoặc một màu. Lăn chuột zoom, kéo di chuyển, `F` / nhấp đúp vừa khung, `←` `→` đổi trang.
- Rê chuột lên chữ: nội dung, font, cỡ, góc xoay, layer, tọa độ (point).
- Tìm chữ (Enter nhảy tới kết quả kế tiếp); danh sách layer CAD: bật/tắt, lọc, bấm tên để solo.
- Thống kê trang: số khối chữ, ký tự, nét, vùng tô, thời gian trích.

Ảnh nền chỉ để người đối chiếu khi debug; MAIN không trả ảnh cho BE (D-07). Bộ mẫu 48 trang: ~100 s, ~99 MB mỗi lần chạy — nhớ dọn `data/inspect/` định kỳ.
