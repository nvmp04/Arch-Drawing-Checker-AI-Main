# Tri thức nhận dạng đối tượng trên bản vẽ (vector PDF xuất từ CAD)

> **Mục đích kép:**
> 1. **Đối tác kiểm tra:** mỗi mục có ô xác nhận. Đúng thì đánh dấu; sai hoặc thiếu thì ghi lại cách công ty thể hiện thực tế.
> 2. **Củng cố thuật toán:** feature `geometry` / `extraction` / `sheets` hiện thực theo đúng file này. Đổi cách nhận dạng thì sửa file này cùng lượt.
>
> **Phạm vi:** tri thức về **cách thể hiện bản vẽ** (quy ước vẽ, thường ổn định theo TCVN và thói quen CAD). **Không** chứa ý nghĩa câu tiêu chí. Hiểu tiêu chí là việc của bước diễn giải (D-18, nguyên tắc 10).
>
> **Nhãn trạng thái từng mục:**
> - **[PN2]** đã quan sát trên bộ PN2;
> - **[GT]** giả thuyết theo quy ước chung, chưa kiểm trên dữ liệu thật;
> - **[ĐT]** đối tác đã xác nhận.
>
> Tạo 2026-10-09.

## 1. Nguyên tắc chung

Một đối tượng được xác định bằng **nhiều nguồn bằng chứng cùng lúc**. Không nguồn nào được quyết định một mình:

| # | Nguồn | Ví dụ | Độ tin |
|---|---|---|---|
| 1 | **Hình học** của nét | Hai nét song song cách đều; cung 90°; đa giác kín tô mẫu | Cao |
| 2 | **Nội dung chữ** | "+3.600", "DR-01", "MẶT CẮT C-C", số mm | Cao |
| 3 | **Quan hệ không gian** | Chữ nằm trong ô bảng; đường dẫn nối chữ với vùng hatch; số nằm giữa hai vạch kích thước | Cao |
| 4 | **Tỉ lệ khung nhìn** | Tường 200 mm ở 1/100 → hai nét cách nhau 2 mm trên giấy | Trung bình (cần đọc đúng tỉ lệ) |
| 5 | **Tên layer CAD** | `A-Door`, `A-dim`, `A-hatch` | **Chỉ là gợi ý**, có thể sai |

**Về layer:**
- Layer chỉ dùng để **sắp thứ tự tìm** (tìm ở layer gợi ý trước). Không bao giờ dùng để **loại bỏ** dữ liệu.
- Mỗi layer của mỗi hồ sơ được **kiểm chéo**: vai mà tên gợi ý so với vai mà hình học + nội dung cho thấy (mục 4). Mâu thuẫn → layer bị đánh "không tin cậy" và tên của nó bị bỏ qua.
- Hồ sơ có layer vô nghĩa (`0`, `Layer1`) hoặc không có layer → hệ thống vẫn chạy, chỉ chậm hơn và kém chắc hơn.

**Khi các nguồn mâu thuẫn:** hạ độ tin cậy, kết luận "Cần kiểm tra". Không chọn đại một nguồn.

## 2. Đặc điểm của PDF xuất từ CAD (ảnh hưởng mọi nhận dạng)

| Đặc điểm | Hệ quả | |
|---|---|---|
| Nét đứt / nét chấm gạch bị xuất thành **nhiều đoạn rời**, không có thuộc tính nét đứt | Muốn nhận trục định vị, đường khuất, đường bao mái thì phải nối đoạn thẳng hàng có khoảng hở đều | [PN2] |
| Một dòng chữ bị **cắt thành nhiều mảnh** quanh ký tự có dấu hoặc khi đổi font | Phải ghép lại trước khi đọc (đã làm ở ingest) | [PN2] |
| Font **VNI-Windows** (mã cũ) lẫn Unicode | Giải mã VNI (đã làm) | [PN2] |
| Chữ có thể ở dạng **NFD** (dấu tách rời) | Chuẩn hóa NFC (đã làm) | [PN2] |
| Khung tên có thể nằm **ngoài vùng hiển thị** của trang | Vẫn đọc (`margin_texts`) | [PN2] |
| Một số trang hoặc vùng là **ảnh nhúng**: trang danh mục, logo, keyplan, một số mẫu hatch | Không đọc được nội dung ảnh (không OCR, D-03). Chỉ biết "ở đây có ảnh" | [PN2] |
| Bản vẽ dẫn từ file khác (xref) → tên layer có **tiền tố** (`xr-se\|`, `DETAILS\|`, `…$0$…`) | Bỏ tiền tố khi so tên; tiền tố cho biết nguồn | [PN2] |
| Hatch chiếm phần lớn số nét (trang 39: 74% nét thuộc `A-hatch`) | Tách hatch ra trước khi tìm tường, cửa… để giảm nhiễu | [PN2] |

