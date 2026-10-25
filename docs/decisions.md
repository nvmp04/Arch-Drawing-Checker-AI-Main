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
- Chuẩn hóa khoảng trắng đặc biệt (NBSP…) trong chữ; bỏ ký tự nằm ngoài khổ trang và chữ ẩn. Từ 2026-10-02: chuẩn hóa NFC, giải mã font VNI, nối dòng chữ bị tách (research-log §8, §9).
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
  3. Bảng khai báo (`rules/plan_table.py`): rule → checker theo mã (`code` / `parentCode*`), sinh `CheckPlan`. Là MOCK của bước diễn giải (Q-07); bộ diễn giải thật chỉ cần sinh cùng `CheckPlan`. **⚠ Viết tay theo mã rule bộ 4 SAO — không tổng quát cho file tiêu chí khác (xem D-18).**
- **Dòng không có checker** → `unknown` "chưa hỗ trợ" → báo cáo độ phủ tự động.
- **Chỉ dùng số GHI trên bản vẽ**, không đo hình học (người dùng: tỉ lệ có thể sai / gõ đè). Điều kiện áp dụng không kiểm được (vd. "nêu trong Báo cáo NCKT") → `pending` qua trường `note` của bảng.
- **Kết quả chỉ ghi vào viewer** (tab "Kiểm tra"), BE vẫn nhận `findings: []` — chờ chốt Q-09, L-02, L-03.
- **Phạm vi đợt đầu:** 1.8, 2.1.x, 3.2, 3.4, 3.5, 1.4.1–1.4.5.
- Một requirementLine có thể có nhiều kết quả khi tiêu chí là danh mục (1.4.x: mỗi cửa một kết quả, gắn với mục danh mục gần nhất).

## D-17 · Hai cách tìm bằng chứng: thực thể dùng chung (tiêu chí số) · rule khai báo phạm vi rồi đi tìm (tiêu chí chữ / vật liệu)

> ⚠ **Phần "luật trước" đã bị hủy bởi D-18 (2026-10-02).** Ý tưởng "rule khai báo phạm vi rồi đi tìm" và "nhiều–nhiều" vẫn giữ làm định hướng; cách hiện thực bằng bảng / từ điển viết tay thì không.

Người dùng (2026-10-01) đặt câu hỏi ngược: "sao không dùng rule để tìm trong bản vẽ thay vì bóc tách mọi thứ rồi mới kiểm?". Chốt kết hợp:
- **Tiêu chí số / hình học** (chiều cao tầng, bậc thang, cửa…): giữ cách D-16 — trích thực thể **một lần**, nhiều rule dùng chung và khớp chéo (vd. cao độ dùng cho 2.1.x và cho 3.x).
- **Tiêu chí chữ / vật liệu** (phần lớn 84% dòng chưa hỗ trợ): **rule khai báo phạm vi** (vd. 5.1 "Trần ngoài nhà" = bề mặt *trần* + *ngoài nhà*) rồi tìm bằng chứng khớp phạm vi (bảng vật liệu hoàn thiện, ghi chú). Không phân loại "cái này thuộc rule nào" từ phía bản vẽ.
- **Nhiều–nhiều:** một bằng chứng dùng được cho nhiều rule; mỗi rule tự kết luận. Không chắc phạm vi → hạ `confidence` (không `fail`).
- **Luật trước, AI sau** (người dùng đồng ý): từ điển vật liệu / từ đồng nghĩa phạm vi viết tay, **dùng chung cho câu tiêu chí và chữ trên bản vẽ** → danh sách vật liệu được phép suy ra từ câu tiêu chí, không viết cứng. Bản luật là mốc để đo; embedding (Q-12) chỉ thêm vào sau, ở chỗ luật bỏ sót do cách diễn đạt khác, và chỉ để **tìm ứng viên** — kết luận vẫn do luật.
Lý do: chỉ có 1 bộ bản vẽ có comment (Q-06) → chưa đo được AI; loại tiêu chí "chọn vật liệu từ danh sách" luật làm chính xác và giải thích được (nguyên tắc 9).
Loại: dựng mô hình toàn bộ căn nhà rồi phân loại từng phát hiện vào rule.

## D-18 · Không viết cứng ngữ nghĩa câu tiêu chí vào code — gỡ 4 checker ngữ nghĩa (2026-10-02)

**Sự cố:** người dùng sửa câu tiêu chí 4.2.1 dòng 0 thành nghĩa ngược lại ("Sàn bê tông cốt thép"); checker cấu tạo sàn vẫn báo "không đạt — tiêu chí yêu cầu không thực hiện". Nguyên nhân: `rules/plan_table.py` là bảng **viết tay theo mã rule của bộ 4 SAO**; với các checker đợt 2–3 (D-17) nó chứa luôn cách hiểu từng câu (lớp nào, có / không, thông số). Nó không sinh ra khi chạy và không phải thuật toán — AI đã tự làm thay phần ngữ nghĩa cho đúng một file. Người dùng: bộ tiêu chí thay đổi theo file nạp vào → đây là **sai lầm nghiêm trọng**.

