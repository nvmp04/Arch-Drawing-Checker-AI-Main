# Lộ trình MAIN

## Giai đoạn 0 — Khung xương ✅ (2026-09-27)

Cấu trúc feature-based, hợp đồng Pydantic, route stub (501), tài liệu ngữ cảnh đầy đủ, dữ liệu mẫu + ground truth trích tự động. Xem `progress/00-skeleton.md`.

## Giai đoạn 0.5 — Bắt tay BE v0 ✅ (2026-09-28)

Nhận việc, tải PDF, đếm trang, callback `extract` → `aggregate`, hủy. Kiểm chứng với BE thật. Xem `progress/01-handshake.md`. Bước 7 của Giai đoạn 1 (phần khung dispatch/callback) coi như đã có; còn gửi findings thật.

## Giai đoạn 1 — Pipeline không cần train (chạy được trên bộ mẫu)

Mục tiêu: chạy hết bộ PDF mẫu, ra kết quả theo requirementLine có bằng chứng, đo độ trùng với comment người kiểm tra.

1. ✅ `ingest`: đọc PDF → trang, khối chữ + tọa độ + layer, nét vẽ + layer (2026-09-28, `progress/02-ingest.md`). Quy đổi tọa độ Q-01 để ở `findings`. Công cụ xem: `scripts/inspect_ingest.py`.
2. `sheets`: phân loại trang theo tiêu đề; tách khung nhìn + tỉ lệ.
3. ✅ (đợt đầu) `rules`: phân tích ngưỡng + so sánh + bảng khai báo rule → checker (2026-09-30, `progress/03-rule-engine.md`). Còn: mở rộng checker theo độ phủ đo được.
4. ◐ `extraction` heuristic: ✅ cao độ, vế thang, bảng cửa, bảng vật liệu hoàn thiện, ghi chú trần (2026-10-01, `progress/04-finish-materials.md`) · ☐ kích thước (đường kích thước ↔ số), ghi chú vật liệu tường / sàn, vị trí mã vật liệu trên mặt bằng.
5. ✅ `rules.evaluator`: so ngưỡng.
6. ◐ Tiêu chí chữ / vật liệu theo D-17 (luật trước, AI sau): ✅ bước 1 — 5.1 trần ngoài nhà (từ điển vật liệu dùng chung cho tiêu chí và bản vẽ) · ☐ bước 2 — mở rộng sang tiêu chí vật liệu khác, đo trên 29 comment · ☐ bước 3 — embedding tìm ứng viên ở chỗ luật bỏ sót.
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
