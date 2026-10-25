# 05 · Checker chắc chắn đúng — cấu tạo sàn, chống mối, kính cửa (2026-10-02)

> ⚠ **ĐÃ GỠ ngày 2026-10-02 (D-18, `progress/06-remove-hardcoded-semantic.md`):** ba checker cấu tạo sàn / chống mối / kính cửa, phần trích ghi chú chủ đề. Lý do: cách hiểu tiêu chí viết cứng theo file 4 SAO. Phần đọc bảng trên bản vẽ và sửa ingest vẫn còn. Nội dung dưới đây là nhật ký lúc làm, không còn mô tả đúng hiện trạng.

Người dùng chốt: bước 2 chưa dùng PhoBERT (chưa có dữ liệu fine-tune); **tập trung hoàn toàn vào checker chắc chắn đúng** (dữ liệu từ bảng / câu tự đủ nghĩa); cần một file mô tả từng checker.

## Đã làm

- `docs/checkers.md` (mới): công năng + cách hiện thực từng checker, danh sách dự kiến. Quy ước cập nhật ghi ở `AGENTS.md` §6.
- Ingest (research-log §9): giải mã font VNI (`ingest/vni.py`), nối dòng chữ bị tách thành nhiều lượt vẽ.
- `extraction`: `extract_floor_assemblies` (bảng thống kê cấu tạo sàn → mỗi lớp một `TABLE_ROW`), `extract_topic_mentions` (ghi chú theo chủ đề, hiện có "chống mối"), độ dày kính trong bảng cửa (`glass_mm`).
- `rules/checkers.py`: `check_floor_assembly` (kiểm con: text / base / number / rebar / absent), `check_forbidden_topic`, `check_opening_glass`.
- `rules/plan_table.py`: 4.2.1 (sàn tầng 1), 4.2.4, 4.2.5 (mái bằng), 4.5.3, 4.5.5 (mái bằng), 4.4.1, 1.4. Khóa "<khóa>|<tên rule>" cho biến thể không mã khác nội dung. `CheckPlan.params` cho phép giá trị lồng.
- Test: 70 passed (bảng tổng hợp + hồi quy PDF thật).

## Kết quả

research-log §10. Độ phủ 55/223 dòng (25%). Khớp thêm 3 comment (sàn BTCT tầng 1, sàn mái, chống mối).

## Còn treo

- Chưa chạy lại luồng thật FE → BE → MAIN cho các đợt 2–3 (mới kiểm bằng test trên PDF mẫu).
- #11 vật liệu tường / chân tường: chờ người dùng xác nhận 1.5 ↔ 5.2.1 (porcelain hay sơn nước).
- #12 vật liệu sàn ngoài nhà; phần còn lại của bảng cấu tạo sàn (sảnh hiên, cầu thang, bồn hoa).
- Rủi ro nối nhầm chữ ở ingest (hai số kích thước sát nhau) — người dùng: tạm bỏ qua.
- Q-13 (comment người kiểm tra có đầy đủ không) — chờ người dùng.