**Quyết định (người dùng yêu cầu):**
- **Gỡ hoàn toàn** các checker ngữ nghĩa phụ thuộc file tiêu chí: trần ngoài nhà (5.1), cấu tạo sàn (4.2.x, 4.5.x), chống mối (4.4.1), kính cửa (1.4); gỡ `rules/materials.py` và phần trích xuất chỉ phục vụ chúng (ghi chú trần, ghi chú chủ đề, gợi ý "ngoài nhà").
- **Cấm** thêm vào `plan_table.py` (hay bất kỳ chỗ nào trong code) cách hiểu câu chữ của tiêu chí: vật liệu, cấu tạo, phạm vi, phủ định. Hiểu câu tiêu chí là phần **ngữ nghĩa — phải do bước diễn giải luật (AI) làm**, sinh `CheckPlan` từ chính câu tiêu chí (Q-07). Từ điển / mẫu câu viết tay cũng là ngữ nghĩa viết cứng → không tự làm.
- Dòng tiêu chí chưa có bước diễn giải → **"chưa hỗ trợ"**, không bao giờ áp cách hiểu mặc định.
- **Giữ** phần không phụ thuộc file tiêu chí: sửa ingest (NFC, VNI, nối chữ), đọc bảng vật liệu hoàn thiện, đọc bảng cấu tạo sàn, độ dày kính bảng cửa.
- **Còn lại 6 checker tiêu chí số của D-16** (cote, chiều cao tầng, bậc thang, danh mục cửa): ngưỡng / danh mục đọc từ rule, nhưng "rule nào đo cái gì" vẫn nối theo mã rule 4 SAO. Chưa gỡ — chờ người dùng quyết.

Bài học quy trình: báo cáo "xong checker" phải nói rõ phần nào đọc từ rule, phần nào viết cứng; phép thử bắt buộc cho mọi checker là **sửa câu tiêu chí thì kết quả phải đổi theo**.

## D-19 · Chiến lược theo quy trình của đối tác; thứ tự A (đọc hồ sơ) → B (định vị, embedding) → C (diễn giải, model nhỏ)

Đối tác (2026-10-05) mô tả quy trình: **PDF → AI phân tích đặc điểm hồ sơ → lọc tiêu chí áp dụng → kiểm tra → checklist + báo cáo**, kết quả **Đạt / Không đạt / Cảnh báo / Cần kiểm tra** kèm trang / vị trí; mục tiêu giảm thời gian kiểm tra thủ công. Đối tác muốn **AI tự hiểu tiêu chí nào áp dụng, không duyệt thủ công**. Comment mẫu chỉ minh họa, không đầy đủ (Q-13). Đối tác không chắc chắn về hợp tác (sửa bản vẽ, dữ liệu) → **không phụ thuộc đối tác**, làm hết sức với dữ liệu hiện có.

Người dùng chốt:
- **Mẫu kiểm tra viết bằng thuật toán cố định** (M1–M7, `docs/check-templates.md` — đặc tả ý nghĩa, bản thảo). Chọn mẫu + điền thông số cho từng dòng tiêu chí là việc của AI, tự động; không chắc → "Cần kiểm tra".
- **Làm phần semantic trước bước 3** (gắn mã / ghi chú vào vùng trên mặt bằng — hoãn).
- **Thứ tự:** A. đọc cấu trúc hồ sơ (không AI) → B. định vị + khớp tên (embedding có sẵn) → C. diễn giải (model nhỏ fine-tune). Thêm model chỉ khi có mốc so sánh "không AI".
- **Bốn trạng thái của đối tác** là nhãn hiển thị của checklist: pass → Đạt, fail → Không đạt, warning → Cảnh báo, pending / unknown / chưa hỗ trợ → Cần kiểm tra (ghi rõ lý do).
- Không OCR trang danh mục bản vẽ (ảnh dán): khung tên từng trang cho cùng thông tin dưới dạng chữ vector. Trang 2 (bảng viết tắt) là từ điển của chính bộ hồ sơ → được dùng (không vi phạm D-18).

## D-20 · Vòng duyệt trên web làm dữ liệu huấn luyện: BE giữ thao tác của người, MAIN giữ nhật ký AI, nối bằng `mainResultId` (2026-10-08)

