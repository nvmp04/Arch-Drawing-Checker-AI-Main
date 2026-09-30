# Arch Drawing Checker — MAIN (lõi AI phân tích bản vẽ)

Đây là **MAIN**: dịch vụ Python, RESTful, làm lõi AI đọc bản vẽ kiến trúc (PDF/CAD vector) và đối chiếu với bộ tiêu chí CHTK. Là một trong ba repo của hệ thống **Arch Drawing Checker** (đồ án tốt nghiệp, 2 người, 6 tháng).

Đọc file này TRƯỚC KHI làm bất cứ việc gì. Người dùng yêu cầu rõ: **phiên AI mới phải hiểu toàn bộ dự án (FE, BE, MAIN) như phiên đã thảo luận.**

---

## 0. Trạng thái hiện tại — đọc dòng này đầu tiên

**ĐÃ BẮT TAY VỚI BE (hợp đồng v0), CHƯA CÓ LOGIC PHÂN TÍCH.** Chạy thật: `GET /health`, `POST/GET/DELETE /v1/analyses` — nhận việc (Bearer token), tải PDF, đếm trang, gửi callback `extract` → `aggregate` với `findings: []`, hủy job. Đã kiểm chứng với BE thật (2026-09-28, `docs/progress/01-handshake.md`). **Ingest đã hiện thực và nằm trong luồng thật** (chữ + nét vẽ + layer CAD, D-14): BE gửi việc → MAIN tải PDF → ingest từng trang (callback tiến độ theo trang) → `aggregate` với `findings: []`. Kết quả ingest của mỗi job xem tại **`http://localhost:8000/debug/inspect/`** (D-15). Chưa gửi kết quả phân tích nào về BE. Các service phân tích khác vẫn ném `NotImplementedError`; `/v1/capabilities` trả `501`.

Hợp đồng BE ↔ MAIN nguồn sự thật: `D:\Downloads\arch-drawing-checker-backend\docs\contracts\be-main.md` (v0).

Kiến trúc đã được **thảo luận và chốt ở mức khung** (phiên 2026-09-25 → 2026-09-27). Nhiều điểm chi tiết **cố ý bỏ ngỏ** — người dùng yêu cầu không đào sâu thêm cho tới khi họ quay lại. Đừng tự quyết các điểm trong `docs/open-questions.md`.

## 1. Đọc gì, theo thứ tự

| # | File | Để làm gì |
|---|---|---|
| 1 | `docs/system-overview.md` | **Bắt buộc.** Ba repo FE / BE / MAIN, đường dẫn, stack, luồng dữ liệu |
| 2 | `docs/project-context.md` | Bài toán, dữ liệu mẫu, từ vựng ngành xây dựng |
| 3 | `docs/decisions.md` | Những gì đã chốt và **vì sao** (kèm các hướng đã loại) |
| 4 | `docs/open-questions.md` | Những gì đang bỏ ngỏ — **không tự quyết** |
| 5 | `docs/architecture.md` | Pipeline, các feature, mô hình Polygon/bằng chứng |
| 6 | `docs/integration-contract.md` | Hợp đồng BE ↔ MAIN: khung BE đang có + chỗ lệch cần đồng bộ |
| 7 | `docs/criteria-json.md` | Schema JSON bộ tiêu chí do BE sinh từ Excel + nhận xét |
| 8 | `docs/research-log.md` | Đã thử gì, kết quả gì (CubiCasa5k, phân tích PDF mẫu, rule engine thử, comment của người kiểm tra) |
| 9 | `docs/roadmap.md` | Sẽ làm gì, theo thứ tự nào |
| 10 | `docs/progress/*.md` | Nhật ký từng giai đoạn |

Tài liệu của hai repo kia (đọc khi cần ghép nối):
- BE: `D:\Downloads\arch-drawing-checker-backend\AGENTS.md`, `docs/decisions.md` (ADR-05 = hợp đồng AI), `docs/domain-model.md`
- FE: `D:\Downloads\arch-drawing-checker-ai\AGENTS.md`, `context/domain-model.md`, `context/project-state.md`

> ⚠ Tài liệu FE/BE mô tả MAIN là "VLM + OCR + document parsing". **Điều đó đã lỗi thời** — xem `docs/decisions.md` D-02, D-03. Không sửa repo FE/BE khi chưa được yêu cầu; chỉ ghi chỗ lệch vào `docs/integration-contract.md`.

## 2. Nguyên tắc bất di bất dịch

