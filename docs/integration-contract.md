# Hợp đồng BE ↔ MAIN

> **Nguồn sự thật hiện tại: `arch-drawing-checker-backend/docs/contracts/be-main.md` (v0 "bắt tay" 2026-09-28 + findings v1 2026-10-19, §5).** findings v1 đã chạy thật ở cả 3 repo (D-23, `progress/09-findings-v1.md`).
> MAIN đã hiện thực và kiểm chứng với BE thật (D-13, `progress/01-handshake.md`). File này giữ phần phân tích chỗ lệch cho hợp đồng v1 (findings + nội dung rule) và **đề xuất v1 + vòng duyệt làm dữ liệu huấn luyện (§5, 2026-10-08)**.

Nguồn phía BE: `arch-drawing-checker-backend/src/infrastructure/ai-client/ai-client.service.ts`, `src/features/analysis/**`, `docs/decisions.md` ADR-05 (**chưa chốt**, đã dựng khung), `src/common/dto/bounding-box.dto.ts`, `src/common/enums/*`.

## 1. Khung BE hiện có

**BE → MAIN** (`AI_SERVICE_URL`, mặc định `http://localhost:8000`; token `AI_SERVICE_TOKEN`):
```ts
dispatchAnalysis({
  reviewId: string,            // UUID
  pdfUrl: string,              // URL có chữ ký, MAIN tự tải
  houseType: HouseType,
  categories: ChtkCategory[],
  rules: Array<{ ruleId, code, checkType, operator, value }>,
  callbackUrl: string,         // POST /api/v1/internal/analysis/callback
}) → { externalJobId: string, stage: AnalysisStage }
cancelAnalysis(externalJobId) → void
```

**MAIN → BE** webhook `POST /internal/analysis/callback`, header `x-internal-token` = `INTERNAL_CALLBACK_TOKEN`, trả `204`, idempotent theo (`reviewId`, `stage`), gọi nhiều lần:
```ts
{ reviewId, externalJobId, stage: 'extract'|'ocr'|'material'|'geometry'|'aggregate',
  state: 'running'|'completed'|'failed', percent: 0..100, pageCount?, errorMessage?,
  findings?: RawFinding[] }

RawFinding { ruleId (UUID), status, severity, extractedValue, standardValue,
             confidence 0..1, checkType ('A'..'D'), pageNumber (≥1),
             boundingBox { x, y, width, height }   // % 0–100, trang đã xoay, gốc trên-trái }
```
BE sẽ hạ `fail` dưới ngưỡng 0.8 xuống `warning`/`pending`.

## 2. API phía MAIN (khung đã dựng)

| Method | Route | Việc | Trạng thái |
|---|---|---|---|
| GET | `/health` | liveness | chạy thật |
| GET | `/v1/capabilities` | MAIN kiểm được những gì (phiên bản, loại trang, loại thực thể…) | 501 |
| POST | `/v1/analyses` | nhận dispatch, trả `202 { externalJobId, stage }`, chạy nền | **chạy thật (v0)** |
| GET | `/v1/analyses/{externalJobId}` | xem trạng thái (debug / đối soát); 404 nếu không biết job | **chạy thật** |
| DELETE | `/v1/analyses/{externalJobId}` | hủy (ứng với `cancelAnalysis`) → 204 / 404 | **chạy thật** |

Tất cả `/v1/analyses*` yêu cầu `Authorization: Bearer <MAIN_SERVICE_TOKEN>`.

Callback hiện gửi: `extract running` 5% (nhận việc) → 10% (đã tải PDF) → tăng theo từng trang ingest tới <90% → `extract completed` 90% + `pageCount` → `aggregate completed` 100% + `findings` v1 (mọi kết quả; `[]` khi không có bộ rule).

Ngoài hợp đồng (debug, không xác thực): `GET /debug/inspect/` — viewer kết quả ingest theo job; tắt bằng `MAIN_INSPECT_ENABLED=false`.