## 3. Từng loại đối tượng

Mỗi mục ghi:
- **Hình học**: dấu hiệu từ nét vẽ.
- **Chữ**: dấu hiệu từ nội dung chữ.
- **Quan hệ**: liên hệ với đối tượng khác.
- **Layer gợi ý**: tên quan sát trên PN2, chỉ để tham khảo.
- **Dễ nhầm**: những gì trông giống nhưng không phải.

### 3.1 Khung tên (title block) — [PN2]
- **Hình học:** khung chữ nhật lớn ở mép phải hoặc dưới trang, chia nhiều ô kẻ.
- **Chữ:** nhãn song ngữ cỡ nhỏ (~4,8 pt) như "TÊN BẢN VẼ - DRAWING NAME", "TỶ LỆ / SCALE:", "HẠNG MỤC - ITEM"; giá trị cỡ lớn hơn nằm ngay dưới nhãn.
- **Quan hệ:** lặp lại cùng vị trí trên mọi trang.
- **Dễ nhầm:** bảng ghi chú chung ở mép trang.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.2 Khung nhìn và tiêu đề hình (viewport) — [PN2] tiêu đề · [GT] khung bao
- **Chữ:** tiêu đề cỡ lớn hơn chữ thường (≥1,3 lần trung vị), kèm tỉ lệ ("MẶT BẰNG KIẾN TRÚC TẦNG 1 _ TL:1/50"). Có thể xuống dòng.
- **Hình học:** tiêu đề thường có gạch chân. Mỗi hình chiếm một vùng tách biệt, có khoảng trống quanh.
- **Quan hệ:** tiêu đề nằm **dưới** (đôi khi trên) hình của nó. Mọi chữ và nét trong vùng thuộc khung nhìn đó và dùng **tỉ lệ của nó**.
- **Dễ nhầm:** tên phòng cỡ lớn; tiêu đề bảng.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.3 Bảng (vật liệu hoàn thiện, cấu tạo sàn, cửa, diện tích, viết tắt) — [PN2] nội dung + lưới kẻ (hiện thực: `geometry/tables.py`, `progress/10-table-grid.md`)
- **Hình học:** lưới các đường ngang và dọc tạo ô chữ nhật. Hàng tiêu đề thường có nét đậm hơn hoặc tô nền.
- **Chữ:** hàng đầu là tên cột. Ô có thể nhiều dòng. Ô gộp (merge) trải nhiều hàng hoặc cột.
- **Quan hệ:** chữ thuộc ô nào thì mang **địa chỉ** (bảng, hàng, cột). Ô gộp áp dụng cho mọi hàng nó trải qua.
- **Layer gợi ý:** `A-TEXT BANG VL` (chữ). Đường kẻ trên PN2 nằm ở `0`, `A-DETL-LLIN`, `A-Door`… — không dùng layer để tìm lưới. [PN2]
- **Trên PN2:** nhiều bảng vẽ ô bằng hình chữ nhật kín; lưới bảng thường nối liền khung trang; bảng viết tắt trang 2 không có đường kẻ. [PN2]
- **Dễ nhầm:** khung tên (cũng là lưới); lưới trục định vị; mặt bằng / mặt đứng (lưới lớn nhưng chỉ 5–18% ô có chữ — bảng thật ≥ 30%); dải số kích thước chồng nhau (toàn số). [PN2]
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.4 Ghi chú và đường dẫn (leader) — [GT]
- **Hình học:** đường gấp khúc 1–2 đoạn, một đầu sát chữ, đầu kia kết thúc bằng mũi tên, chấm tròn hoặc gạch chéo **chạm vào** đối tượng được chú thích.
- **Chữ:** mô tả vật liệu hoặc cấu tạo ("SÀN BTCT DÀY 100", "TRẦN THẠCH CAO KHUNG CHÌM"). Ở mặt cắt thường là **danh sách nhiều dòng**, thứ tự từ trên xuống ứng với các lớp cấu tạo.
- **Quan hệ:** ghi chú **nói về** đối tượng mà đầu kia của đường dẫn chạm vào. Đây là quan hệ quan trọng nhất để gắn chữ với hình.
- **Layer gợi ý:** `A-Ano Text`.
- **Dễ nhầm:** đường kích thước; nét hình bị chữ đè lên.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.5 Kích thước (dimension) — [PN2]
- **Hình học:** một đường kích thước, hai đường gióng vuông góc, hai đầu là gạch chéo 45° hoặc mũi tên. Thường thành **chuỗi** liên tiếp.
- **Chữ:** số nguyên (mm), không đơn vị, đặt giữa và song song đường kích thước ("4650", "4800").
- **Quan hệ:** giá trị ≈ khoảng cách hai đường gióng × mẫu số tỉ lệ. Lệch nhiều → kích thước bị sửa tay (đáng chú ý). Các vế một chuỗi cộng bằng tổng (đã dùng cho bậc thang: 25 × 168 = 4200).
- **Layer gợi ý:** `A-dim`.
- **Dễ nhầm:** số hiệu bản vẽ, số trong bảng.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.6 Cao độ (level) — [PN2]
- **Hình học:** ký hiệu tam giác hoặc ký hiệu cao độ trên đường nằm ngang.
- **Chữ:** số mét có dấu ("+3.600", "±0.000", "FFL +0.200", "SSL +0.150"), kèm nhãn "TẦNG 2", "VỈA HÈ", "MÁI".
- **Quan hệ:** trên mặt đứng và mặt cắt, nhãn và số cùng một đường cao độ. Cùng một tầng phải cùng giá trị trên mọi trang. Chỗ lệch thì ghi nhận (trang 41: +7.800 so với +7.850).
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.7 Trục định vị (grid) — [GT]
- **Hình học:** đường chấm gạch dài (bị xuất thành đoạn rời) xuyên qua mặt bằng. Đầu trục là **vòng tròn** chứa số (trục dọc) hoặc chữ (trục ngang).
- **Quan hệ:** khoảng cách các trục khớp chuỗi kích thước trục.
- **Layer gợi ý:** `A-Axis line`.
- **Dễ nhầm:** vòng tròn ký hiệu chi tiết (3.12).
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.8 Tường (mặt bằng) — [GT]
- **Hình học:** **hai nét song song** cách đều nhau, khoảng cách × tỉ lệ = chiều dày thường gặp (100, 110, 200, 220 mm…). Tường bị cắt thường có **hatch** giữa hai nét. Các đoạn nối nhau tạo mạng kín bao quanh phòng.
- **Quan hệ:** bị ngắt ở chỗ có cửa đi hoặc cửa sổ.
- **Layer gợi ý:** `A-WALL-FULL`, `A-WALL-PATT`.
- **Dễ nhầm:** lan can, bậc thang, mép sàn, nội thất (cũng có nét song song). Phân biệt bằng chiều dày, độ dài và sự liên tục.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.9 Cột — [GT]
- **Hình học:** hình chữ nhật hoặc tròn nhỏ, kín, thường **tô đặc** hoặc hatch. Nằm ở giao trục.
- **Layer gợi ý:** `A-column`.
- **Dễ nhầm:** hộp kỹ thuật, ống đứng.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.10 Cửa đi và cửa sổ — [GT] hình · [PN2] bảng cửa
- **Cửa đi:**
  - **Hình học:** khoảng ngắt trong tường. Cánh là một đoạn thẳng kèm **cung tròn ~90°** chỉ hướng mở. Cửa lùa là các đoạn song song chồng nhau, không có cung.
  - **Chữ:** mã cửa đặt cạnh ("DR-01").
