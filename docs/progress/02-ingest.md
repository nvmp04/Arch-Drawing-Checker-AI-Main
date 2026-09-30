# 02 · Ingest + công cụ xem (2026-09-28)

Người dùng chốt: tạm thời chỉ đánh giá ingest tại lõi (chưa trả gì thêm về BE), xem bằng **viewer HTML tĩnh**, phạm vi **chữ + nét vẽ**.

## Đã làm

- `features/ingest/service.py`: `open` (chữ mọi trang), `load_text`, `load_paths` (nét vẽ một trang), `count_pages`; hàm công khai `extract_texts`, `extract_paths`.
  - Chữ từ `get_texttrace` (có layer), lọc ký tự ngoài khổ trang, bỏ chữ ẩn, chuẩn hóa NBSP, góc xoay theo trang hiển thị.
  - Nét từ `get_cdrawings`, tách drawing thành các nét liền, Bézier → 8 đoạn, `re`/`qu` → đa giác kín, màu hex, layer.
- `features/ingest/schemas.py`: thêm `layer`; `VectorPath` → dataclass (hiệu năng). Quyết định: D-14.
- `scripts/inspect_ingest.py` + `scripts/inspect_ingest_viewer.html`: viewer (xem `scripts/README.md`).
- `tests/test_ingest.py`: PDF tổng hợp có OCG, Bézier, rect tô, trang xoay 90°, lỗi.

## Kiểm chứng

- `pytest`: 25 passed.
- Chạy toàn bộ bộ mẫu PN2 (48 trang): 95 s; mở viewer bằng Edge headless — trang 1 và trang 39 (317k nét) hiển thị đúng.
- Test bắt được lỗi thật: dấu góc xoay chữ trên trang có /Rotate (đã sửa); NBSP trong chữ (đã chuẩn hóa).

## Phát hiện (research-log §6)

- PDF mang 378 layer CAD trên cả chữ và nét — `A-dim`, `A-WALL-*`, `A-Door`, `A-Window`… → cơ hội lớn cho `extraction`/`geometry`.
- Trang 1 là ảnh nhúng (bảng danh mục không đọc được).

## Còn treo

- Người dùng đánh giá bằng viewer → quyết định bước tiếp (sheets / extraction).
- Chưa nối ingest vào pipeline `analyses` (callback vẫn chỉ đếm trang).
- Q-01 (tọa độ trả BE) vẫn mở.

## Bổ sung — ingest trong luồng thật (D-15)

Người dùng chỉnh hướng: phải test **luồng thực thi** (BE → MAIN), không ingest sẵn ngoài hệ thống.
- `IngestService.reader()` → `PageReader` (giữ PDF mở, `read(n)` kèm thời gian, `render_jpeg` cho debug).
- `features/ingest/inspector.py`: ghi viewer theo lần chạy + trang danh sách; template chuyển vào `features/ingest/inspector_viewer.html`. Script dùng lại module này.
- `analyses`: bước `extract` ingest từng trang trong thread, callback % theo trang, ghi viewer cả khi lỗi (meta có `error`).
- `app`: mount `/debug/inspect/` (cờ `MAIN_INSPECT_ENABLED`); bật log INFO cho package `drawing_checker`.
- Kiểm chứng với BE thật: upload bộ mẫu 48 trang (shophouse, facade + stair-ramp) → tiến độ BE tăng 15% → 83% theo trang → `completed`, `pageCount: 48`, ~105 s; viewer phục vụ qua MAIN (200), `/v1/analyses` vẫn 401 nếu thiếu token. `pytest`: 26 passed.
- Quan sát thêm: keyplan nằm trên layer riêng (`xf-keyplan-a|A-keyplan`) — hữu ích cho `sheets` tách khung nhìn.
