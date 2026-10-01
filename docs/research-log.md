# Nhật ký nghiên cứu (2026-09-25 → 2026-09-27)

## 1. Thử CubiCasa5k (`D:\Downloads\CubiCasa5k`)

- Repo paper CubiCasa5K (Kalervo et al. 2019): mạng hourglass đa nhiệm → 44 kênh = 21 heatmap điểm (góc tường, góc biểu tượng, đầu mút cửa) + 12 lớp phòng + 11 lớp biểu tượng; hậu xử lý dựng polygon tường/phòng/biểu tượng.
- Đã chạy được trên CPU: Python 3.10 (uv) + thư viện ở `.pydeps`; sửa code cho CPU và thư viện mới (`.cuda()`, `torch.cuda.LongTensor`, timestamp có `:`, `cm.register_cmap`, `stats.mode`, `is 'H'`); thêm `predict.py` (ảnh so sánh ở `results/`) và `eval.py --format txt --n-samples N`. **Chưa commit** trong repo đó.
- Kết quả: 3 ảnh test — pixel acc phòng 85.9 / 90.9 / 89.4%, biểu tượng ~96–97%. `eval.py` 2 ảnh: Mean IoU phòng 69.8 (pixel) / 70.3 (polygon).
- Thời gian CPU ~40–50 s/ảnh: forward ×4 góc xoay ~30–38 s, dựng polygon ~9 s, đọc SVG ~3 s. GPU chỉ nhanh ~3–4× vì hậu xử lý thuần CPU.
- **Kết luận:** lệch miền (ảnh raster căn hộ Phần Lan, không có chữ/thông số). Chỉ tham khảo cách dựng polygon phòng. Không dùng làm nền (D-04).

## 2. Phân tích PDF mẫu (`D:\Downloads\tieuchuan\`)

- 48 trang, khổ 1445×1162 pt (bản comment 1456×1166). **Vector**: 159–5.918 ký tự/trang, 120 → 316.070 nét vẽ/trang, 1–42 ảnh nhúng/trang (logo, keyplan, hatch).
- Trích được chính xác: tiêu đề trang + tỉ lệ ("MẶT BẰNG KIẾN TRÚC TẦNG 1 _ TL:1/50"), cao độ ("FFL +0.200", "SSL +0.150"), kích thước ("4650", "4800"), bảng thống kê diện tích, ghi chú vật liệu, bảng cửa ("2100w x 2800h").
- Comment của người kiểm tra **không phải annotation PDF** mà là nội dung vẽ thêm vào trang (đám mây đỏ + chữ) → trích bằng cách so chữ giữa hai file. Kết quả: `samples/ground-truth/pn2-dn-reviewer-comments.json` (9 trang, 29 khối, kèm bbox %).
- Comment tiêu biểu: p4 chân tường hàng rào không chống thấm, ron âm theo CHTK, khe hở 2 nhà 10mm, trần ngoài nhà thạch cao chống ẩm 9mm + khung alpha VT, lan can kính 10.76mm + inox 304; p5 bê tông đá mi M200 thép D4@250-300 dốc 1.5%, không bàn giao sàn BTCT tầng 1; p6 trần thạch cao 9mm có shadowline, không ốp đá mặt tiền; p13 không chống mối; p31 & p47 kích thước cửa đi theo CHTK; p43 kính 12.76mm; p44 không ốp trần cemboard; p45 rà soát VE.

## 3. File tiêu chí Excel

Sheet "4 SAO" 127 dòng, 5 nhóm; các sheet khác chỉ 1 ô rác. Chi tiết ở `criteria-json.md`.

## 4. Thử rule engine nhanh trên PDF mẫu (không ML)

Trích chữ bằng PyMuPDF + regex + ghép nhãn–số theo tọa độ:

