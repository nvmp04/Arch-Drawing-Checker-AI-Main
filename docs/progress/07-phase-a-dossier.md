# 07 · Giai đoạn A — đọc cấu trúc hồ sơ (2026-10-05)

Quyết định: D-19. Chi tiết kỹ thuật và kết quả: research-log §12. Không AI, không phụ thuộc bộ tiêu chí (D-18).

## Đã làm

- `ingest`: giữ chữ ngoài vùng hiển thị thành `DrawingPage.margin_texts` (`extract_all_texts`) — khung tên của PN2 nằm ở đó.
- `sheets` (điền stub): `SheetService.analyze` (khung tên + tiêu đề hình / bảng), `abbreviations` (bảng viết tắt), `build_index` (mục lục + đặc điểm hồ sơ); hàm `expand_abbreviations`. Schema: `TitleBlock`, `DrawingView`, `SheetInfo`, `Abbreviation`, `DossierProfile`, `DocumentIndex` (bỏ `PageKind` — phân loại trang theo tên là việc của bước semantic).
- `analyses`: đọc cấu trúc hồ sơ trong luồng job; ghi `dossier.js` cho viewer (`_dossier_payload`).
- Viewer: tab "Hồ sơ"; danh sách trang lấy tên theo khung tên; tab "Kiểm tra" dùng 4 nhãn Đạt / Không đạt / Cảnh báo / Cần kiểm tra.
- `scripts/inspect_ingest.py` ghi luôn tab "Hồ sơ".
- `docs/check-templates.md`: đặc tả ý nghĩa mẫu kiểm tra M1–M7 + cổng áp dụng (bản thảo).
- Test: `tests/test_sheets.py` (tổng hợp + PDF thật), handshake kiểm `dossier.js`. **70 passed.**

## Kết quả trên PN2

48/48 trang đọc được khung tên (tên, tỉ lệ, số hiệu) · tiêu đề hình / bảng từng trang (lẫn vài ô bảng chữ to) · 53 mục viết tắt · đặc điểm hồ sơ: MẪU NHÀ SH1, 3 tầng, không hầm / tum.

## Chưa kiểm chứng

- Chưa xem viewer bằng trình duyệt (máy không có Chrome cho công cụ tự động) — đã kiểm cú pháp JS và dữ liệu `dossier.js`. Người dùng mở `data/inspect/<lần chạy>/index.html#tab=dossier` để xem.
- Chưa chạy lại luồng thật FE → BE → MAIN với giai đoạn A.
- Khung tên dạng nằm ngang ở đáy trang (đơn vị thiết kế khác) chưa hỗ trợ — chỉ dạng cột dọc mép phải.

## Tiếp theo

Giai đoạn B (định vị + khớp tên bằng embedding có sẵn) — cần người dùng duyệt thêm thư viện (Q-14).
