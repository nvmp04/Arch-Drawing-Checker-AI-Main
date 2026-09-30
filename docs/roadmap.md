# Lộ trình MAIN

## Giai đoạn 0 — Khung xương ✅ (2026-09-27)

Cấu trúc feature-based, hợp đồng Pydantic, route stub (501), tài liệu ngữ cảnh đầy đủ, dữ liệu mẫu + ground truth trích tự động. Xem `progress/00-skeleton.md`.

## Giai đoạn 0.5 — Bắt tay BE v0 ✅ (2026-09-28)

Nhận việc, tải PDF, đếm trang, callback `extract` → `aggregate`, hủy. Kiểm chứng với BE thật. Xem `progress/01-handshake.md`. Bước 7 của Giai đoạn 1 (phần khung dispatch/callback) coi như đã có; còn gửi findings thật.

## Giai đoạn 1 — Pipeline không cần train (chạy được trên bộ mẫu)

Mục tiêu: chạy hết bộ PDF mẫu, ra kết quả theo requirementLine có bằng chứng, đo độ trùng với comment người kiểm tra.

1. ✅ `ingest`: đọc PDF → trang, khối chữ + tọa độ + layer, nét vẽ + layer (2026-09-28, `progress/02-ingest.md`). Quy đổi tọa độ Q-01 để ở `findings`. Công cụ xem: `scripts/inspect_ingest.py`.
2. `sheets`: phân loại trang theo tiêu đề; tách khung nhìn + tỉ lệ.
3. `rules.interpreter` bản luật: tách số/đơn vị/toán tử từ `value` và `requirementLines`.
4. `extraction` heuristic: cao độ, thang, bảng cửa, kích thước, ghi chú.
5. `rules.evaluator`: so ngưỡng.
6. `semantic` bản từ khóa + so số cho tiêu chí dạng chữ.
7. `findings` + `analyses`: dispatch → chạy nền → callback BE theo 5 bước.
8. `benchmark`: làm sạch `samples/ground-truth/…json`, đo precision / recall.

Điều kiện bắt đầu: người dùng duyệt hướng; chốt tối thiểu Q-01 (tọa độ) và L-01 (BE gửi nội dung rule).

## Giai đoạn 2 — Train (khi có thêm bộ bản vẽ đã kiểm tra — Q-06)

- Công cụ xuất / nhập nhãn: kết quả trích xuất → người sửa → dữ liệu train.
- Model trích xuất trên đồ thị nét vẽ (gắn số ↔ đối tượng, tách khung nhìn, nhận dạng phòng/ký hiệu).
- Model tiếng Việt cho so khớp ghi chú ↔ tiêu chí (embedding + phân loại).
- Model diễn giải requirementLine (Q-07) + hiện thực `checkType`.

## Giai đoạn 3 — Mở rộng

DXF/DWG nếu có (Q-05), hiệu năng, đóng gói Docker.
