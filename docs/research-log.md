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

> ⚠ **Checker 5.1 ở mục này đã bị gỡ ngày 2026-10-02 (D-18, §11).** Phần đọc bảng vật liệu và Unicode NFC vẫn còn. Kết quả "khớp comment" bên dưới đạt được bằng cách hiểu tiêu chí viết tay cho bộ 4 SAO — chỉ có giá trị tham khảo.

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

## 9. Ingest: chữ mã VNI và dòng chữ bị tách (2026-10-02)

Phát hiện khi khảo sát ghi chú cho bước 2: một số chữ "mất ký tự đầu" ("ỚP CHỐNG THẤM CAO 200", "ƯỜNG GẠCH"). Thực ra có hai hiện tượng của PDF xuất từ CAD:

- **Bảng mã VNI cũ:** 218 lượt chữ dùng font `VNI-*` (trang 4, 5, 7…), mã ký tự theo VNI-Windows — "LÔÙP VÖÕA XI MAÊNG M.75 DAØY 20" = "LỚP VỮA XI MĂNG M.75 DÀY 20". Trước đây hoàn toàn không tìm được bằng từ khóa. Sửa: `ingest/vni.py` giải mã (chữ gốc + ký tự dấu → Unicode) khi tên font bắt đầu bằng "VNI".
- **Một dòng chữ bị tách thành nhiều lượt vẽ:** CAD cắt dòng quanh ký tự có dấu ("QU" + "Ả" + "N", "T ĐƯ" + "ỢC THỂ HIỆN…") hoặc khi đổi font ("L" VNI + "ỚP CHỐNG THẤM" Arial). ~3.500 chỗ toàn file, nặng nhất ở khung tên và các trang ghi chú / bảng cửa. Sửa: nối các lượt liền kề cùng layer / cỡ / hướng khi khoảng hở giữa ký tự cuối và ký tự đầu ≤ 0.5 cỡ chữ; hở ≥ 0.15 cỡ chữ → chèn dấu cách bị lược.

Kết quả: 9.520 → 8.715 khối chữ; câu ghi chú liền mạch ("1/ TẤT CẢ HƯỚNG MỞ CỬA CẦN PHẢI XEM BẢN VẼ…"). Các kết quả kiểm tra cũ không đổi (63 test). Chỗ nối sai tiềm ẩn: hai chữ khác nhau đặt sát nhau dưới nửa cỡ chữ — chưa gặp trên PN2 (mã bảng ↔ mô tả cách ≥ 1.4 cỡ chữ).

## 10. Checker từ bảng: cấu tạo sàn, chống mối, kính cửa (2026-10-02)

> ⚠ **Ba checker ở mục này đã bị gỡ cùng ngày (D-18, §11).** Phần đọc bảng cấu tạo sàn và độ dày kính vẫn còn. Kết quả bên dưới chỉ có giá trị tham khảo.

Người dùng chốt chỉ làm checker chắc chắn đúng. Chi tiết từng checker: `checkers.md` #8–#10.

**Bảng thống kê cấu tạo sàn (trang 5, lặp ở 37–39):** 8 dòng F1.1…F3.1 → 38 lớp cấu tạo / trang, đọc đúng toàn bộ khi soát tay (vị trí, nhóm tầng, lớp ghi trên nhiều dòng). Mỗi lớp có dấu gạch đầu dòng "·" là một khối chữ riêng → lọc bỏ. Hai lớp của cùng một dòng bảng có thể cách nhau một dòng trống (F3.1) nên không tách dòng bảng bằng ngưỡng khoảng hở cố định — dùng "khoảng hở lớn nhất giữa hai mã liên tiếp".

**Kết quả so với comment người kiểm tra:**

| Tiêu chí | Bản vẽ | Kết quả | Comment |
|---|---|---|---|
| 4.2.1 "Không bàn giao sàn bê tông tầng 1" | F1.2, F1.3: "SÀN BTCT" | **không đạt** | trang 5, 13 "Không bàn giao sàn BTCT tầng 1" — **khớp** |
| 4.2.5 mái bằng, dòng 0 "Lớp hoàn thiện: không thực hiện" | F3.1: "LỚP VỮA TẠO PHẲNG DÀY 10MM" | **không đạt** | trang 5 "Lớp vữa hoàn thiện: không thực hiện" — **khớp** |
| 4.2.5 dòng 1 "BT đá mi M200, thép D4@250-300, dày min 40" | M200, D6@200, 50 mm | **không đạt** (thép) | cùng comment trên — **khớp** |
| 4.2.5 dòng 2–4, 4.5.5 | dốc 1.5%, chống thấm PU cuộn 300, sàn BTCT | đạt | — |
| 4.2.4, 4.5.3 ban công | vữa M75 (không ghi dày / dốc), chống thấm không ghi gốc | chờ người | — |
| 4.4.1 "Không xử lý chống mối" | ghi chú chống mối trang 5, 13, 37–39 | **không đạt** | trang 13 "Không thực hiện chống mối" — **khớp** |
| 1.4 kính cửa | DR: 8 mm, WD: 6 mm | kính đúng; khung không ghi hệ → chờ người | — |

