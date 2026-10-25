# 06 · Gỡ checker ngữ nghĩa viết cứng theo file tiêu chí (2026-10-02)

Quyết định: D-18. Chi tiết sự cố: research-log §11.

## Chuyện gì đã xảy ra

Người dùng sửa một câu tiêu chí (4.2.1 dòng 0) thành nghĩa ngược lại để thử; checker cấu tạo sàn vẫn kết luận như cũ. Truy ra: `rules/plan_table.py` là bảng **viết tay theo mã rule của bộ 4 SAO** (không sinh ra khi chạy, không phải thuật toán); các checker đợt 2–3 để toàn bộ cách hiểu câu tiêu chí trong bảng đó. Người dùng: bộ tiêu chí thay đổi theo file nạp vào → sai lầm nghiêm trọng; yêu cầu gỡ ngay.

## Đã gỡ

- `rules/checkers.py`: `check_exterior_ceiling`, `check_floor_assembly`, `check_forbidden_topic`, `check_opening_glass` và mọi hằng số / hàm phụ của chúng.
- `rules/materials.py` (xóa file).
- `rules/plan_table.py`: các dòng 5.1.1, 5.1.2, 4.2.1, 4.2.4, 4.2.5, 4.5.3, 4.5.5, 4.4.1, 1.4; các hàm `_ceiling`, `_floor`, `_text`, `_min`. Thêm cảnh báo ở đầu file.
- `rules/interpreter.py`: bỏ khóa "<khóa>|<tên rule>". `rules/schemas.py`: `CheckPlan.params` về kiểu phẳng.
- `extraction/service.py`: `extract_callouts`, `extract_topic_mentions`, gợi ý "ngoài nhà" (`EXTERIOR_HINTS`).
- Test của các checker trên. Thêm `test_semantic_lines_are_unsupported_not_hardcoded` (các dòng đó phải là "chưa hỗ trợ").

## Giữ lại (không phụ thuộc file tiêu chí)

- Ingest: NFC, giải mã VNI, nối dòng chữ bị tách.
- Đọc bảng vật liệu hoàn thiện, bảng thống kê cấu tạo sàn, độ dày kính bảng cửa — chưa có checker dùng.
- 6 checker tiêu chí số của D-16 (cote, chiều cao tầng, bậc thang, danh mục cửa).

## Trạng thái sau khi gỡ

Độ phủ 35/223 dòng (16%) · 64 test đạt · chưa chạy lại luồng thật FE → BE → MAIN.

## Còn treo — cần người dùng quyết

1. **6 checker tiêu chí số còn lại vẫn nối theo mã rule 4 SAO** ("rule 3.4 = chiều cao bậc"…). Ngưỡng đọc từ rule nhưng "đo cái gì" là viết cứng. Gỡ nốt, hay giữ tạm tới khi có bước diễn giải?
2. **Bước diễn giải luật (Q-07)** — câu tiêu chí bất kỳ → kế hoạch kiểm tra: AI local · AI đề xuất + người duyệt · người khai báo. Cần dữ liệu (các sheet khác của file Excel?).
