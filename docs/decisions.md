# Quyết định đã chốt (MAIN)

Mỗi mục: quyết định · lý do · hướng đã loại. Mã `D-xx`. Thảo luận diễn ra 2026-09-25 → 2026-09-27 giữa người dùng và AI.

## D-01 · MAIN là project Python riêng, RESTful

BE là NestJS (không có Python) → lõi AI tách thành dịch vụ Python độc lập, BE gọi qua HTTP. Framework: FastAPI (async, Pydantic, OpenAPI tự sinh). Cổng 8000 (khớp `AI_SERVICE_URL` của BE).
Loại: import trực tiếp như thư viện (BE không phải Python).

## D-02 · AI chạy local, không phụ thuộc model bên ngoài

Không gọi VLM/LLM thương mại (Claude, GPT, Gemini), không host LLM lớn (Qwen2.5-VL…). Model nhỏ, train được, suy luận trên CPU.
Lý do (lời người dùng): chỉ gọi VLM ngoài thì dự án "chả khác gì một cái vỏ với lõi Claude", tốn tiền, phụ thuộc bên ngoài. Thêm: bản vẽ là tài liệu nội bộ của chủ đầu tư.
Loại: pipeline "trích chữ + gửi VLM ngoài" (từng được đề xuất ở đầu phiên).

## D-03 · Đầu vào chỉ là PDF/CAD vector đồ họa cao — không OCR

Người dùng xác nhận: chỉ có file PDF/CAD vector, không có bản scan. PDF mẫu đã kiểm chứng là vector, chữ trích được chính xác kèm tọa độ (`research-log.md` §2).
Hệ quả: không cần OCR (OCR chỉ thêm lỗi dấu tiếng Việt, 0/O…). CNN trên ảnh render chỉ còn vai trò phụ (tách vùng tờ bản vẽ); ưu tiên hướng **học trực tiếp trên nét vẽ vector** (đồ thị nét/chữ) khi cần model nhận dạng.
File DWG gốc: người dùng cho là **khả năng không có** (xem `open-questions.md` Q-05).

## D-04 · CubiCasa5k / YOLO chỉ là thử nghiệm, không phải nền móng

Đã chạy CubiCasa5k thật (`research-log.md` §1): hợp với ảnh raster căn hộ Phần Lan, nhãn chỉ có phòng + biểu tượng, không có chữ/thông số → lệch miền. YOLO không đọc được chữ, kém với tường mảnh dài. Người dùng: "mọi thứ chỉ là quá trình tìm tòi, không hợp thì bỏ".

## D-05 · Tiêu chí đến từ BE dưới dạng JSON

BE đã có luồng Excel → JSON (`POST rules/import`). MAIN không đọc Excel. Schema: `criteria-json.md`.

## D-06 · Mô hình bằng chứng: một kiểu `Polygon` duy nhất, có `precision`

Không chỉ kết luận đúng/sai mà phải **đưa bằng chứng đã phát hiện** dưới dạng vùng trên bản vẽ. Trong code chỉ có `Polygon`; bounding box là polygon 4 đỉnh. Trường `precision`:
- `bbox` — phần tử không quá quan trọng (ghi chú, con số, ký hiệu cửa, ô chi tiết);
- `approximate` — không cần khoanh **chính xác hình dạng**, chỉ cần xác thực với số liệu ghi trên bản vẽ (ví dụ phòng khi chỉ kiểm chiều rộng lọt lòng);
- `exact` — cần đúng hình dạng (ví dụ phòng khi tính diện tích).
Hệ tọa độ cụ thể: xem `open-questions.md` Q-01 (đề xuất theo quy ước % của BE).

## D-07 · Frontend vẽ từ tọa độ; MAIN không render ảnh

Không tốn chi phí render ảnh bằng AI. MAIN chỉ trả tọa độ polygon.

## D-08 · `checkType` tồn tại nhưng chưa hiện thực

4 loại (người dùng định nghĩa, khớp BE/FE A–D): đối chiếu số đo · đối chiếu vật liệu/thông số · phân tích hình học · phán đoán chủ quan (có thể bỏ — người dùng chưa đi sâu). `checkType` "chỉ người và AI hiểu được", không chuẩn hóa được thành danh mục "đo cái gì".
Phát hiện chính: **một rule chứa nhiều checkType** (ví dụ 5.3.1 có số đo, hình học, chủ quan trong cùng một rule). → Giữ trường, nullable, không dùng để rẽ nhánh.

## D-09 · Đơn vị kiểm tra và kết quả là `requirementLine`

Hệ quả trực tiếp của D-08. Kết quả của MAIN gắn với (rule, dòng yêu cầu), không chỉ rule. (BE hiện gắn Finding theo rule × trang — cần đồng bộ, xem `integration-contract.md`.)

## D-10 · Kiến trúc lõi: trích xuất (AI) + phán quyết (luật)

