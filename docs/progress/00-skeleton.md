# 00 · Khung xương (2026-09-27)

## Đã làm

- Thảo luận kiến trúc với người dùng qua nhiều vòng (xem `decisions.md` D-01…D-12).
- Đọc tài liệu FE (`arch-drawing-checker-ai`) và BE (`arch-drawing-checker-backend`) để khớp từ vựng, enum, hợp đồng AI (ADR-05 của BE).
- Tạo repo MAIN: tài liệu `docs/`, `AGENTS.md` + `CLAUDE.md`, khung code feature-based dưới `src/drawing_checker/`, test khung, `pyproject.toml`.
- Dữ liệu mẫu: `samples/criteria/ruleset-4sao.json`; `samples/ground-truth/pn2-dn-reviewer-comments.json` (trích tự động bằng so chữ hai PDF).

## Kiểm chứng

- `GET /health` chạy; các route nghiệp vụ trả 501; `pytest` qua (xem README).

## Còn treo

Toàn bộ `open-questions.md`; lệch hợp đồng `integration-contract.md` §3. Chưa có logic nào.