Độ phủ: **55/223 dòng (25%)**, trước 39. Tổng kết quả: 14 không đạt · 13 đạt · 9 chờ người · 2 không thấy dữ liệu. Số comment đã bắt được (ước tính, ground truth chưa làm sạch): cửa (trang 31, 47) · trần ngoài nhà (4, 6, 44) · sàn tầng 1 (5, 13) · sàn mái (5) · chống mối (13).

Chưa bắt: trang 4 (các chi tiết nhỏ: ron âm, khe hở 2 nhà, chống thấm chân tường rào, lan can kính 10.76, ngạch cửa…), trang 5 ("không trát mặt bậc", "chèn đỉnh tường…", "trát vữa dày 15mm"), trang 43 (kính mái đón), "Rà soát định hướng VE".

Phát hiện: rule không mã cùng `parentCode` có thể là các biến thể **khác nội dung** (4.2.5*: mái bằng / mái ngói / bitum) chứ không chỉ khác loại nhà → bảng khai báo nhận thêm khóa "<khóa>|<tên rule>". Hai tiêu chí 1.5 và 5.2.1 nói khác nhau về chân tường (porcelain / sơn nước) → cần người dùng xác nhận trước khi viết checker vật liệu tường.

## 11. Sự cố: checker ngữ nghĩa viết cứng theo file tiêu chí — đã gỡ (2026-10-02)

**Phép thử của người dùng:** sửa `requirementLines[0]` của rule 4.2.1 "Sàn tầng 1 trong nhà" từ "Không bàn giao sàn bê tông tầng 1…" thành "Sàn bê tông cốt thép", rồi "Sàn btct"; chạy luồng thật.

| Lần chạy | Cấu hình hồ sơ | Kết quả | Nguyên nhân |
|---|---|---|---|
| "Sàn bê tông cốt thép" (job 14:12) | single-villa, đủ 5 nhóm | **không đạt** — "tiêu chí yêu cầu không thực hiện sàn bê tông tầng 1" | checker không đọc câu tiêu chí; `plan_table` ghi cứng "4.2.1 dòng 0 = lớp sàn bê tông không được có" |
| "Sàn btct" (job 14:16) | townhouse, **chỉ nhóm `facade`** | không có kết quả cho 4.2.1 | rule 4.2.1 thuộc nhóm `structure` → bị lọc theo nhóm đã chọn, không liên quan chữ "btct". Người dùng xác nhận: lúc tạo hồ sơ không chọn đủ nhóm (không phải lỗi BE). Chạy lại với đủ nhóm thì cũng ra "không đạt" như trên |

**Kết luận:** `plan_table.py` là bảng viết tay theo mã rule của bộ 4 SAO, không sinh ra khi chạy. Với các checker đợt 2–3 nó chứa cả cách hiểu câu chữ → hệ thống chỉ "đúng" với đúng file này, và sai lặng lẽ khi câu tiêu chí đổi. Mức phụ thuộc trước khi gỡ:

| Checker | Đọc từ rule | Viết cứng |
|---|---|---|
| Cote, chiều cao tầng, bậc thang | ngưỡng | đo cái gì |
| Danh mục cửa | kích thước cho phép | loại cửa của từng rule |
| Trần ngoài nhà | vật liệu cho phép | phạm vi, dòng trát / sơn, từ điển |
| Kính cửa | độ dày kính | cửa đi / cửa sổ |
| Cấu tạo sàn | không gì | toàn bộ |
| Chống mối | không gì | toàn bộ |

**Xử lý (D-18):** gỡ bốn checker cuối cùng phần trích xuất chỉ phục vụ chúng; các dòng đó trả "chưa hỗ trợ". Độ phủ về **35/223 (16%)**; 64 test đạt. Giữ: sửa ingest, đọc bảng vật liệu hoàn thiện, bảng cấu tạo sàn, kính bảng cửa (không phụ thuộc file tiêu chí).

**Điều còn đúng sau sự cố:** nửa "đọc bản vẽ + so sánh" làm được và chính xác trên PN2. **Điều chưa có:** nửa "hiểu câu tiêu chí" (Q-07) — phải là AI / bước diễn giải tổng quát, không phải bảng tay.

## 12. Giai đoạn A — đọc cấu trúc hồ sơ trên PN2 (2026-10-05)

**Trang 1 (danh mục bản vẽ) là ảnh dán** (3 ảnh raster ~3700×5100 px) — PyMuPDF không đọc được chữ. Không cần OCR: **mỗi trang có khung tên dạng chữ vector**. Ở PN2 khung tên nằm **ngoài vùng hiển thị** (MediaBox 1684 pt, CropBox 1445 pt — bị cắt lề phải, có lẽ để ẩn thông tin dự án); ingest trước đây bỏ chữ ngoài khổ trang nên chưa từng dùng. Nay ingest giữ riêng `margin_texts`.

