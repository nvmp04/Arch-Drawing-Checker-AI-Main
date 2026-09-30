# Kiến trúc MAIN

## 1. Vào / ra

- **Vào** (từ BE, dispatch): URL PDF có chữ ký · `houseType` · `categories` · danh sách rule (đầy đủ nội dung, gồm `requirementLines`) · `callbackUrl`.
- **Ra** (gọi callback về BE, nhiều lần): tiến độ theo 5 bước + kết quả. Mỗi kết quả gắn với **một `requirementLine` của một rule**: `status`, `confidence`, `reason`, `extractedValue`, `standardValue`, danh sách **bằng chứng** (`Evidence`: trang + `Polygon` + vai trò + chữ/số trích được).

## 2. Pipeline

```
PDF ─► [ingest] ─► [sheets] ─► [extraction] ─┬─► [rules.evaluator]  (số: so ngưỡng)
                                 [geometry] ─┤
                                             └─► [semantic]         (chữ: phù hợp / mâu thuẫn / thiếu)
rules JSON ─► [rules.interpreter] ─► kế hoạch kiểm tra từng requirementLine ─┘
                                             ▼
                                        [findings] ─► callback BE
```

| Feature | Việc | Kỹ thuật định hướng | Train? |
|---|---|---|---|
| `ingest` | PDF → trang (kích thước, xoay), khối chữ + font + tọa độ + **layer CAD**, nét vẽ (đường, đa giác, hatch) + layer. **Đã hiện thực** (D-14) | PyMuPDF `get_texttrace`, `get_cdrawings` | Không |
| `sheets` | Phân loại trang (mặt bằng / mặt cắt / chi tiết / mặt đứng / bảng cửa…); tách khung nhìn + tiêu đề + tỉ lệ (1/50, 1/25, keyplan 1/10000) | Luật từ tiêu đề + khung; sau: classifier | Sau |
| `rules` | `interpreter`: requirementLine → kế hoạch kiểm tra (đối tượng, thuộc tính, toán tử, giá trị chuẩn hóa, loại trang cần tìm). `evaluator`: so ngưỡng | Parser số/đơn vị + luật; sau: model phân loại tiếng Việt | Sau |
| `extraction` | Thực thể: cao độ (FFL/SSL, "TẦNG n +x.xxx"), kích thước (đường kích thước ↔ con số), thang ("N BẬC x H"), bảng cửa ("W w x H h"), ghi chú vật liệu (đường dẫn → vị trí), tên phòng | v0 heuristic tự gán nhãn → v1 model trên đồ thị nét vẽ, train từ nhãn đã được người sửa | Có (v1) |
| `geometry` | Tường (khối hatch) → vùng kín → polygon phòng; đo chiều rộng lọt lòng, diện tích, độ dốc; xác thực bằng kích thước ghi trên bản vẽ | shapely + luật | Có thể |
| `semantic` | Tiêu chí dạng chữ: tìm ghi chú liên quan trong ô chi tiết khớp, phân loại phù hợp / mâu thuẫn / thiếu | Từ khóa + so số → embedding local + PhoBERT | Có (sau) |
| `findings` | Gom kết quả theo requirementLine, gắn bằng chứng, áp quy tắc trạng thái (không `approved`, dưới 0.8 không `fail`), chuyển sang payload BE | Luật | Không |
| `benchmark` | So kết quả với comment thật của người kiểm tra → precision / recall theo nhóm | — | — |
| `analyses` | Nhận dispatch, chạy pipeline nền, gửi callback theo `AnalysisStage`, hủy việc | FastAPI + job runner in-process | — |

## 3. Mô hình hình học (D-06)

```
Point    { x, y }                       # hệ tọa độ: open-questions Q-01 (đề xuất % 0–100, gốc trên-trái, trang đã xoay)
Polygon  { points: Point[≥3], precision: bbox | approximate | exact }
Evidence { pageNumber (1-based), polygon, role, text?, measuredValue?, unit? }
role     = subject (đối tượng được kiểm) | measurement (con số làm căn cứ) | annotation (ghi chú) | region (vùng cần người xem)
```

- Bounding box = `Polygon` 4 đỉnh, `precision=bbox`. Không có kiểu BBox riêng.
- `approximate`: hình gần đúng, **giá trị được xác thực bằng con số ghi trên bản vẽ** (evidence `measurement` đi kèm).
- BE hiện chỉ nhận một `boundingBox` / finding → cần mở rộng (xem `integration-contract.md`). Trong lúc chờ, `findings` có thể suy bbox bao ngoài từ polygon chính.

## 4. Trạng thái kết quả

MAIN sinh: `pass` · `fail` · `warning` (dấu hiệu lệch nhưng chưa chắc / dưới ngưỡng) · `pending` (cần người xem, vd. loại chủ quan — Q-08) · `unknown` (không tìm thấy dữ liệu). Không bao giờ `approved`.

## 5. Ánh xạ AnalysisStage (BE/FE) ↔ việc thật của MAIN

Tên bước của BE mang dấu vết thiết kế cũ (OCR/VLM). Giữ nguyên giá trị enum để không phá FE/BE; nghĩa thực tế:

| Stage | Nghĩa trong MAIN |
|---|---|
| `extract` | ingest + sheets (báo `pageCount`) |
| `ocr` | extraction thực thể số (cao độ, kích thước, thang, bảng) — **không phải OCR** |
| `material` | semantic (tiêu chí dạng chữ) |
| `geometry` | geometry (tường, phòng, đo đạc) |
| `aggregate` | rules.evaluator + findings, gửi toàn bộ kết quả còn lại |

## 6. Hiệu năng (đo trên máy dev, CPU)

Mở PDF 48 trang ~20MB + trích chữ: vài giây. Render 1 trang 80dpi ≈ 0.3 s (chỉ dùng khi debug; MAIN không trả ảnh). Trang nặng nhất ~316k nét vẽ — cần xử lý theo trang / khung nhìn, tránh nạp toàn bộ nét vào RAM một lúc.