Schema Pydantic: `src/drawing_checker/features/analyses/schemas.py` (mirror BE) và `features/findings/schemas.py`.

## 3. Chỗ lệch giữa khung BE và quyết định của MAIN — cần đồng bộ

| # | BE hiện tại | MAIN cần | Ghi chú |
|---|---|---|---|
| L-01 | `rules[]` chỉ có `ruleId, code, checkType, operator, value` | **Thêm `title`, `requirement`, `requirementLines`, `headings`, `parentCode`, `houseTypes`** | Thiếu nội dung chữ thì MAIN không kiểm được ~60% tiêu chí. Khung MAIN đã khai các trường này là tùy chọn |
| ~~L-02~~ | `checkType` bắt buộc (A–D) ở `RawFinding` | Nullable (D-08) | **Đã khớp (v1)** — tùy chọn, MAIN không gửi |
| ~~L-03~~ | Finding = rule × trang, **một** `boundingBox` | Kết quả theo **requirementLine**, nhiều bằng chứng | **Đã khớp (v1)** — `lineIndex`, `reason`, `evidence[]`, bằng chứng gửi dạng bbox % |
| ~~L-04~~ | `severity` bắt buộc | MAIN không suy được | **Đã khớp (v1, D-23)** — tùy chọn, BE để `null` |
| L-05 | Stage `ocr`, `geometry` mô tả "OCR", "VLM" | Không OCR, không VLM | Giữ giá trị enum, đổi mô tả — `architecture.md` §5 |
| ~~L-06~~ | ~~Chưa định header xác thực~~ | `Authorization: Bearer <AI_SERVICE_TOKEN>` | **Đã khớp** — hợp đồng v0, D-13 |
| ~~L-07~~ | `pageNumber` 1-based, bbox theo % | MAIN theo đúng quy ước này | **Đã khớp (D-23)** |
| L-08 | `status` gồm cả `approved` | MAIN không bao giờ gửi `approved` | — |

Không tự sửa repo BE/FE; khi người dùng đồng ý, thay đổi bên BE ghi vào ADR-05 của BE.

## 4. Ghi chú vận hành (2026-09-30)

- BE v0 luôn gửi `rules: []` → MAIN dùng bộ rule mock (`MAIN_MOCK_RULESET`, D-16). Kết quả rule engine chỉ ở viewer; callback vẫn `findings: []`.
- Hợp đồng BE §7 ghi `npm run start:dev`, nhưng `package.json` của BE hiện là **`npm run dev`** (nest start --watch). Chưa sửa repo BE — báo người dùng.

## 5. Đề xuất v1 — gửi kết quả + vòng duyệt làm dữ liệu huấn luyện (2026-10-08, D-20)

> **Tài liệu bàn giao cho người làm BE / FE.** Người dùng đã đồng ý hướng; chi tiết trường dữ liệu còn chỉnh được khi hiện thực. MAIN không sửa repo BE / FE — khi bên BE chốt, ghi vào ADR-05 và `docs/contracts/be-main.md` (v1) của BE, rồi MAIN cập nhật lại mục này.

### 5.1 Vì sao

Đối tác sẽ dùng web để **duyệt và sửa kết quả**. Thao tác duyệt vừa để đo độ chính xác, vừa là **dữ liệu huấn luyện** (thư viện ví dụ cho AI, sau này huấn luyện model local — "Claude làm thầy, PhoBERT làm trò"). Muốn vậy, thao tác phải **có cấu trúc** (nút bấm, lựa chọn) và **ghép được** với cái AI đã thấy / đã trả lời.

### 5.2 Ai giữ dữ liệu gì