Đối tác cần web để thử và duyệt / sửa kết quả; người dùng muốn thao tác đó thành dữ liệu huấn luyện ("nạp nhiều hồ sơ thì AI hiểu hơn" — nhưng phải qua tay người huấn luyện). Người dùng đồng ý:
- **BE** lưu thao tác của người (CSDL của hệ thống); **MAIN** lưu nhật ký gọi AI (đầu vào, đầu ra, prompt, model, chi phí — cũng là kho ghi lại / phát lại để tiết kiệm). Ghép bằng `mainResultId` gắn trên mỗi kết quả.
- Thao tác duyệt **có cấu trúc**: Đúng · Sai kết luận (trạng thái đúng + mã lý do) · Không áp dụng · Sai vị trí · Thêm phát hiện bị sót. Ghi chú tự do không đủ cho huấn luyện.
- **Kho chờ + người huấn luyện duyệt**: thao tác của đối tác chỉ vào dữ liệu huấn luyện / thư viện ví dụ khi người huấn luyện chấp nhận.
- Dữ liệu tích lũy dùng cho: thư viện ví dụ đưa vào prompt (ngay), đo độ chính xác, và sau tháng 1 huấn luyện model local cho ca dễ ("Claude làm thầy, PhoBERT làm trò").
Chi tiết hợp đồng (bàn giao BE / FE): `integration-contract.md` §5. Việc chặn đầu tiên: BE chưa có CSDL (ADR-03 của BE).

## D-21 · Hạ tầng đưa lên mạng: Oracle Always Free + Neon Postgres + Cloudflare R2 + Cloudflare Access / Tunnel (2026-10-08)

Người dùng chốt một lần cả gói (không báo lẻ tẻ): máy chạy FE + BE + MAIN trên **Oracle Cloud Always Free** (không tạo được thì VPS trả phí nhỏ); CSDL **Neon Postgres** free; PDF + dữ liệu huấn luyện trên **Cloudflare R2** của người dùng ("cloud của tôi"); truy cập qua **Cloudflare Access** (chỉ email được mời, OTP) + **Cloudflare Tunnel** (không mở cổng). Giới hạn ~10 bộ hồ sơ khác nhau cho đối tác. Người dùng cho AI toàn quyền sửa FE / BE. Kế hoạch + tiến độ: `docs/online-rollout.md`.
Đã loại: Vercel Hobby (cấm thương mại), Supabase free (tự dừng sau 1 tuần), máy cá nhân.


## D-22 · Đưa Claude API vào lõi (hạn mức 5 USD/tháng), sau một giao diện chung, mặc định tắt (2026-10-09)

Người dùng: "tạm thời chọn mốc 5$/tháng. Đưa AI thật vào". Q-15 chốt **phần hướng đi** (dùng Claude API, nới nguyên tắc 1 trong giai đoạn thử với đối tác); còn mở: đồng ý dữ liệu của đối tác, chọn model sau khi đo, định nghĩa độ chính xác.
- **Gửi gì:** chữ vector có mã khối (`p5-12`) theo trang, kèm khung tên, tiêu đề hình/bảng, bảng viết tắt, đặc điểm hồ sơ, mã layer (ghi rõ "chỉ là gợi ý"). Không ảnh, không tọa độ; khối chỉ có số (kích thước) lược bỏ — phần số do rule engine. Trang chia vùng kiểu XY-cut theo khoảng trống để hai bảng cạnh nhau không đọc xen hàng (tạm, chờ lưới bảng từ nét vẽ — `drawing-knowledge.md` §3.3). PN2: ~122k ký tự, ~4.000 khối.
- **Cách hỏi:** mỗi rule một lần gọi; câu tiêu chí gửi nguyên văn; prompt chỉ mô tả cách làm (cổng áp dụng, M1–M7, 4 trạng thái) — không chứa nghĩa của tiêu chí cụ thể (D-18). Đầu ra JSON theo lược đồ cố định (structured outputs). Bản tóm tắt hồ sơ là khối hệ thống được cache.
- **Hậu kiểm bằng code:** mã khối không tồn tại bị loại (−0.2 tin cậy); Đạt/Không đạt/Cảnh báo mà không còn bằng chứng → Cần kiểm tra (trừ M4 vắng mặt: Đạt, tin cậy ≤ 0.6); M6/M7 → Cần kiểm tra; không bao giờ `approved`; Không đạt < 0.8 → Cảnh báo (`findings.finalize`).
- **Trong pipeline:** AI chỉ kiểm các dòng rule engine "chưa hỗ trợ"; kết quả vào tab "Kiểm tra" của viewer (chưa gửi BE — chờ findings v1).
- **Chi phí:** sổ chi tiêu `data/ai/usage.jsonl`, chặn khi vượt `MAIN_AI_MONTHLY_BUDGET_USD` (5) và trần mỗi lần chạy `MAIN_AI_MAX_USD_PER_RUN` (1). Giới hạn cứng đặt thêm trong Anthropic Console. Bản ghi mỗi lần gọi `data/ai/calls/` — phát lại miễn phí (`MAIN_AI_PROVIDER=replay`) và là nhật ký AI của D-20.
- **Một giao diện** (`semantic/provider.py`): Claude / phát lại / model giả; thêm nhà cung cấp khác (Gemini…) không đụng chỗ khác.
- Model mặc định `claude-opus-5-5` (theo skill claude-api; đổi bằng `MAIN_AI_MODEL`). Ước tính PN2 cả bộ 92 rule: Opus ~6,7 USD · Sonnet 5.5 ~3,9 · Haiku 5.5 ~0,2 mỗi lần chạy (chưa đo thật) → với 5 USD/tháng, thử trên tập nhỏ hoặc model rẻ.
- AI không tự test: mọi lần gọi thật do người dùng chạy (`scripts/run_ai_eval.py --live`, có hỏi xác nhận).
Tiến độ: `docs/progress/08-claude-integration.md`.

