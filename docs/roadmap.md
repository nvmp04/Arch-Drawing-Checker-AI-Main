# Lộ trình MAIN

## Giai đoạn 0 — Khung xương ✅ (2026-09-27)

Cấu trúc feature-based, hợp đồng Pydantic, route stub (501), tài liệu ngữ cảnh đầy đủ, dữ liệu mẫu + ground truth trích tự động. Xem `progress/00-skeleton.md`.

## Giai đoạn 0.5 — Bắt tay BE v0 ✅ (2026-09-28)

Nhận việc, tải PDF, đếm trang, callback `extract` → `aggregate`, hủy. Kiểm chứng với BE thật. Xem `progress/01-handshake.md`. Bước 7 của Giai đoạn 1 (phần khung dispatch/callback) coi như đã có; còn gửi findings thật.

## Giai đoạn 1 — Pipeline không cần train (chạy được trên bộ mẫu)

Mục tiêu: chạy hết bộ PDF mẫu, ra kết quả theo requirementLine có bằng chứng, đo độ trùng với comment người kiểm tra.

1. ✅ `ingest`: đọc PDF → trang, khối chữ + tọa độ + layer, nét vẽ + layer (2026-09-28, `progress/02-ingest.md`). Quy đổi tọa độ Q-01 để ở `findings`. Công cụ xem: `scripts/inspect_ingest.py`.
2. ✅ **Giai đoạn A — đọc cấu trúc hồ sơ** (2026-10-05, `progress/07-phase-a-dossier.md`, D-19): khung tên 48/48 trang (tên, tỉ lệ, số hiệu), tiêu đề hình / bảng + tỉ lệ, bảng viết tắt trang 2 + mở rộng chữ, đặc điểm hồ sơ; tab "Hồ sơ" ở viewer. ☐ tách vùng của từng hình (hình học), khung tên nằm ngang.
3. ◐ `rules`: ✅ phân tích ngưỡng + so sánh (2026-09-30, `progress/03-rule-engine.md`) · ⚠ bảng rule → checker (`plan_table.py`) viết tay theo mã rule bộ 4 SAO, không tổng quát (D-18) · ☐ **bước diễn giải luật** (Q-07): câu tiêu chí → kế hoạch kiểm tra — điều kiện để mở rộng checker.
4. ◐ `extraction` heuristic: ✅ cao độ, vế thang, bảng cửa (+ kính), bảng vật liệu hoàn thiện, bảng cấu tạo sàn (`progress/04`, `05`; chưa có checker dùng ba mục sau) · ☐ kích thước (đường kích thước ↔ số), ghi chú vật liệu tường / sàn, vị trí mã vật liệu trên mặt bằng.
5. ✅ `rules.evaluator`: so ngưỡng.
6a. ✅ Lưới bảng từ nét vẽ → bản tóm tắt gửi AI đọc bảng theo hàng / ô (2026-10-19, `progress/10-table-grid.md`). ☐ đo tác động lên độ chính xác AI · ☐ đường dẫn ghi chú (leader).
6. ◐ Tiêu chí chữ / vật liệu / cấu tạo: **2026-10-09 nối Claude API** (D-22, `progress/08-claude-integration.md`) — AI diễn giải + phán đoán mỗi dòng rule engine chưa hỗ trợ, hậu kiểm trích dẫn bằng code, mặc định tắt; ☐ người dùng chạy đo lần đầu (`scripts/run_ai_eval.py --live`) · ☐ lưới bảng + đường dẫn ghi chú từ nét vẽ (`drawing-knowledge.md`) để nâng độ chính xác. Trước đó: **dừng** cho tới khi có bước diễn giải luật (Q-07, D-18). Bốn checker viết cứng (trần ngoài nhà, cấu tạo sàn, chống mối, kính cửa) đã làm rồi **gỡ** ngày 2026-10-02 (`progress/06-remove-hardcoded-semantic.md`). Không làm lại bằng bảng / từ điển viết tay.
7. ✅ `findings` + `analyses`: dispatch → chạy nền → callback BE; **findings v1** gửi mọi kết quả theo dòng tiêu chí, BE lưu, FE hiện (2026-10-19, D-23, `progress/09-findings-v1.md`). ☐ thao tác duyệt lưu BE (integration-contract §5.4).
8. `benchmark`: làm sạch `samples/ground-truth/…json`, đo precision / recall.

Điều kiện bắt đầu: người dùng duyệt hướng; chốt tối thiểu Q-01 (tọa độ) và L-01 (BE gửi nội dung rule).

### Thứ tự tiếp theo (D-19)

- ☐ **Giai đoạn B — định vị + khớp tên:** mỗi dòng tiêu chí → trang / hình / bảng liên quan; khớp tên tiêu chí ↔ bản vẽ (chữ đã mở rộng viết tắt). Embedding có sẵn, không train. Chờ duyệt thư viện (Q-14).
- ☐ **Giai đoạn C — diễn giải:** cổng áp dụng + chọn mẫu M1–M7 + thông số (`check-templates.md`), có ngưỡng tin cậy. Model nhỏ (fine-tune). Làm khi A, B ổn.
- ⏸ Bước 3 — gắn mã / ghi chú vào vùng trên mặt bằng: hoãn (người dùng 2026-10-05).

## Giai đoạn 2 — Train (khi có thêm bộ bản vẽ đã kiểm tra — Q-06)

- Công cụ xuất / nhập nhãn: kết quả trích xuất → người sửa → dữ liệu train.
- Model trích xuất trên đồ thị nét vẽ (gắn số ↔ đối tượng, tách khung nhìn, nhận dạng phòng/ký hiệu).
- Model tiếng Việt cho so khớp ghi chú ↔ tiêu chí (embedding + phân loại).
- Model diễn giải requirementLine (Q-07) + hiện thực `checkType`.

## Giai đoạn 3 — Mở rộng

DXF/DWG nếu có (Q-05), hiệu năng, đóng gói Docker.
