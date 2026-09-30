# Hợp đồng BE ↔ MAIN

> **Nguồn sự thật hiện tại: `arch-drawing-checker-backend/docs/contracts/be-main.md` (v0 "bắt tay", 2026-09-28).** MAIN đã hiện thực và kiểm chứng với BE thật (D-13, `progress/01-handshake.md`). File này giữ phần phân tích chỗ lệch cho hợp đồng v1 (findings + nội dung rule).

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

Callback hiện gửi: `extract running` 5% (nhận việc) → 10% (đã tải PDF) → tăng theo từng trang ingest tới <90% → `extract completed` 90% + `pageCount` → `aggregate completed` 100% + `findings: []` (D-15).

Ngoài hợp đồng (debug, không xác thực): `GET /debug/inspect/` — viewer kết quả ingest theo job; tắt bằng `MAIN_INSPECT_ENABLED=false`.

Schema Pydantic: `src/drawing_checker/features/analyses/schemas.py` (mirror BE) và `features/findings/schemas.py`.

## 3. Chỗ lệch giữa khung BE và quyết định của MAIN — cần đồng bộ

| # | BE hiện tại | MAIN cần | Ghi chú |
|---|---|---|---|
| L-01 | `rules[]` chỉ có `ruleId, code, checkType, operator, value` | **Thêm `title`, `requirement`, `requirementLines`, `headings`, `parentCode`, `houseTypes`** | Thiếu nội dung chữ thì MAIN không kiểm được ~60% tiêu chí. Khung MAIN đã khai các trường này là tùy chọn |
| L-02 | `checkType` bắt buộc (A–D) ở `RawFinding` | Nullable (D-08) | Rule gửi đi: hợp đồng v0 đã cho `null`. Còn `RawFinding` bắt buộc — chờ v1 |
| L-03 | Finding = rule × trang, **một** `boundingBox` | Kết quả theo **requirementLine**, **nhiều** bằng chứng dạng `Polygon` có `precision` | Đề xuất thêm vào `RawFinding`: `lineIndex`, `reason`, `evidence[]` (giữ `boundingBox` = bbox bao ngoài để FE cũ vẫn chạy) |
| L-04 | `severity` bắt buộc | MAIN không suy được | Q-09 |
| L-05 | Stage `ocr`, `geometry` mô tả "OCR", "VLM" | Không OCR, không VLM | Giữ giá trị enum, đổi mô tả — `architecture.md` §5 |
| ~~L-06~~ | ~~Chưa định header xác thực~~ | `Authorization: Bearer <AI_SERVICE_TOKEN>` | **Đã khớp** — hợp đồng v0, D-13 |
| L-07 | `pageNumber` 1-based, bbox theo % | MAIN theo đúng quy ước này | Q-01 (đề xuất chốt theo BE) |
| L-08 | `status` gồm cả `approved` | MAIN không bao giờ gửi `approved` | — |

Không tự sửa repo BE/FE; khi người dùng đồng ý, thay đổi bên BE ghi vào ADR-05 của BE.
