# 09 · findings v1 — kết quả kiểm tra về BE → FE (2026-10-19)

Quyết định: D-23. Người dùng chốt 2026-10-19: tọa độ theo % trang của BE (Q-01) · MAIN không gửi `severity`, BE gán theo rule khi có (Q-09) · gửi **mọi** kết quả, kể cả "Không áp dụng" / "Chưa hỗ trợ".

## Hợp đồng (RawFindingV1)

Mỗi phần tử trong `findings` của callback `aggregate` = kết quả của **một dòng tiêu chí** (D-09). Chi tiết: `integration-contract.md` §5.3 (MAIN) · `be-main.md` §5 (BE, nguồn sự thật).

- `mainResultId = "<jobId>:<ruleId>:<lineIndex>:<k>"` — `k` vì checker danh mục cửa ra **một kết quả / cửa**, một dòng có thể có nhiều kết quả (hoặc không có kết quả nào: dòng danh mục không có cửa nào thuộc loại đó).
- `rule { code, parentCode, title, requirementLine }` — **bản chụp rule**: BE chưa lưu bộ tiêu chí (L-01), không tra được rule theo `ruleId`.
- `applicability`: `applies` · `not-applicable` (AI kết luận không áp dụng) · `unknown` (chưa hỗ trợ / thiếu dữ liệu). **Dòng không áp dụng gửi status `unknown`** → web hiện "Không xác định" (người dùng 2026-10-19: đó chính là trạng thái sẵn có, không tách mục riêng; lý do "Không áp dụng: …" vẫn hiện).
- `pageNumber` + `boundingBox` = bằng chứng chính (bao các bằng chứng cùng trang với bằng chứng đầu tiên); **bỏ trống** khi dòng không có bằng chứng. `evidence[]` = mọi bằng chứng, % trang.
- Không gửi `severity`, `checkType` (null → bỏ trường, `exclude_none`).

## Đã làm

| Repo | Việc |
|---|---|
| MAIN | `Polygon.from_bbox / bounding_box`; `findings.schemas` (`RawFinding` v1, `BackendEvidence`, `RuleSnapshot`, `Applicability`); `FindingsService.to_backend` (point → % theo kích thước trang đã xoay, cắt tràn trang); `analyses` lưu kích thước trang lúc ingest, gửi findings ở `aggregate`. Test: `tests/test_findings_v1.py`, `test_handshake.py` sửa. **92 test đạt.** |
| BE | Bảng `findings` (migration `0001_findings.sql`, cột + `data` JSONB như `reviews`); `RawFindingDto` v1 (cấm `approved`); `FindingsService.replaceFromAnalysis` (thay toàn bộ kết quả cũ, hạ `fail` < 0.8 → `warning`, `statusCounts`) + `listByReview` (lọc tab / trạng thái…, sắp xếp trạng thái → mức độ → mã → dòng); kiểm job hiện hành **trước** khi lưu (job cũ không ghi đè); giới hạn body JSON 10 MB. **61 unit + 32 e2e đạt.** |
| FE | `Finding` thêm `requirementLine`, `reason`, `applicability`, `evidence`, `lineIndex`; `severity` / `group` / `category` / `pageNumber` / `boundingBox` / giá trị có thể null (badge ẩn khi null); trang hồ sơ thật gọi `GET …/reviews/:id/findings`; thẻ kết quả hiện câu tiêu chí + lý do; mỗi bằng chứng một khung trên bản vẽ, khung quá nhỏ nới tới 1,2% trang. `npm run build` sạch. |

## Chạy thử thật (MAIN + BE, AI tắt, PN2 48 trang)

- BE nhận **201 kết quả**, payload ~188 KB (vượt mặc định 100 KB của Express → phải nâng giới hạn).
- `statusCounts`: pass 5 · fail 8 · pending 1 · unknown 187 (dòng rule engine chưa hỗ trợ — bật AI thì phần lớn thành kết luận).
- Chỉ 14 kết quả định vị được (rule engine không AI). Checker cửa có 2 bằng chứng cùng trang ở xa nhau (dòng bảng + hình cửa) → gộp thành một khung cao ~49% trang → FE đổi sang vẽ từng bằng chứng.

## Còn lại / giới hạn

- Thao tác duyệt (Xác nhận / Ghi chú / Sai kết luận / Không áp dụng / Thêm phát hiện) vẫn chỉ ở bộ nhớ trang FE — chưa lưu BE (integration-contract §5.4).
- BE chưa lưu bộ tiêu chí, chưa gửi nội dung rule (L-01) → MAIN vẫn dùng bộ mock; `ruleId` chưa là khóa ngoại.
- Trang "Kết quả tiêu chí" (`/[slug]/findings`) và dashboard vẫn dùng mock.
- Xuất PDF đánh dấu chỉ vẽ bằng chứng chính.

**Sửa 2026-10-19 (người dùng):** bỏ tab "Không áp dụng" đã tự thêm ở FE — dòng không áp dụng là "Không xác định" sẵn có (MAIN gửi status `unknown`, BE đếm như mọi dòng).