- **Cửa sổ:**
  - **Hình học:** khoảng ngắt trong tường, có 2–4 nét song song **chạy dọc theo tường**, không có cung.
  - **Chữ:** mã "WD-01".
- **Quan hệ:** mã cửa ↔ hàng tương ứng trong **bảng cửa** (kích thước, vật liệu, kính). Bề rộng khoảng ngắt × tỉ lệ ≈ bề rộng trong bảng.
- **Layer gợi ý:** `A-Door`, `A-Window`.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.11 Cầu thang — [PN2] số liệu · [GT] hình
- **Hình học (mặt bằng):** dãy nét song song cách đều (bậc). Có mũi tên chỉ hướng lên và đường ngắt chéo.
- **Chữ:** "LÊN", "XUỐNG", số bậc. Trên PN2, ký hiệu thang có chữ nghiêng ~23,8°.
- **Quan hệ:** chiều cao bậc × số bậc = chiều cao tầng.
- **Dễ nhầm:** lam chắn nắng, sàn gỗ (cũng có nét song song đều).
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.12 Ký hiệu mặt cắt và chi tiết dẫn (callout) — [GT]
- **Mặt cắt:** đường cắt có hai đầu là ký hiệu mũi tên kèm chữ ("C"). Ứng với khung nhìn "MẶT CẮT C-C".
- **Chi tiết dẫn:** vòng tròn chia đôi, trên là số chi tiết, dưới là số bản vẽ. Hoặc mã kiểu "CT-BC" trong khung.
- **Quan hệ:** dẫn tới khung nhìn hoặc trang khác. Đây là cách nối mặt bằng tổng thể với chi tiết phóng to.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.13 Mã ký hiệu vật liệu / hoàn thiện (FC-01, CT-ST…) — [PN2]
- **Chữ:** mã ngắn chữ in + số, thường trong ô ký hiệu (khung chữ nhật, lục giác).
- **Quan hệ:** mã trên hình ↔ hàng trong bảng vật liệu hoàn thiện. Mã **không** được mở rộng như chữ viết tắt.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.14 Vùng hatch (vật liệu bị cắt / bề mặt) — [PN2] số lượng · [GT] phân loại
- **Hình học:** đa giác kín (đường bao) được lấp bằng **mẫu lặp**: nét chéo 45° đều, chấm + tam giác (bê tông), lưới… Đặc trưng của mẫu là **góc** và **khoảng cách** nét lặp. Một số mẫu là ảnh nhúng.
- **Quan hệ:** mẫu ↔ **chú thích hatch** (bảng ký hiệu vật liệu) nếu có. Ghi chú có đường dẫn chạm vùng → tên vật liệu của vùng.
- **Layer gợi ý:** `A-hatch`.
- **Dễ nhầm:** dãy nét song song của thang, lam, sàn gỗ (không có đường bao kín).
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.15 Tên phòng — [GT]
- **Chữ:** tên ("P. NGỦ", "WC", "BẾP"), thường kèm diện tích "m²" hoặc cao độ sàn.
- **Quan hệ:** nằm **bên trong** vùng kín do tường bao → gắn với phòng đó.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

