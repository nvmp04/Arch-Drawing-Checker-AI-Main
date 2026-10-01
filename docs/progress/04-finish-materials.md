# 04 · Tiêu chí vật liệu — bước 1: bảng vật liệu hoàn thiện + trần ngoài nhà (2026-10-01)

Người dùng chốt hướng D-17 và cách đi: **luật trước, AI sau, từng bước để thử nghiệm và đánh giá.** Bước 1 = 5.1 trần ngoài nhà (ví dụ comment "không có ốp trần cemboard").

## Đã làm

- `ingest/service.py`: chuẩn hóa chữ về Unicode NFC (bản vẽ có dấu tiếng Việt dạng tổ hợp).
- `extraction`: `EntityKind.FINISH` — dòng bảng vật liệu hoàn thiện (mã, mô tả, bề mặt trần / tường / sàn, tiêu đề bảng, gợi ý ngoài nhà); `CALLOUT` — ghi chú về trần (ghép dòng xếp chồng). Hàm `extract_finish_tables`, `extract_callouts`.
- `rules/materials.py`: từ điển vật liệu dùng chung cho câu tiêu chí và chữ trên bản vẽ.
- `rules/checkers.py`: `check_exterior_ceiling` (checker nhóm cho 5.1.1 dòng 0–1, 5.1.2 dòng 0–1) — vật liệu được phép suy ra từ câu tiêu chí / tên rule.
- `rules/plan_table.py`: thêm 5.1.1, 5.1.2.
- Test: bảng + ghi chú tổng hợp, suy vật liệu từ câu tiêu chí, không có gợi ý ngoài nhà thì không `fail`; hồi quy PDF thật (cemboard ↔ comment trang 4, 6, 44). **61 passed.**

## Kết quả

research-log §8: cemboard **không đạt**, bằng chứng trùng cả 3 comment về trần ngoài nhà. Độ phủ 39/223 dòng (17%).

## Còn treo

- **Gỗ nhựa (FC-02) bị đánh không đạt nhưng người kiểm tra không comment** — người dùng chưa xác định được comment có đầy đủ không, sẽ cập nhật sau (Q-13).
- Chưa chạy lại luồng thật FE → BE → MAIN cho đợt này (đã kiểm bằng test hồi quy trên cùng PDF).
- Bước 2: mở rộng khuôn sang các tiêu chí vật liệu khác (tường, chân tường 5.2, ban công 5.3…), đo trên 29 comment.