| Tiêu chí | Trích được | Kết quả |
|---|---|---|
| 1.8 cote tầng 1 vs vỉa hè (Shophouse ≥150mm) | Tầng 1 +0.250, vỉa hè ±0.000 (p38) | đạt |
| 2.1.2 chiều cao tầng 1 (Shophouse ≥4.0m) | +4.450 − 0.250 = 4.2m | đạt |
| 2.1.3 tầng 2–3 (≥3.4m) | 3.4m, 3.4m | đạt (sát ngưỡng) |
| 3.2 rộng bậc ≥250 | "17 BẬC x 250" (p42) | đạt |
| 3.4 cao bậc ≤180 | "18 BẬC x 168", "8 BẬC x 162" | đạt |
| 3.5 số bậc ∈ {17,18,21,22,25} | tầng 1→2: 18+7 = 25; tầng 2→3: 6+8+7 = 21 | đạt |
| 1.4.x kích thước cửa ∈ danh mục | 2100×2800, 3000×2800, 3700×3000, 4800×3000, 900×3000, 850×2800, 1000×1000, 1000×1750 (p47–48) | **không khớp danh mục** — trùng comment p31/p47 của người kiểm tra |

Lưu ý: giả định SH1 = Shophouse; chưa phân biệt cửa đi / cửa sổ trong bảng; ghép nhãn–số bằng khoảng cách tọa độ là heuristic. Phần khó thật là **gắn số với đúng đối tượng**, không phải so sánh.

## 5. Các hướng đã cân nhắc

| Hướng | Kết luận |
|---|---|
| Trích chữ + VLM ngoài (Claude/GPT/Gemini) | Loại — D-02 |
| Host Qwen2.5-VL local | Không cần cho lõi — D-02 |
| OCR (PaddleOCR/VietOCR) | Không cần — D-03 |
| YOLO detect/seg | Hợp cho biểu tượng trên ảnh raster; không đọc chữ; không phải nền |
| CNN trên ảnh render | Vai trò phụ (tách vùng tờ bản vẽ) |
| Model học trên nét vẽ vector (GNN), dataset FloorPlanCAD | Định hướng khi cần nhận dạng ký hiệu/phòng |
| Rule engine + trích xuất có học + model tiếng Việt nhỏ | **Chọn** — D-10 |

## 6. Ingest thật trên bộ mẫu PN2 (2026-09-28)

Công cụ: `scripts/inspect_ingest.py` → viewer HTML (`data/inspect/<pdf>/index.html`).

- **PDF mang layer CAD (Optional Content).** 378 layer, gắn trên **cả nét vẽ lẫn chữ**. Tên theo chuẩn CAD/xref: `A-WALL-PATT`, `A-WALL-FULL`, `A-Door`, `A-Window`, `A-dim`, `A-Ano Text`, `A-Axis line`, `A-hatch`, `A-column`, `A-TEXT BANG VL`…, có tiền tố xref (`xr-se|`, `DETAILS|`, `CHI TIET CHUNG$0$…`). Ví dụ trang 39 (mặt cắt C-C): `xr-se|A-dim` chứa 111 khối chữ kích thước. → Có thể thay một phần lớn việc *nhận dạng* bằng *đọc layer* (liên quan Q-05: không cần DWG vẫn có layer). Cần kiểm trên bộ bản vẽ khác xem quy ước tên layer có ổn định không.
- **Chữ:** phải dùng `page.get_texttrace()` — `get_text()` không trả layer. Đã đối chiếu toàn bộ 48 trang: cùng tập ký tự với `get_text("dict")` (chênh 0,4% do span vắt ra ngoài khổ trang → lọc theo tâm từng ký tự). Dấu tiếng Việt đúng. 9.520 khối chữ, 63.100 ký tự; góc xoay: 0° (75%), 90° (16%), còn lại chữ nghiêng ~23,8° (ký hiệu thang).
- **Nét vẽ:** 2,48 triệu drawing / 48 trang; trang nặng nhất 39 (317k nét, 74% thuộc layer `A-hatch`). Không có nét đứt (`dashes` luôn rỗng) — CAD xuất nét đứt thành đoạn rời. Đa số drawing là 1 đoạn thẳng.
- **Trang 1 (danh mục bản vẽ) là ảnh nhúng**, chỉ có 3 khối chữ vector → nội dung bảng không đọc được nếu không OCR (D-03). Không ảnh hưởng tiêu chí (trang bìa/danh mục), nhưng cho thấy PDF "vector" vẫn có thể lẫn ảnh.
- **Hiệu năng (CPU máy dev):** chữ cả 48 trang ~6 s; nét vẽ trang 39: `get_cdrawings` 2,3 s + chuyển đổi → tổng ~5 s (ban đầu 18 s — Pydantic `model_construct` chiếm 70% → đổi `VectorPath` sang dataclass). Xuất viewer toàn bộ 48 trang: 95 s, 99 MB.

