# Arch Drawing Checker — MAIN (lõi AI phân tích bản vẽ)

Đây là **MAIN**: dịch vụ Python, RESTful, làm lõi AI đọc bản vẽ kiến trúc (PDF/CAD vector) và đối chiếu với bộ tiêu chí CHTK. Là một trong ba repo của hệ thống **Arch Drawing Checker** (đồ án tốt nghiệp, 2 người, 6 tháng).

Đọc file này TRƯỚC KHI làm bất cứ việc gì. Người dùng yêu cầu rõ: **phiên AI mới phải hiểu toàn bộ dự án (FE, BE, MAIN) như phiên đã thảo luận.**

---

## 0. Trạng thái hiện tại — đọc dòng này đầu tiên

**ĐÃ BẮT TAY VỚI BE (hợp đồng v0) + INGEST + RULE ENGINE KHÔNG AI CHO TIÊU CHÍ SỐ (6 checker, 16% dòng tiêu chí). 2026-10-19: ĐÃ GỬI KẾT QUẢ VỀ BE (findings v1, D-23, `docs/progress/09-findings-v1.md`) — BE lưu, FE hiện ở trang hồ sơ.** Chạy thật: `GET /health`, `POST/GET/DELETE /v1/analyses` — nhận việc (Bearer token), tải PDF, đếm trang, gửi callback `extract` → `aggregate` (từ 2026-10-19 kèm findings v1), hủy job. Đã kiểm chứng với BE thật (2026-09-28, `docs/progress/01-handshake.md`). **Ingest nằm trong luồng thật** (chữ + nét vẽ + layer CAD, D-14; từ 2026-10-02 thêm chuẩn hóa NFC, giải mã font VNI, nối dòng chữ bị tách): BE gửi việc → MAIN tải PDF → ingest từng trang → rule engine → `aggregate` kèm findings v1. Kết quả mỗi job xem tại **`http://localhost:8000/debug/inspect/`** (D-15). **Rule engine không AI chạy trong luồng thật** (D-16): extraction heuristic → checker → kết quả theo requirementLine, tab "Kiểm tra" của viewer. BE v0 gửi `rules: []` → MAIN dùng bộ rule mock `samples/criteria/ruleset-4sao.json`. **Giai đoạn A — đọc cấu trúc hồ sơ đã xong** (2026-10-05, D-19, `docs/progress/07-phase-a-dossier.md`): khung tên từng trang (PN2: nằm ngoài vùng hiển thị → `margin_texts`), tiêu đề hình / bảng, bảng viết tắt trang 2 + mở rộng chữ, đặc điểm hồ sơ → tab "Hồ sơ" của viewer. **2026-10-07/08: đối tác yêu cầu khả thi trong 1 tháng, độ chính xác 50–60% trên bộ PN2, web để họ thử và duyệt.** **2026-10-09: đã nối Claude API vào lõi (D-22, `docs/progress/08-claude-integration.md`)** — hạn mức 5 USD/tháng, mặc định TẮT (`MAIN_AI_PROVIDER=off`); AI kiểm các dòng rule engine chưa hỗ trợ, gửi chữ vector có mã khối, hậu kiểm trích dẫn bằng code; thử bằng `scripts/run_ai_eval.py` (người dùng tự chạy `--live`). Nguyên tắc 1 được nới trong giai đoạn thử với đối tác. **Console API chưa có credit** (gói Claude Code không dùng chung) → chạy thử thật bằng **agent Claude Code sạch đóng vai model** (`scripts/export_agent_inputs.py` → agent → `scripts/import_agent_answers.py` → `run_ai_eval.py --replay --calls-dir data/ai-agent/calls`); lượt 1 (prompt v1) chấm đủ 92 rule / 230 dòng PN2, ~273k token agent. **Duyệt kết quả trên viewer** (tab "Kiểm tra": Đúng / Sai vị trí / Sai → kết luận đúng, chấm mù) → `data/reviews/<mã hồ sơ>.jsonl`, `run_ai_eval.py` tự chấm mọi lần chạy sau theo file này. **2026-10-25: đối tác chấm qua mạng** — viewer MAIN lên **Render** ở chế độ chấm (mật khẩu chung, tên đăng nhập = người chấm), kết quả chấm lưu **Neon Postgres** (`MAIN_REVIEWS_DATABASE_URL`), kéo về jsonl bằng `scripts/pull_reviews.py` (D-24, `docs/deploy-review.md`; Oracle là cách dự phòng). Chi tiết + việc đang dở: `docs/progress/08-claude-integration.md` (đọc mục cuối). Vòng duyệt làm dữ liệu huấn luyện: D-20, bàn giao BE / FE ở `docs/integration-contract.md` §5. Chiến lược theo quy trình đối tác: A → B (định vị, embedding) → C (diễn giải, model nhỏ); mẫu kiểm tra M1–M7 ở `docs/check-templates.md` (bản thảo). `semantic` = AI (Claude, D-22); `geometry`: **lưới bảng đã làm** (2026-10-19, `docs/progress/10-table-grid.md` — bản tóm tắt gửi AI in bảng theo hàng / ô; phát lại lượt agent cũ cần `--no-table-grid`), đường dẫn ghi chú / hatch chưa làm; `/v1/capabilities` trả `501`.