## D-23 · findings v1: MAIN gửi kết quả theo dòng tiêu chí về BE; tọa độ % trang; không gửi severity (2026-10-19)

Người dùng chốt ba điểm, đóng Q-01, Q-09, Q-10:

- **Tọa độ (Q-01):** nội bộ MAIN giữ point PDF của trang đã xoay; gửi BE quy đổi sang **% 0–100 trang đang hiển thị, gốc trên-trái** — đúng `BoundingBoxDto` của BE / FE.
- **`severity` (Q-09):** MAIN không gửi (không có cơ sở suy). BE gán theo rule khi bộ tiêu chí có mức độ; hiện chưa có → `null`, FE ẩn badge. Không đặt giá trị mặc định giả.
- **Phạm vi gửi (Q-10):** mọi kết quả, kể cả "Không áp dụng" và "Chưa hỗ trợ" — cả hai gửi status `unknown` ("Không xác định" trên web, người dùng: không tách mục riêng); `applicability` chỉ là thông tin kèm theo — người duyệt thấy đủ checklist. Đơn vị = dòng tiêu chí; một dòng có thể có nhiều kết quả (checker danh mục cửa: một kết quả / cửa) → `mainResultId` có số thứ tự.
- Mỗi finding mang **bản chụp rule** (mã, tên, câu tiêu chí) vì BE chưa lưu bộ tiêu chí (L-01).

Hợp đồng: `integration-contract.md` §5.3, BE `docs/contracts/be-main.md` §5. Nhật ký: `progress/09-findings-v1.md`.


## D-24 · Chấm kết quả AI cho đối tác: viewer MAIN trên Oracle, IP + Caddy + mật khẩu chung (2026-10-25)

Người dùng: việc chấm AI "rất cấp bách"; web (FE / BE) phục vụ khách hàng nên **không** đưa phần chấm AI vào đó. Chọn: dùng lại viewer debug của MAIN (đã có Đúng / Sai vị trí / Sai, chấm mù, lưu `data/reviews/*.jsonl`) và đưa lên máy Oracle.
- Chưa có tên miền → **không dùng Cloudflare Tunnel / Access** lúc này: mở cổng 80 / 443, Caddy tự cấp HTTPS cho `<IP>.sslip.io`. Khi có tên miền thì quay về Tunnel + Access như D-21.
- `MAIN_REVIEW_ONLY=true`: chỉ `/health` + viewer + API chấm. `MAIN_REVIEW_PASSWORD`: Basic auth cho `/debug/*`, **tên đăng nhập = người chấm** → trường `reviewer` do server ghi (không tin trình duyệt). Không làm giao diện đăng nhập riêng.
- Chỉ đưa lượt 2 (`eval-20261019-005535`, prompt v2). Kết quả chấm nằm trên Oracle; kéo về máy dev bằng `scp` (người dùng chọn: kéo về đúng định dạng jsonl để `run_ai_eval.py` không phải sửa).
- Nhiều người chấm một dòng: lần sau cùng thắng (như cũ); cả hai lần vẫn còn trong file.
Hướng dẫn: `docs/deploy-review.md`.
- **Sửa 2026-10-25 (người dùng):** Oracle báo "Out of capacity" (vùng nhà không đổi được) → dùng **Render miễn phí + Neon Postgres miễn phí**, thêm `psycopg`. Render miễn phí xóa ổ đĩa khi ngủ → `MAIN_REVIEWS_DATABASE_URL` có giá trị thì kết quả chấm vào bảng `ai_reviews` (chỉ thêm, `data` = đúng một dòng jsonl); `scripts/pull_reviews.py` xuất về `data/reviews/*.jsonl`. Triển khai từ một repo GitHub riêng tư dựng từ gói (repo MAIN bỏ qua `data/`). Người dùng: task phụ, giữ đơn giản. Oracle giữ làm cách dự phòng.