1. **AI chạy local.** Không gọi VLM/LLM bên ngoài (Claude, GPT, Gemini…), không host LLM lớn (Qwen…). Model nhỏ, suy luận chạy được trên CPU. Lý do: giá trị riêng của dự án, chi phí, bảo mật bản vẽ.
2. **Đầu vào chỉ là PDF/CAD vector đồ họa cao.** Không OCR, không xử lý bản scan. Chữ và nét vẽ lấy trực tiếp từ vector.
3. **Không render ảnh để trả về.** MAIN chỉ trả tọa độ; frontend tự vẽ.
4. **Một kiểu hình học duy nhất: `Polygon`**, kèm `precision` (`bbox` | `approximate` | `exact`). Bounding box là polygon 4 đỉnh. `approximate` = không cần khoanh đúng hình, số liệu được xác thực bằng con số ghi trên bản vẽ.
5. **Đơn vị kiểm tra là `requirementLine`**, không phải cả rule — một rule có thể chứa nhiều loại kiểm tra.
6. **`checkType` tồn tại nhưng CHƯA hiện thực** (luôn nullable, không dùng để rẽ nhánh logic).
7. **Không bao giờ trả `approved`** (đó là thao tác của người). Kết quả dưới ngưỡng tin cậy 0.8 không được là `fail` (BE cũng hạ, nhưng MAIN không được cố ý gửi).
8. **Mọi kết luận kèm bằng chứng** (trang + polygon + chữ/số trích được) và `confidence`.
9. Luật (so sánh ngưỡng) ưu tiên hơn ML khi luật làm được chính xác. ML dùng cho phần nhận dạng / gắn kết / hiểu câu chữ.
10. Code, tên biến, route: **tiếng Anh**. Tài liệu, comment giải thích nghiệp vụ, message cho người dùng: **tiếng Việt**.

## 3. Stack

Python **3.10** · FastAPI · Pydantic v2 · pydantic-settings · PyMuPDF (đọc PDF vector) · httpx (gọi callback BE). Dự kiến sau: shapely (hình học), scikit-learn / PyTorch CPU, PhoBERT hoặc bge-m3 cho tiếng Việt. **Hỏi trước khi thêm thư viện lớn.**

## 4. Cấu trúc — feature-based

```
src/drawing_checker/
  app.py              create_app(): đăng ký router của các feature
  config.py           Settings (biến môi trường)
  common/             KHÔNG chứa nghiệp vụ: geometry (Polygon), enums (khớp BE), errors, security
  infrastructure/     tích hợp bên ngoài: backend_client (callback), pdf_fetcher, job_runner
  features/           MỖI THƯ MỤC = MỘT FEATURE
    health/           liveness
    capabilities/     MAIN hỗ trợ kiểm được những gì
    analyses/         API nhận việc từ BE, điều phối pipeline, gửi callback  ← điểm vào
    ingest/           PDF → trang, chữ + tọa độ, nét vẽ
    sheets/           phân loại trang, tách khung nhìn/ô chi tiết, tỉ lệ
    rules/            diễn giải requirementLine → kế hoạch kiểm tra; rule engine so ngưỡng
    extraction/       trích thực thể: cao độ, kích thước, thang, bảng cửa, ghi chú, tên phòng
    geometry/         tường, phòng (polygon), đo đạc
    semantic/         so khớp ghi chú chữ ↔ tiêu chí (model tiếng Việt local)
    findings/         kết quả theo requirementLine + bằng chứng; chuyển sang định dạng BE
    benchmark/        chấm điểm với comment thật của người kiểm tra
tests/  scripts/  samples/  docs/
```

Mỗi feature: `schemas.py` (hợp đồng dữ liệu), `service.py` (nghiệp vụ), `router.py` nếu có API.
Import một chiều: `features/*` → `common/*`, `infrastructure/*`, `config`; `infrastructure` và `common` **không** import `features`. Feature dùng feature khác chỉ qua `schemas.py` (kiểu dữ liệu) hoặc service công khai, không đụng nội bộ. Riêng `analyses` là feature điều phối, được phụ thuộc các feature pipeline.

## 5. Chạy trên máy phát triển hiện tại (Windows)

Máy này **không có GPU**. Từ **2026-09-28** venv chạy được (trước đó Windows Application Control chặn `python.exe` trong venv — lỗi `os error 4551`). `.venv` đã tạo sẵn, cài `-e .[dev]`:

```bash
# Git Bash, tại thư mục repo
.venv/Scripts/python.exe -m uvicorn drawing_checker.app:app --port 8000
.venv/Scripts/python.exe -m pytest
# Thêm phụ thuộc: sửa pyproject.toml rồi
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
# Tạo lại venv nếu mất: "$(uv python find 3.10)" -m venv .venv
```
Đừng gọi `python` trần — nó kích hoạt trình cài Python của Windows.

Dự phòng nếu venv lại bị chặn: cài vào `.pydeps` và chạy bằng Python của uv —
`uv pip install --python "$P" --target .pydeps -r pyproject.toml --extra dev` rồi `PYTHONPATH=".pydeps;src" "$P" -m pytest` (với `P=$(uv python find 3.10)`, PYTHONPATH ngăn bằng `;`).

Cổng mặc định **8000** — khớp `AI_SERVICE_URL=http://localhost:8000` bên BE.

## 6. Quy trình làm việc

- **Thảo luận trước, code sau.** Người dùng muốn duyệt hướng đi trước khi code logic. Trả lời ngắn gọn, tập trung, không lan man.
- Trước khi tạo file: kiểm tra stub đã có — điền vào stub, đừng tạo file song song.
- Đổi hợp đồng với BE → cập nhật `docs/integration-contract.md` cùng lượt.
- Quyết định mới → `docs/decisions.md`. Chốt được một câu hỏi mở → chuyển từ `open-questions.md` sang `decisions.md`.
- Xong một giai đoạn → thêm `docs/progress/NN-<tên>.md`, cập nhật `docs/roadmap.md`.
- Chưa rõ → **hỏi, đừng tự quyết.**