**⚠ SỰ CỐ 2026-10-02 — ĐỌC TRƯỚC KHI ĐỤNG VÀO `rules/` (D-18, `docs/progress/06-remove-hardcoded-semantic.md`):** bốn checker ngữ nghĩa (trần ngoài nhà, cấu tạo sàn, chống mối, kính cửa) đã được viết rồi **bị gỡ**, vì cách hiểu câu tiêu chí nằm trong `rules/plan_table.py` — bảng **viết tay theo mã rule của bộ 4 SAO**, không sinh ra khi chạy. Người dùng sửa câu tiêu chí thành nghĩa ngược lại, checker vẫn kết luận như cũ. Bộ tiêu chí **thay đổi theo file nạp vào** → **cấm viết cứng ngữ nghĩa câu tiêu chí vào code** (bảng, từ điển, mẫu câu). Tiêu chí chữ / vật liệu / cấu tạo chỉ làm tiếp khi chốt bước diễn giải luật (Q-07, cần AI). Sáu checker số còn lại vẫn nối theo mã rule 4 SAO — người dùng chưa quyết gỡ hay giữ. Phần đọc bảng trên bản vẽ (vật liệu hoàn thiện, cấu tạo sàn, kính cửa) được giữ, chưa có checker dùng.

Hợp đồng BE ↔ MAIN nguồn sự thật: `D:\Downloads\arch-drawing-checker-backend\docs\contracts\be-main.md` (v0 + findings v1 ở §5).

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
| 8a | `docs/check-templates.md` | **Mẫu kiểm tra M1–M7 + cổng áp dụng** — đặc tả ý nghĩa (bản thảo, D-19) |
| 8b | `docs/checkers.md` | **Danh mục checker**: từng checker kiểm gì, hiện thực thế nào, **phần nào đọc từ rule / phần nào viết cứng**, checker đã gỡ và lý do |
| 8b2 | `docs/drawing-knowledge.md` | **Tri thức nhận dạng đối tượng bản vẽ** (hình học + chữ + quan hệ; layer chỉ là gợi ý, có kiểm chéo) — đối tác xác nhận, thuật toán `geometry` / `extraction` theo file này |
| 8c | `docs/online-rollout.md` | **Đưa hệ thống lên mạng (cả 3 repo):** hạ tầng đã chốt (D-21), các giai đoạn, tiến độ — cập nhật sau mỗi bước |
| 8c2 | `docs/deploy-review.md` | **Viewer chấm kết quả AI cho đối tác trên Render + Neon / Oracle** (D-24): chế độ `MAIN_REVIEW_ONLY` + mật khẩu, cài / cập nhật / kéo kết quả chấm về |
| 9 | `docs/roadmap.md` | Sẽ làm gì, theo thứ tự nào |
| 10 | `docs/progress/*.md` | Nhật ký từng giai đoạn |

Tài liệu của hai repo kia (đọc khi cần ghép nối):
- BE: `D:\Downloads\arch-drawing-checker-backend\AGENTS.md`, `docs/decisions.md` (ADR-05 = hợp đồng AI), `docs/domain-model.md`
- FE: `D:\Downloads\arch-drawing-checker-ai\AGENTS.md`, `context/domain-model.md`, `context/project-state.md`

> ⚠ Tài liệu FE/BE mô tả MAIN là "VLM + OCR + document parsing". **Điều đó đã lỗi thời** — xem `docs/decisions.md` D-02, D-03. Không sửa repo FE/BE khi chưa được yêu cầu; chỉ ghi chỗ lệch vào `docs/integration-contract.md`.

## 2. Nguyên tắc bất di bất dịch