- Phần **so ngưỡng** (≥, ≤, khoảng, danh sách) làm bằng **rule engine** — chính xác tuyệt đối khi đã trích đúng số, giải thích được, không cần dữ liệu train.
- Phần **khó và cần AI**: gắn con số với đúng đối tượng, tách khung nhìn, dựng tường/phòng, hiểu câu chữ ghi chú so với tiêu chí.
- So khớp chữ tiếng Việt: embedding local (vd. bge-m3) để tìm + phân loại nhỏ (vd. PhoBERT) — giai đoạn đầu dùng từ khóa + so số.
Đã thử nhanh trên bản vẽ mẫu: luật tìm lại đúng lỗi "kích thước cửa không thuộc danh mục CHTK" mà người kiểm tra comment (`research-log.md` §4).

## D-11 · Tổ chức code feature-based

Theo yêu cầu người dùng, đồng bộ với BE (feature-based) và FE. Cấu trúc ở `AGENTS.md` §4, chi tiết `architecture.md`.

## D-12 · Theo khung hợp đồng BE (ADR-05): dispatch + webhook callback

BE đã dựng `AiClientService.dispatchAnalysis` và webhook `POST /internal/analysis/callback` (5 bước tiến độ). MAIN theo mô hình **đẩy** này thay vì mô hình "BE polling job" từng đề xuất trong phiên. Payload chi tiết còn lệch — xem `integration-contract.md`.

## D-13 · Bắt tay theo hợp đồng BE v0 (`backend/docs/contracts/be-main.md`) — chốt Q-11

BE ban hành hợp đồng v0 (2026-09-28); MAIN hiện thực đúng, đã kiểm chứng với BE thật:
- BE → MAIN xác thực bằng `Authorization: Bearer <MAIN_SERVICE_TOKEN>` (= `AI_SERVICE_TOKEN` của BE). Sai/thiếu → 401.
- `POST /v1/analyses` trả `202 { externalJobId: "job-<uuid>", stage: "extract" }` ngay, việc chạy nền (asyncio in-process).
- PDF tải nguyên văn `pdfUrl` (chữ ký trong query), theo luồng, kiểm `%PDF-`, xóa file tạm khi xong.
- Callback: body chỉ gồm trường trong hợp đồng (serialize by_alias, bỏ None — BE từ chối trường thừa). 5xx/lỗi mạng retry 3 lần (0.5/1/2 s); 404/409 → dừng job; 400/401 → lỗi cấu hình, không retry.
- v0 chỉ gửi `extract` (running 5% → completed 30% + `pageCount`) rồi `aggregate` completed 100% `findings: []`. Lỗi → `state: failed` + `errorMessage` tiếng Việt.
- `findings`, nội dung rule (L-01…L-04) để dành cho hợp đồng v1.

## D-14 · Ingest: tọa độ nội bộ = point PDF của trang hiển thị; layer CAD là thuộc tính hạng nhất

- Tọa độ trong `ingest` (và các feature nội bộ): **point PDF, trang đã áp /Rotate, gốc trên-trái, y xuống**. Quy đổi sang hệ trả BE (Q-01, vẫn mở) chỉ làm ở `findings`.
- `TextSpan` và `VectorPath` có trường `layer` (tên Optional Content từ CAD). Chữ lấy bằng `get_texttrace` vì chỉ nó trả layer.
- `VectorPath` là `dataclass(slots=True)` với điểm dạng tuple — dữ liệu thô khối lượng lớn, không ra API. Bằng chứng trả BE vẫn là `Polygon` (D-06).
- Chuẩn hóa khoảng trắng đặc biệt (NBSP…) trong chữ; bỏ ký tự nằm ngoài khổ trang và chữ ẩn.
Lý do: research-log §6. Người dùng chưa duyệt riêng từng điểm — là lựa chọn kỹ thuật nội bộ, đổi được.

## D-15 · Kiểm thử luồng thật: ingest chạy trong job, kết quả xem tại lõi qua viewer debug

Người dùng (2026-09-28): muốn test **luồng thực thi của hệ thống** (BE gửi việc → MAIN), không chỉ ingest rời; tạm chưa trả kết quả phân tích về BE.
- Bước `extract` của job = tải PDF + ingest từng trang (trong thread), callback `running` với % tăng theo trang (10 → 90%; BE lấy max). Sau đó `extract completed` + `pageCount`, `aggregate completed` + `findings: []`.
- Mỗi job ghi viewer vào `MAIN_INSPECT_DIR/<externalJobId>/` (dữ liệu trang, ảnh nền debug, `meta.json` gồm reviewId/houseType/categories/trạng thái/lỗi) + trang danh sách lần chạy.
- MAIN phục vụ thư mục đó tại `/debug/inspect/` (StaticFiles), **không xác thực** → chỉ dùng khi phát triển; tắt bằng `MAIN_INSPECT_ENABLED=false`.
- `scripts/inspect_ingest.py` giữ lại để thử nhanh một PDF cục bộ, ghi vào cùng thư mục.
Loại: ingest sẵn ngoài hệ thống (cách làm đầu tiên — người dùng bác vì không kiểm được luồng thật).