### 3.16 Khác — [GT]
- **Mũi tên chỉ hướng Bắc:** ký hiệu tròn hoặc mũi tên kèm "N" / "B".
- **Keyplan:** sơ đồ thu nhỏ ở góc trang, thường có layer riêng (`xf-keyplan-a|A-keyplan`) hoặc là ảnh.
- **Nội thất và thiết bị vệ sinh:** khối hình lặp lại (giường, bồn cầu, lavabo). Không mang số liệu, cần **tách ra để giảm nhiễu**.
- Đối tác: ☐ Đúng ☐ Cần sửa: ……

## 4. Kiểm chéo độ tin cậy của layer (thuật toán)

1. **Với mỗi layer, code thống kê:** số khối chữ và mẫu chữ; kiểu nét (đoạn thẳng, cung, đa giác kín, mẫu lặp hatch); các trang xuất hiện.
2. **Suy ra vai theo nội dung:**
   - đa số là số mm giữa hai vạch gióng → *kích thước*;
   - đa số là mẫu lặp đều trong đường bao → *hatch*;
   - nhiều cặp nét song song cách đều theo chiều dày tường → *tường*;
   - …
3. **Suy ra vai theo tên** (gợi ý).
4. **So sánh hai vai:**
   - khớp → layer **tin cậy**, dùng để tìm nhanh;
   - lệch → layer **không tin cậy**, chỉ dùng vai theo nội dung;
   - không suy ra được → **chưa rõ**.
5. **Báo cáo:** tỉ lệ layer tin cậy của hồ sơ hiện trên viewer. Tỉ lệ thấp → cả hồ sơ không dựa vào layer.

## 5. Câu hỏi cho đối tác

1. Công ty có **quy ước đặt tên layer** chung không (theo tiêu chuẩn nào)? Các đơn vị thiết kế bên ngoài có theo không?
2. Có **bảng ký hiệu hatch chuẩn** của công ty không (bê tông, gạch, đất, cách nhiệt…)?
3. Ký hiệu **chi tiết dẫn** và **mã vật liệu** (FC-, CT-…) có thống nhất giữa các dự án không?
4. Còn đối tượng nào **thường được kiểm tra** mà file này chưa liệt kê?