| Bên | Giữ | Lý do |
|---|---|---|
| **BE** (cơ sở dữ liệu của hệ thống) | Finding, mọi thao tác duyệt của người (ai, lúc nào, sửa gì), phát hiện do người thêm, cờ "người huấn luyện đã duyệt" | BE quản người dùng / hồ sơ / finding; là nguồn sự thật cho thao tác của người |
| **MAIN** | Nhật ký gọi AI: đầu vào gửi model (tóm tắt trang, câu tiêu chí), đầu ra, phiên bản prompt, model, token, chi phí; kết quả diễn giải bộ tiêu chí | Chứa nội dung prompt và chi tiết kỹ thuật; dùng cho ghi lại / phát lại (tiết kiệm chi phí) |
| **Nối** | `mainResultId` — mã duy nhất MAIN gắn cho mỗi kết quả, BE lưu cùng finding | Khi huấn luyện, MAIN lấy thao tác duyệt từ BE, ghép với nhật ký của mình → mẫu "đầu vào · AI trả lời · người sửa thành" |

```
Đối tác duyệt trên web ──► BE (lưu thao tác: người + thời điểm)
                                  │  API nội bộ xuất dữ liệu duyệt (5.5)
MAIN (nhật ký gọi AI) ◄───────────┘
        └─► ghép theo mainResultId ─► kho chờ ─► người huấn luyện duyệt ─► thư viện ví dụ / dữ liệu huấn luyện
```

**Việc chặn đầu tiên phía BE:** BE chưa có cơ sở dữ liệu (ADR-03 chưa chọn ORM; finding và hồ sơ đang ở bộ nhớ). Không có CSDL thì mọi thao tác duyệt mất khi khởi động lại → phải làm trước mọi mục dưới.

### 5.3 MAIN → BE: `findings` trong callback — ✅ ĐÃ HIỆN THỰC (2026-10-19, D-23)

Mỗi phần tử = một kết quả của **một dòng tiêu chí** (D-09), có thể nhiều bằng chứng. Gửi ở `aggregate completed`. Trường `null` **bỏ hẳn** khỏi JSON (BE không nhận `null` cho trường tùy chọn).

```ts
RawFindingV1 {
  mainResultId: string,          // "<jobId>:<ruleId>:<lineIndex>:<k>" — k: một dòng có thể nhiều kết quả (vd. một / cửa)
  ruleId: string,                // UUID rule
  lineIndex: number,             // chỉ số requirementLine (0-based)
  rule: {                        // bản chụp rule — BE chưa lưu bộ tiêu chí (L-01)
    code?: string, parentCode?: string, title: string, requirementLine: string,
  },
  status: 'pass'|'fail'|'warning'|'pending'|'unknown',   // không bao giờ 'approved' (BE trả 400)
  applicability: 'applies'|'not-applicable'|'unknown',   // not-applicable luôn đi với status 'unknown' (Không xác định)
  severity?: FindingSeverity,    // MAIN không gửi (Q-09)
  checkType?: 'A'|'B'|'C'|'D',   // MAIN không gửi (D-08)
  confidence: number,            // 0..1; < 0.8 không bao giờ là 'fail'
  extractedValue?: string,
  standardValue?: string,
  reason: string,                // lý do tiếng Việt
  pageNumber?: number,           // trang của bằng chứng chính — không có khi không định vị được
  boundingBox?: BoundingBox,     // % 0–100 trang đã xoay, gốc trên-trái — bao các bằng chứng cùng trang chính
  evidence: Array<{
    pageNumber: number,
    boundingBox: BoundingBox,    // %
    role: 'subject'|'measurement'|'annotation'|'region',
    text?: string,
  }>,
}
```

BE: lưu bảng `findings` (thay toàn bộ kết quả cũ của hồ sơ), hạ `fail` < 0.8 → `warning`, tính `statusCounts`; FE đọc `GET /workspaces/:slug/reviews/:id/findings`. Payload PN2 ~190 KB → BE nâng giới hạn body JSON lên 10 MB.

Ánh xạ hiển thị theo đối tác (D-19): `pass` → Đạt · `fail` → Không đạt · `warning` → Cảnh báo · `pending` / `unknown` → Cần kiểm tra (FE hiện `reason`).

Ràng buộc unique ở BE: (`review_id`, `main_result_id`).