## D-16 · Đợt thử rule engine không AI: lõi nhỏ + checker + bảng khai báo; kết quả chỉ ở viewer

Người dùng (2026-09-30): muốn biết rule engine thuần (chưa AI) với bộ rule JSON + PDF mẫu đi được tới đâu, qua luồng thật FE → BE → MAIN; lo dự án phình to.
- **Nguồn rule:** BE v0 gửi `rules: []` → MAIN nạp `MAIN_MOCK_RULESET` (mặc định `samples/criteria/ruleset-4sao.json`). Không sửa BE/FE. Khi hợp đồng v1 gửi nội dung rule (L-01) → tắt mock.
- **Lọc rule:** `houseTypes` chứa loại nhà của hồ sơ; `category` thuộc các nhóm đã chọn.
- **Chống phình — 3 lớp tách bạch:**
  1. Lõi (`rules/interpreter.parse_value`, `rules/evaluator`): phân tích ngưỡng + so sánh, hàm thuần, không nghiệp vụ.
  2. Checker (`rules/checkers.py`): mỗi loại tiêu chí một hàm, dùng thực thể từ `extraction`. Thêm tiêu chí = thêm checker + dòng bảng.
  3. Bảng khai báo (`rules/plan_table.py`): rule → checker theo mã (`code` / `parentCode*`), sinh `CheckPlan`. Là MOCK của bước diễn giải (Q-07); bộ diễn giải thật chỉ cần sinh cùng `CheckPlan`.
- **Dòng không có checker** → `unknown` "chưa hỗ trợ" → báo cáo độ phủ tự động.
- **Chỉ dùng số GHI trên bản vẽ**, không đo hình học (người dùng: tỉ lệ có thể sai / gõ đè). Điều kiện áp dụng không kiểm được (vd. "nêu trong Báo cáo NCKT") → `pending` qua trường `note` của bảng.
- **Kết quả chỉ ghi vào viewer** (tab "Kiểm tra"), BE vẫn nhận `findings: []` — chờ chốt Q-09, L-02, L-03.
- **Phạm vi đợt đầu:** 1.8, 2.1.x, 3.2, 3.4, 3.5, 1.4.1–1.4.5.
- Một requirementLine có thể có nhiều kết quả khi tiêu chí là danh mục (1.4.x: mỗi cửa một kết quả, gắn với mục danh mục gần nhất).

## D-17 · Hai cách tìm bằng chứng: thực thể dùng chung (tiêu chí số) · rule khai báo phạm vi rồi đi tìm (tiêu chí chữ / vật liệu)

Người dùng (2026-10-01) đặt câu hỏi ngược: "sao không dùng rule để tìm trong bản vẽ thay vì bóc tách mọi thứ rồi mới kiểm?". Chốt kết hợp:
- **Tiêu chí số / hình học** (chiều cao tầng, bậc thang, cửa…): giữ cách D-16 — trích thực thể **một lần**, nhiều rule dùng chung và khớp chéo (vd. cao độ dùng cho 2.1.x và cho 3.x).
- **Tiêu chí chữ / vật liệu** (phần lớn 84% dòng chưa hỗ trợ): **rule khai báo phạm vi** (vd. 5.1 "Trần ngoài nhà" = bề mặt *trần* + *ngoài nhà*) rồi tìm bằng chứng khớp phạm vi (bảng vật liệu hoàn thiện, ghi chú). Không phân loại "cái này thuộc rule nào" từ phía bản vẽ.
- **Nhiều–nhiều:** một bằng chứng dùng được cho nhiều rule; mỗi rule tự kết luận. Không chắc phạm vi → hạ `confidence` (không `fail`).
- **Luật trước, AI sau** (người dùng đồng ý): từ điển vật liệu / từ đồng nghĩa phạm vi viết tay, **dùng chung cho câu tiêu chí và chữ trên bản vẽ** → danh sách vật liệu được phép suy ra từ câu tiêu chí, không viết cứng. Bản luật là mốc để đo; embedding (Q-12) chỉ thêm vào sau, ở chỗ luật bỏ sót do cách diễn đạt khác, và chỉ để **tìm ứng viên** — kết luận vẫn do luật.
Lý do: chỉ có 1 bộ bản vẽ có comment (Q-06) → chưa đo được AI; loại tiêu chí "chọn vật liệu từ danh sách" luật làm chính xác và giải thích được (nguyên tắc 9).
Loại: dựng mô hình toàn bộ căn nhà rồi phân loại từng phát hiện vào rule.
