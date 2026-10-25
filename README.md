# Arch Drawing Checker — MAIN

Lõi AI (Python, FastAPI) của hệ thống Arch Drawing Checker: đọc bản vẽ kiến trúc PDF vector, đối chiếu tiêu chí CHTK, trả kết quả kèm polygon bằng chứng cho backend NestJS.

> **Trạng thái:** đã bắt tay với BE (hợp đồng v0), ingest PDF và rule engine không AI cho **tiêu chí số** (6 checker, ~16% dòng tiêu chí) chạy trong luồng thật. Bảng nối rule → checker hiện viết tay theo bộ tiêu chí mẫu 4 SAO, **chưa tổng quát cho file tiêu chí khác** (xem `docs/checkers.md`). Kết quả kiểm tra mới xem ở viewer debug, **chưa gửi findings về BE**. Chi tiết: [`AGENTS.md`](AGENTS.md) §0.

## Yêu cầu

- Python **≥ 3.10** (máy dev dùng Python 3.14 cài hệ thống, không dùng venv/uv).
- Chạy mọi lệnh tại thư mục repo.

## Cài đặt

```bash
python -m pip install -e ".[dev]"
cp .env.example .env   # rồi sửa token cho khớp BE
```

Biến môi trường chính (tiền tố `MAIN_`, xem `.env.example`):

| Biến | Ý nghĩa |
|---|---|
| `MAIN_SERVICE_TOKEN` | Token BE gửi khi gọi MAIN (`Authorization: Bearer`), khớp `AI_SERVICE_TOKEN` bên BE |
| `MAIN_CALLBACK_TOKEN` | Token MAIN gửi khi gọi callback BE (`x-internal-token`), khớp `INTERNAL_CALLBACK_TOKEN` bên BE |
| `MAIN_INSPECT_ENABLED` | Bật viewer debug tại `/debug/inspect/` — **không xác thực**, tắt khi triển khai |
| `MAIN_MOCK_RULESET` | Bộ rule mock dùng khi BE gửi `rules: []`; để trống để tắt |

## Chạy

```bash
python -m uvicorn drawing_checker.app:app --port 8000   # cổng khớp AI_SERVICE_URL bên BE
python -m pytest
```

- Kiểm tra: `curl http://localhost:8000/health` → `{"status":"ok"}`
- OpenAPI: `http://localhost:8000/docs`
- Viewer kết quả ingest + kiểm tra theo job: `http://localhost:8000/debug/inspect/`
- Thử nhanh một PDF cục bộ (không qua BE): `python scripts/inspect_ingest.py <file.pdf>` — xem `scripts/README.md`

## Tài liệu

`docs/system-overview.md` (FE/BE/MAIN) · `docs/decisions.md` · `docs/open-questions.md` · `docs/architecture.md` · `docs/integration-contract.md` · `docs/criteria-json.md` · `docs/research-log.md` · `docs/roadmap.md` · `docs/progress/`