1. **AI chạy local.** Không gọi VLM/LLM bên ngoài (Claude, GPT, Gemini…), không host LLM lớn (Qwen…). Model nhỏ, suy luận chạy được trên CPU. Lý do: giá trị riêng của dự án, chi phí, bảo mật bản vẽ. **Ngoại lệ (D-22, 2026-10-09):** Claude API cho bước diễn giải / phán đoán, theo đề xuất của đối tác, sau một giao diện chung, có hạn mức chi tiêu; hướng lâu dài vẫn là chưng cất sang model nhỏ.
2. **Đầu vào chỉ là PDF/CAD vector đồ họa cao.** Không OCR, không xử lý bản scan. Chữ và nét vẽ lấy trực tiếp từ vector.
3. **Không render ảnh để trả về.** MAIN chỉ trả tọa độ; frontend tự vẽ.
4. **Một kiểu hình học duy nhất: `Polygon`**, kèm `precision` (`bbox` | `approximate` | `exact`). Bounding box là polygon 4 đỉnh. `approximate` = không cần khoanh đúng hình, số liệu được xác thực bằng con số ghi trên bản vẽ.
5. **Đơn vị kiểm tra là `requirementLine`**, không phải cả rule — một rule có thể chứa nhiều loại kiểm tra.
6. **`checkType` tồn tại nhưng CHƯA hiện thực** (luôn nullable, không dùng để rẽ nhánh logic).
7. **Không bao giờ trả `approved`** (đó là thao tác của người). Kết quả dưới ngưỡng tin cậy 0.8 không được là `fail` (BE cũng hạ, nhưng MAIN không được cố ý gửi).
8. **Mọi kết luận kèm bằng chứng** (trang + polygon + chữ/số trích được) và `confidence`.
9. Luật (so sánh ngưỡng) ưu tiên hơn ML khi luật làm được chính xác. ML dùng cho phần nhận dạng / gắn kết / hiểu câu chữ.
10. **Không viết cứng ngữ nghĩa của câu tiêu chí vào code** (D-18). Bộ tiêu chí đổi theo file nạp vào: không bảng tra theo mã rule, không từ điển / mẫu câu viết tay để "hiểu" tiêu chí. Dòng chưa có bước diễn giải → "chưa hỗ trợ". Phép thử bắt buộc: **sửa câu tiêu chí thì kết quả phải đổi theo**.
11. Code, tên biến, route: **tiếng Anh**. Tài liệu, comment giải thích nghiệp vụ, message cho người dùng: **tiếng Việt**.

## 3. Stack

Python **≥ 3.10** (máy dev: 3.14 hệ thống) · FastAPI · Pydantic v2 · pydantic-settings · PyMuPDF (đọc PDF vector) · httpx (gọi callback BE). Dự kiến sau: shapely (hình học), scikit-learn / PyTorch CPU, PhoBERT hoặc bge-m3 cho tiếng Việt. **Hỏi trước khi thêm thư viện lớn.**

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

Máy này **không có GPU**. Từ **2026-09-30** dự án chạy bằng **Python hệ thống (3.14)**, không dùng venv/uv — người dùng muốn gọi thẳng lệnh `python`. Gói đã cài bằng `pip install -e ".[dev]"`.

```bash
# Tại thư mục repo
python -m uvicorn drawing_checker.app:app --port 8000
python -m pytest
# Thêm phụ thuộc: sửa pyproject.toml rồi
python -m pip install -e ".[dev]"
```
`python` trỏ tới `C:\Users\LENOVO\AppData\Local\Python\bin\python.exe`. Nếu terminal còn kích hoạt venv cũ (dấu `(.venv…)` ở prompt) thì chạy `deactivate` trước.

Cổng mặc định **8000** — khớp `AI_SERVICE_URL=http://localhost:8000` bên BE.

## 6. Quy trình làm việc

- **Thảo luận trước, code sau.** Người dùng muốn duyệt hướng đi trước khi code logic. Trả lời ngắn gọn, tập trung, không lan man.
- Trước khi tạo file: kiểm tra stub đã có — điền vào stub, đừng tạo file song song.
- Đổi hợp đồng với BE → cập nhật `docs/integration-contract.md` cùng lượt.
- Quyết định mới → `docs/decisions.md`. Chốt được một câu hỏi mở → chuyển từ `open-questions.md` sang `decisions.md`.
- Xong một giai đoạn → thêm `docs/progress/NN-<tên>.md`, cập nhật `docs/roadmap.md`.
- Thêm / sửa / gỡ checker → cập nhật `docs/checkers.md`, ghi rõ phần nào đọc từ rule, phần nào viết cứng. Khi báo cáo "xong checker" phải nói rõ điều này với người dùng.
- **TUYỆT ĐỐI không tự gọi Claude API / API AI trả phí để test, đo, thử nghiệm** (người dùng 2026-10-09: rất tốn chi phí, việc test do họ tự tay làm). Chỉ viết code + test không tốn tiền (model giả, ghi lại–phát lại); cần chạy thật thì đưa lệnh + ước tính chi phí để người dùng tự chạy. Mặc định cấu hình tắt gọi AI thật.
- Chưa rõ → **hỏi, đừng tự quyết.**