**Khung tên** (`sheets.read_title_block`): nhãn song ngữ cỡ ~4.8 pt ("TÊN BẢN VẼ - DRAWING NAME", "TỶ LỆ / SCALE:", "HẠNG MỤC - ITEM"), giá trị cỡ 6–9.5 pt ngay dưới; trường lấy theo phần tiếng Anh của nhãn. Giá trị gán cho nhãn gần nhất ở hàng ngay trên (cùng hàng → gần theo ngang). Số hiệu bản vẽ không có nhãn: phần chữ dưới hàng tỉ lệ / ngày. Chữ vẽ đè hai lần (CAD xuất trùng: "CD" "CD") → bỏ trùng. Kết quả: **48/48 trang** có tên, tỉ lệ, số hiệu; số hiệu mã hóa nhóm (GE = chung; SH1 A 10x mặt bằng, 11x kích thước, 12x hoàn thiện sàn, 13x trần, 14x tường, 2xx mặt đứng, 3xx mặt cắt, 4xx chi tiết, 5xx cửa). Lỗi còn lại: trang 35 tên có tiền tố "215" (chữ lạc trong ô tên trên bản vẽ gốc).

**Tiêu đề hình / bảng** (`sheets.read_views`): chữ ngang cỡ ≥ 1.3 × trung vị cỡ chữ của trang, ≥ 10 ký tự; tiêu đề xuống dòng (cùng lề, cùng cỡ, sát dưới) được ghép; tỉ lệ "…_TL:1/25" tách ra. Trang 4 ra đủ 15 tiêu đề chi tiết; trang 31 4 hình tỉ lệ 1/25. **Giới hạn:** ô bảng chữ to in đậm (trang 5: "SÀN NỘI THẤT", "SÂN THƯỢNG") lẫn vào — không phân biệt được bằng font / cỡ; chấp nhận vì mục lục chỉ dùng để tra trang.

**Bảng viết tắt** (`sheets.read_abbreviations`, trang 2): tiêu đề "VIẾT TẮT / ABBREVIATIONS"; cột viết tắt = lề trái có ≥ 4 chữ viết tắt thẳng hàng (2 cặp cột); nghĩa = chữ ngang hàng bên phải, trước cột kế tiếp; bảng khác cùng hàng tiêu đề ("CHÚ THÍCH KÝ HIỆU") chặn biên phải (trước khi chặn, "FW" ghép nhầm "RANH ĐẤT"). Kết quả **53 mục** (BTCT = BÊ TÔNG CỐT THÉP, BVKC = BẢN VẼ KẾT CẤU, FW = PHỂU THU NƯỚC SÀN, MIN = TỐI THIỂU…). `expand_abbreviations`: thay nguyên từ ≥ 2 ký tự, không đụng mã ("DR-01", "CT-ST"); chữ 1 ký tự ("D", "M") không thay. "SÀN BTCT( xem BVKC)" → "SÀN BÊ TÔNG CỐT THÉP( xem BẢN VẼ KẾT CẤU)". Giới hạn: chỉ viết tắt phía bản vẽ; viết tắt trong file tiêu chí ("PD CĐT", "TKYT", "NCKT") không có ở đây.

**Đặc điểm hồ sơ** (`sheets.build_profile`): hạng mục "MẪU NHÀ SH1", công trình, giai đoạn "HỒ SƠ THIẾT KẾ THI CÔNG", tầng 1–3 (nhãn "TẦNG 4" trùng cao độ mái → mái), không hầm, không tum, cao độ, các tỉ lệ. Chưa suy luận (vd. chưa quy "SH1" ra loại nhà — việc của bước semantic).

Viewer: tab **"Hồ sơ"** (đặc điểm, mục lục trang + hình / bảng bấm được để nhảy tới trang, bảng viết tắt); danh sách trang lấy tên theo khung tên; tab "Kiểm tra" dùng 4 nhãn của đối tác. Chạy script trên PN2: 86 s (dpi 60). 70 test đạt.

## 13. Lưới bảng từ nét vẽ trên PN2 (2026-10-19)

- Lưới bảng không nằm ở layer riêng (`0`, `A-DETL-LLIN`, `A-Door`…); nhiều bảng vẽ ô bằng hình chữ nhật kín; bảng hay nối liền khung trang.
- Phân biệt bảng với lưới của hình vẽ bằng tỉ lệ ô có chữ: mặt bằng / mặt đứng 5–18%, bảng thật 30–100%. Thêm điều kiện có chữ cái (loại dải số kích thước) và bỏ "ô" > 10% trang (vùng vẽ trong khung trang).
- 47 bảng / 30 trang, đọc đúng các bảng vật liệu, cấu tạo sàn (ô gộp nhiều hàng), phân loại tường, bảng cửa. ~4 s / 48 trang.
- Bản tóm tắt gửi AI +3% ký tự. Chưa đo tác động lên độ chính xác. Chi tiết: `progress/10-table-grid.md`.