### 5.4 Thao tác duyệt cần ghi (BE + FE)

Ghi vào `finding_events` (append-only, đã có trong `data-model.md` của BE) — **thêm các loại sự kiện**:

| Nút trên FE (thẻ kết quả) | `finding_events.type` | Dữ liệu thêm | Dùng để huấn luyện | Ưu tiên |
|---|---|---|---|---|
| **Đúng** | `confirmed` (đã có) | — | mẫu đúng | có sẵn |
| **Sai kết luận** → chọn trạng thái đúng + lý do ngắn | `verdict-corrected` | `from_status`, `to_status`, `reason_code` (danh sách chọn), `comment?` | phán đoán | **phải có** |
| **Không áp dụng cho hồ sơ này** | `not-applicable` | `reason_code`, `comment?` | cổng áp dụng | **phải có** |
| **Sai vị trí** → chọn trang / khoanh lại | `evidence-corrected` | `page_number`, `bounding_box` (%) | định vị | nên có |
| *(ghi chú tự do)* | `note-changed` (đã có) | — | ít giá trị huấn luyện | có sẵn |

**Phát hiện do người thêm** (thứ hệ thống bỏ sót — giống comment của người kiểm tra): nút **"Thêm phát hiện"** ở viewer → chọn tiêu chí (rule + dòng), trang, khoanh vùng, trạng thái, ghi chú. Lưu như finding với `source = 'human'` (không có `mainResultId`). **Phải có.**

**Duyệt của người huấn luyện:** mỗi sự kiện / phát hiện do người thêm có `trainer_status`: `waiting` (mặc định) · `accepted` · `rejected`, đặt bởi người có vai trò huấn luyện (đề xuất: `owner` / `admin`). **Chỉ `accepted` mới vào dữ liệu huấn luyện.** Lý do: đối tác có thể duyệt sai / không nhất quán (bản vẽ của họ cũng không chắc đúng chuẩn).

`reason_code` gợi ý (FE hiện danh sách, có "Khác"): `wrong-page` · `misread-value` · `wrong-criterion-understanding` · `drawing-ambiguous` · `criterion-not-applicable` · `other`.

Luật miền giữ nguyên: "Xác nhận" → `approved` (không phải `pass`); mọi thay đổi cập nhật `reviews.status_counts` cùng transaction.

### 5.5 BE → MAIN: xuất dữ liệu duyệt (API nội bộ)

`GET /api/v1/internal/feedback-export?since=<ISO 8601>&trainerStatus=accepted` — header `x-internal-token` (giống webhook). Trả các sự kiện duyệt + phát hiện do người thêm từ thời điểm `since`, mỗi dòng gồm: `mainResultId?`, `reviewId`, `ruleId`, `lineIndex`, `type`, giá trị trước / sau, `reasonCode`, `comment`, `actorRole`, `trainerStatus`, `createdAt`. MAIN gọi khi cần (script huấn luyện / cập nhật thư viện ví dụ), không gọi theo lịch.

### 5.6 L-01 — gửi nội dung rule (bắt buộc cho hướng diễn giải bằng AI)

Không đổi so với L-01: `rules[]` trong dispatch cần `title`, `headings`, `requirement`, `requirementLines`, `parentCode`, `houseTypes`. Thiếu thì MAIN chỉ chạy được bằng bộ rule mock.

### 5.7 Thứ tự đề xuất cho BE / FE

1. CSDL thật cho hồ sơ, finding, finding_events (chọn ORM — ADR-03).
2. Nhận `RawFindingV1` (5.3) + gửi nội dung rule (5.6).
3. FE hiển thị checklist 4 trạng thái + `reason` + nhiều bằng chứng.
4. Nút "Sai kết luận", "Không áp dụng", "Thêm phát hiện" (5.4).
5. `trainer_status` + giao diện duyệt kho chờ cho người huấn luyện.
6. API xuất dữ liệu (5.5). "Sai vị trí" làm sau nếu kịp.

