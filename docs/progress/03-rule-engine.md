# 03 · Rule engine không AI — đợt thử (2026-09-30)

Người dùng chốt: rule mock nạp ở MAIN · kết quả chỉ xem ở viewer · phạm vi = các họ đã chứng minh. Quyết định: D-16.

## Đã làm

- `rules/interpreter.py`: `parse_value` ("150mm", "3.3m", "1.2m - 2.6m", "2.8 x 5.6m", "18%", "17, 18, 21…"); `interpret` theo bảng.
- `rules/plan_table.py`: bảng rule → checker (1.8*, 2.1.1*–2.1.4, 3.2, 3.2*, 3.4, 3.5, 1.4.1–1.4.5).
- `rules/evaluator.py`: `compare`, `at_threshold`, `describe` — lõi thuần.
- `rules/checkers.py`: chênh cote tầng 1 – vỉa hè, chiều cao tầng, bậc cao / rộng / số bậc (khớp chéo với chiều cao tầng), danh mục kích thước cửa.
- `rules/service.py`: lọc rule (loại nhà + nhóm), chạy checker, báo cáo độ phủ, `load_mock_rules`.
- `extraction/service.py`: cao độ (nhãn + số), vế thang ("N BẬC x h=tổng"), bảng thống kê cửa.
- `findings/service.py`: `finalize` (không `approved`; `fail` dưới 0.8 → `warning`).
- `analyses`: trích thực thể theo trang trong luồng job → rule engine → `checks.js` cho viewer. Cấu hình `MAIN_MOCK_RULESET`.
- Viewer: tab "Kiểm tra" (tóm tắt, độ phủ, lọc theo trạng thái, thẻ kết quả, bấm "tr.N" → nhảy tới trang + tô bằng chứng); `#tab=checks`; trang danh sách lần chạy có cột "Kiểm tra".
- Test: `test_rules_engine.py` (lõi + trang tổng hợp theo bố cục PN2), `test_sample_pdf.py` (hồi quy trên PDF thật, tự bỏ qua nếu không có file), job ghi `checks.js`. **57 passed.**

## Kiểm chứng

Luồng thật BE → MAIN (shophouse, 5 nhóm): hồ sơ `completed` ~100 s; viewer phục vụ qua MAIN hiển thị đúng. Kết quả: research-log §7.

## Còn treo

- 84% dòng tiêu chí chưa có checker — phần lớn là tiêu chí chữ / vật liệu (cần `semantic`) và hình học.
- Gửi findings về BE: chờ Q-09 (severity), L-02 (checkType), L-03 (lineIndex + nhiều bằng chứng), Q-01 (tọa độ).
- Hợp đồng BE ghi `npm run start:dev`, thực tế `npm run dev`.