## 7. Rule engine không AI trên bộ mẫu PN2 (2026-09-30)

Luồng thật FE/curl → BE → MAIN, loại nhà shophouse, đủ 5 nhóm, bộ rule mock 4 SAO (D-16).

**Độ phủ:** 92 rule → 86 áp dụng (lọc loại nhà) → 223 dòng tiêu chí; **35 dòng có checker (16%)**, 188 dòng "chưa hỗ trợ". 16 kết quả: **6 đạt · 7 không đạt · 1 chờ người · 2 không thấy dữ liệu**.

| Tiêu chí | Trích từ bản vẽ | Kết quả |
|---|---|---|
| 1.8 cote tầng 1 − vỉa hè ≥150 | +0.250 − ±0.000 = 250 (6 trang) | đạt |
| 2.1.1 tầng hầm | không có nhãn HẦM | không thấy dữ liệu ("nếu có") |
| 2.1.2 tầng 1 ≥4.0m | +4.450 − 0.250 = 4200 | đạt |
| 2.1.3 tầng 2–3 ≥3.4m | 3400, 3400 (tầng 3 tới cao độ MÁI) | đạt sát ngưỡng; **cờ: 2/22 chỗ ghi +7.800 thay vì +7.850 (trang 41)** |
| 2.1.4 tầng tum | không có | không thấy dữ liệu |
| 3.2 rộng bậc ≥250 | 250 | đạt sát ngưỡng |
| 3.2 biến thể ≥280 ("nêu trong Báo cáo NCKT") | 250 | chờ người (điều kiện không kiểm được) |
| 3.4 cao bậc ≤180 | 168 (tầng 1→2), 162 (tầng 2→3) | đạt |
| 3.5 số bậc ∈ {17,18,21,22,25} | 25, 21 | đạt |
| 1.4.x danh mục cửa | DR-01…06, WD-01 (trang 47–48) | **7/7 không đạt** — trùng comment người kiểm tra |

Kỹ thuật đáng giữ:
- **Nhận ra vế ghi chiều cao bậc mà không đoán theo giá trị:** các vế cùng chiều cao bậc trong một chuỗi kích thước cộng lại bằng chiều cao tầng (25 × 168 = 4200 = +4.450 − 0.250; 21 × 162 ≈ 3400). Hai nguồn số liệu độc lập khớp chéo → vừa phân loại vừa tự kiểm chứng.
- **Cao độ:** nhãn ("TẦNG 2", "VỈA HÈ", "MÁI") với số ngay dưới ~11pt trên mặt đứng / mặt cắt; gom theo số đông trên nhiều trang, ghi chú chỗ ghi khác. Nhãn "TẦNG 4" trùng cao độ mái (trang 33) → coi là mái.
- **Bảng cửa:** "4800w x 3000h" + mã cột (DR-/WD-) theo ô bảng (chữ trong ô căn trái, mã căn giữa) + mô tả loại ("trượt" → lùa, "mở"/"bật" → mở). Mục không mã (cửa thăm mái) bỏ qua.
- Toàn bộ chạy trong ~100 s (chủ yếu là ingest + render ảnh debug); extraction + rule engine < 1 s.

Giới hạn: mẫu regex/bố cục rút từ một bộ bản vẽ; tầng trên cùng tính tới cao độ "MÁI" (giả định, confidence 0.85); tread = các vế không khớp chiều cao tầng (suy ra bằng loại trừ, confidence 0.85).

## 8. Tiêu chí vật liệu — bảng vật liệu hoàn thiện + trần ngoài nhà 5.1 (2026-10-01)

Hướng D-17, bản luật (chưa AI). Bộ mẫu PN2, shophouse.

