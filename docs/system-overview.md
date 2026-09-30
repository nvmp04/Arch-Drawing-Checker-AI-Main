# Toàn cảnh hệ thống: FE · BE · MAIN

Hệ thống **Arch Drawing Checker** hỗ trợ soát bản vẽ kiến trúc nhà ở thấp tầng: người thẩm định tải PDF bản vẽ của một căn nhà, hệ thống đối chiếu với **bộ tiêu chí CHTK** (chuẩn hóa thiết kế, nạp từ Excel), trả về danh sách kết quả kèm vùng khoanh trên bản vẽ để chuyên gia xác nhận.

Đồ án tốt nghiệp · 2 người · 6 tháng · 2 giai đoạn: (1) nghiên cứu / đánh giá khả thi → (2) xây hệ thống mức proof-of-concept.

## 1. Ba repo

| Tên gọi | Thư mục | Stack | Vai trò | Trạng thái (2026-09-27) |
|---|---|---|---|---|
| **FE** | `D:\Downloads\arch-drawing-checker-ai` | Next.js 16 (App Router), React 19, TS, Tailwind v4, TanStack Query, pdf.js, pdf-lib | Giao diện: hồ sơ thẩm định, viewer bản vẽ (pan/zoom, vẽ vùng khoanh), kết quả, bộ tiêu chí, dashboard | UI dựng bằng mock; đã nối thật: nạp Excel ở trang Tiêu chuẩn CHTK |
| **BE** | `D:\Downloads\arch-drawing-checker-backend` | NestJS 11, TS, class-validator, Swagger, exceljs | API cho FE (`/api/v1`, cổng 4000), lưu trữ, điều phối phân tích, nhận callback từ MAIN | Khung 67 endpoint; chạy thật: `/health`, `POST rules/import` (Excel → JSON, chưa lưu CSDL), upload hồ sơ + dispatch sang MAIN + webhook callback (lưu bộ nhớ, chưa CSDL) |
| **MAIN** | `D:\Downloads\arch-drawing-checker-main` (repo này) | Python 3.10, FastAPI | Lõi AI: đọc PDF vector, trích xuất, đối chiếu tiêu chí, trả kết quả + polygon bằng chứng | Bắt tay BE v0 chạy thật (nhận việc, tải PDF, đếm trang, callback); chưa logic phân tích |

> Tên repo FE là `-ai` vì lịch sử đặt tên; **phần AI thật nằm ở MAIN**.
> Tài liệu BE ghi FE nằm ở `C:\Users\LENOVO\Downloads\` — thực tế cả ba nằm ở `D:\Downloads\`.

Thư mục liên quan khác trên máy:
- `D:\Downloads\CubiCasa5k` — thí nghiệm với dataset/model CubiCasa5k (xem `research-log.md`), không phải một phần của hệ thống.
- `D:\Downloads\tieuchuan\` — dữ liệu mẫu thật: file Excel tiêu chí + 2 PDF bản vẽ (bản gốc và bản có comment của người kiểm tra).

## 2. Luồng dữ liệu

```
┌──────────┐  HTTP /api/v1   ┌──────────────┐  POST /v1/analyses (dispatch)   ┌──────────────┐
│    FE    │ ──────────────► │      BE      │ ──────────────────────────────► │     MAIN     │
│ Next.js  │ ◄────────────── │   NestJS     │ ◄────────────────────────────── │   FastAPI    │
└──────────┘  {data}/{error} └──────────────┘  POST /internal/analysis/callback └──────────────┘
     ▲                          │    ▲             (x-internal-token, nhiều lần:     │
     │ pdf.js tải PDF (Range)   │    │              tiến độ từng bước + findings)    │
     └──────────────────────────┘    └───── MAIN tải PDF qua URL có chữ ký ◄────────┘
```

1. Kỹ sư nạp **Excel tiêu chí** ở FE → BE đọc thành **bộ rules** (JSON; mỗi sheet một bộ, ví dụ "4 SAO").
2. Người thẩm định tạo **hồ sơ** ở FE: tải PDF, chọn phân khu, bộ rules, **loại nhà**, các nhóm CHTK cần kiểm.
3. BE gửi việc sang MAIN (dispatch): URL PDF có chữ ký, loại nhà, nhóm, danh sách rule, `callbackUrl`.
4. MAIN chạy pipeline, gọi callback về BE theo từng bước (tiến độ %) và gửi kết quả.
5. BE chuẩn hóa thành **Finding**, lưu, FE hiển thị trên viewer (vẽ polygon theo tọa độ), chuyên gia xác nhận (`approved`) hoặc ghi chú.

Chi tiết hợp đồng BE ↔ MAIN và các điểm cần đồng bộ: `integration-contract.md`.

## 3. Từ vựng dùng chung (khớp FE/BE)

- **Workspace → Zone → Review (hồ sơ = 1 PDF) → Drawing page → Finding.** Rule là danh mục dùng chung, thuộc một RuleSet.
- **FindingStatus:** `pass` · `fail` · `warning` · `pending` · `approved` · `unknown`. MAIN chỉ sinh `pass`/`fail`/`warning`/`pending`/`unknown`; `approved` là của người.
- **FindingSeverity:** `low` · `medium` · `high` · `critical` — trục độc lập với status.
- **CheckType:** A đối chiếu số đo · B vật liệu/thông số · C phân tích hình học · D phán đoán chủ quan. (MAIN: tồn tại, chưa hiện thực — D-08.)
- **ChtkCategory** (suy từ chữ số đầu mã rule): 1 `facade` · 2 `dimension` · 3 `stair-ramp` · 4 `structure` · 5 `finishing`.
- **HouseType:** `shophouse` · `townhouse` · `semi-villa` · `single-villa` · `shop-villa`.
- **CONFIDENCE_THRESHOLD = 0.8.** Dưới ngưỡng không được là `fail`.
- **AnalysisStage** (5 bước tiến độ FE hiển thị): `extract` · `ocr` · `material` · `geometry` · `aggregate`.
