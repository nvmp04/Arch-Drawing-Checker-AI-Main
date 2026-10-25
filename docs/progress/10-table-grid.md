# 10 · Lưới bảng từ nét vẽ → bản tóm tắt gửi AI đọc bảng theo hàng / ô (2026-10-19)

Mục 4 của "việc đang dở" ở `progress/08` (phần hình học, `drawing-knowledge.md` §3.3). Lý do: bản tóm tắt chỉ dựa vào vị trí chữ (XY-cut) làm chữ của ô nhiều dòng xen với ô bên cạnh (bảng cấu tạo sàn, bảng cửa).

## Khảo sát PN2

- Lưới bảng **không có layer riêng ổn định**: `0`, `A-DETL-LLIN`, `A-Door`, `DETAILS|…`. Nhiều bảng vẽ ô bằng **hình chữ nhật kín**. Lưới bảng thường **nối liền khung trang** (bảng cửa trang 47, bảng sàn trang 37).
- Mặt bằng / mặt đứng tạo "lưới" rất lớn (70–200 đường mỗi chiều) nhưng chỉ 5–18% ô có chữ. Bảng thật: 30–100%.

## Thuật toán (`features/geometry/tables.py`, kiểu lattice — chỉ hình học, không dựa layer)

1. Đoạn ngang / dọc từ mọi nét (cả cạnh hình chữ nhật), dài ≥ 2 pt; nối đoạn thẳng hàng hở ≤ 1 pt.
2. Gom đường ngang + dọc cắt nhau (union-find, `bisect`) → cụm lưới.
3. Ô cơ sở theo vị trí đường kẻ; thiếu nét ngăn → gộp ô; vùng gộp không chữ nhật / thiếu viền → bỏ. "Ô" > 10% trang = vùng vẽ trong khung trang, bỏ.
4. Chữ thuộc ô nhỏ nhất chứa tâm. Giữ cụm có ≥ 4 ô có chữ, ≥ 2 hàng có chữ, ≥ 30% ô có chữ, ≥ 4 ô có chữ cái (loại dải số kích thước chồng nhau, trang 46), không ô nào ôm > 60% chữ.

Tốc độ: ~4 s cho 48 trang PN2 (sau ingest). Thuần Python, không thêm thư viện.

## Kết quả trên PN2

- 47 bảng / 30 trang. Đọc đúng (đối chiếu tay): bảng vật liệu hoàn thiện tường / trần / sàn ngoại thất, ký hiệu, đèn (trang 3, 43, 44); bảng cấu tạo sàn (trang 5, 37–39, ô "TẦNG 2,3" trải 4 hàng); bảng phân loại tường (trang 5); bảng cửa (trang 47, 48 — mỗi cột một cửa, hàng "KÍCH THƯỚC", "CÁNH CỬA"…); bảng ghi chú vật liệu ở các trang mặt bằng.
- Không nhận: bảng viết tắt trang 2 (không có đường kẻ — đã đọc riêng ở `sheets`), trang 4.
- Bản tóm tắt: 121.871 → 125.606 ký tự (+3%), cùng 4.013 khối chữ; bản không lưới **giữ nguyên từng ký tự** (mốc so sánh).

## Bản tóm tắt gửi AI (`semantic/digest.py`)

`build_digest(..., tables=…)`: chữ ngoài bảng in như cũ; mỗi bảng in sau phần chữ của trang:

```
[BẢNG 12]
H1| C1↓4: p5-114 TẦNG 2,3 | C2: p5-115 F2.1 | C3: p5-203 SÀN NỘI; p5-204 THẤT; p5-205 SÀN WC | C5: p5-202 SÀN BTCT( xem BVKC)
H2| C2: p5-116 F2.2 | C3: p5-138 BAN CÔNG; p5-94 SÂN THƯỢNG; p5-206 SÀN P. GIẶT | C5: p5-96 GẠCH PORCELAIN …
```

Giữ mã khối → hậu kiểm trích dẫn không đổi. Phần đầu bản tóm tắt giải thích cách đọc (`C2+1` trải thêm cột, `C1↓4` trải 4 hàng).

## Nối vào luồng

- Job thật (`analyses`): tính bảng từng trang lúc ingest (cần nét vẽ), truyền vào bản tóm tắt khi AI bật.
- `scripts/run_ai_eval.py`, `scripts/export_agent_inputs.py`: mặc định **có** lưới bảng; `--no-table-grid` = mốc chỉ chữ. Kho phát lại khóa theo nội dung bản tóm tắt → **phát lại lượt agent 1–2 phải thêm `--no-table-grid`** (script in nhắc khi `--replay`).

Test: `tests/test_tables.py` (10: lưới giả lập, ô gộp, ô hình chữ nhật, loại lưới thưa / toàn số, khung trang, bản tóm tắt, hồi quy PN2 trang 3 / 5 / 47). **102 test đạt.**

## Chưa làm / đo

- **Chưa đo tác động lên độ chính xác AI** — cần một lượt chạy (agent hoặc API) với bản có lưới, so với mốc lượt 2 (`compare_ai_runs.py`) + kết quả duyệt. Lệnh ở cuối `progress/08`.
- Chưa hiện bảng trên viewer debug; chưa gắn tiêu đề bảng (ở ngoài lưới) với bảng; bằng chứng AI vẫn là khung từng khối chữ, chưa dùng khung ô.
- Đường dẫn ghi chú (leader, §3.4) — bước hình học tiếp theo.