**Bảng vật liệu hoàn thiện trong PDF từ CAD:** không có cấu trúc bảng — chỉ là chữ đặt theo tọa độ + nét kẻ. Bộ dò bảng tổng quát của PyMuPDF (`find_tables`) **thất bại** (nhầm nét kiến trúc thành ô, không thấy bảng vật liệu). Dựng lại bằng mốc thì ổn định:
- đầu cột `KÝ HIỆU` + `MÔ TẢ` cùng hàng; tiêu đề ngay trên, có khi tách nhiều khối chữ (`VẬT LIỆU HOÀN THIỆN` + `TRẦN`); chỉ nhận bảng có chữ "VẬT LIỆU" (loại bảng đèn, chú thích);
- mã theo cột (`FW1`, `FC-01`, `L1`), mô tả ghép với mã **gần nhất theo y** (mô tả có thể lệch trên / dưới mã vài point);
- hai bảng đặt cạnh nhau (trang 22) → chặn biên phải tại đầu cột của bảng bên cạnh.
Kết quả: 108 dòng (80 tường, 28 trần) trên các trang 3, 22–36, 43, 44; đọc đúng toàn bộ khi soát tay. Mã vật liệu còn xuất hiện rải trên mặt bằng (vd. 13 thẻ `FC-` ở trang 22) → dùng được để biết "ở đâu" (chưa làm).

**Ghi chú ngoài bảng:** ghi chú CAD gồm nhiều dòng xếp chồng cùng lề trái → ghép (vd. trang 4 "HỆ KHUNG TRẦN" + "TẤM CEMBOARD"). Đợt này chỉ lấy ghi chú có chữ "TRẦN", bỏ "ĐÈN … TRẦN".

**Unicode tổ hợp:** chữ trang 6 ("CHI TIẾT ĐÓNG TRẦN CEMBOARD ĐIỂN HÌNH") ghi dấu dạng NFD ("O" + dấu sắc rời) → regex không khớp. Sửa ở ingest: chuẩn hóa NFC mọi chữ.

**Phạm vi "ngoài nhà":** bộ PN2 là hồ sơ ngoại thất — trang 3 "DANH MỤC VẬT LIỆU HOÀN THIỆN NGOẠI THẤT", trang 4/6 "… NGOÀI NHÀ", trang 43/44 "MÁI ĐÓN", trang 22–24 "ĐÈN … NGOẠI THẤT". Gợi ý lấy theo trang (từ khóa đầu tiên gặp) — thô, đủ cho bộ này.

**Kết quả 5.1 (so với comment người kiểm tra):**

| Vật liệu trần tìm được | Nguồn | Kết quả | Comment người kiểm tra |
|---|---|---|---|
| cemboard (FC-01, FC-06, ghi chú) | trang 3, 4, 6, 22–24, 43, 44 | **không đạt** (0.9) | trang 4, 6, 44 — **khớp cả 3** |
| gỗ nhựa (FC-02, ghi chú) | trang 3, 22–24, 43, 44 | không đạt (0.9) | **không có comment** → cần người dùng xác nhận (đúng luật nhưng có thể là ngoại lệ thiết kế được chấp nhận) |
| "TRẦN ĐỂ THÔ" (FC-03) | trang 3, 22–24, 43, 44 | chờ người (không nêu vật liệu) | không có |
| bê tông trát + sơn (FC-04, FC-05) | trang 3, 22–24 | 5.1.2 dòng trát: chờ người (không ghi M75 / 15 mm) · dòng sơn: đạt | không có |

Độ phủ: 39/223 dòng có checker (17%, trước 35). Dòng 5.1.1 về hệ khung / bước khung / ty treo chưa hỗ trợ (comment trang 4 có nhắc "hệ khung alpha VT").

Giới hạn: từ điển vật liệu / phạm vi viết tay từ một bộ bản vẽ; một kết quả gộp mọi chỗ ghi cùng vật liệu (bằng chứng nhiều trang); tấm thạch cao / silicat nếu gặp chỉ trả "chờ người" (chưa kiểm độ dày, chống ẩm, vùng biển / đồng bằng).
