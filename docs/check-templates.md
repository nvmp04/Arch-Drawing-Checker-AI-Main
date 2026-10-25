# Mẫu kiểm tra (check templates) — đặc tả ý nghĩa

> **Trạng thái: bản thảo để thảo luận (2026-10-05).** Người dùng đồng ý ý tưởng "hệ thống có sẵn một số mẫu kiểm tra viết bằng thuật toán cố định"; đặc tả chi tiết bên dưới chưa được duyệt.
> File này mô tả **mỗi mẫu kiểm cái gì, cần biết gì, tìm gì trên bản vẽ, kết luận thế nào** — không mô tả kỹ thuật.

## 0. Vị trí của mẫu kiểm tra trong hệ thống

```
Câu tiêu chí ──(AI diễn giải, tự động)──► Mẫu kiểm tra + thông số ──(thuật toán cố định)──► Kết luận + bằng chứng
                                                ▲
Bản vẽ ──(đọc bản vẽ: mục lục trang, bảng, cao độ, ghi chú…)──┘
```

- **Mẫu kiểm tra là thuật toán cố định, không biết gì về bộ tiêu chí cụ thể.** Nó nhận "thông số" (phạm vi, đối tượng, thuộc tính, yêu cầu) và trả kết luận. Không có mẫu nào chứa tên một rule, mã rule hay câu chữ của một file tiêu chí (D-18).
- **Việc chọn mẫu và điền thông số cho từng dòng tiêu chí do AI làm tự động** (ý đồ của đối tác: không duyệt thủ công). AI không chắc → dòng đó thành **Cần kiểm tra**, không đoán.
- Sửa câu tiêu chí → AI diễn giải lại → thông số đổi → kết luận đổi theo (phép thử bắt buộc, AGENTS.md nguyên tắc 10).

## 1. Khái niệm chung cho mọi mẫu

| Khái niệm | Nghĩa | Ví dụ |
|---|---|---|
| **Phạm vi** | bộ phận / vị trí của công trình mà tiêu chí nói tới | sàn mái, ban công, tầng 1, cửa đi, cầu thang, trần ngoài nhà |
| **Đối tượng** | thứ cụ thể cần kiểm trong phạm vi | lớp chống thấm, bậc thang, ô cửa, tấm trần |
| **Thuộc tính** | đặc điểm của đối tượng được đem ra so | chiều cao, độ dày, mác, vật liệu, gốc chống thấm, kích thước |
| **Yêu cầu** | điều tiêu chí đòi hỏi về thuộc tính | ≥ 1.1 m · thuộc {17, 18, 21} · phải có · không được có · là thạch cao hoặc silicat |
| **Bằng chứng** | chỗ trên bản vẽ (trang + vùng + chữ / số trích được) làm căn cứ kết luận | trang 5, dòng "LỚP CHỐNG THẤM GỐC PU…" |

### Bốn trạng thái (theo đối tác) và quy tắc chung

| Trạng thái | Khi nào | Ghi chú |
|---|---|---|
| **Đạt** | tìm thấy đúng đối tượng trong đúng phạm vi, thuộc tính thỏa yêu cầu | |
| **Không đạt** | tìm thấy, thuộc tính **ghi rõ** và trái yêu cầu | chỉ khi độ tin cậy ≥ 0.8 (nguyên tắc 7) |
| **Cảnh báo** | có dấu hiệu trái yêu cầu nhưng chưa chắc: tin cậy < 0.8, giá trị ở nhóm khác của danh mục, "hoặc tương đương", lệch rất nhỏ | không được dùng thay cho Không đạt khi đã chắc |
| **Cần kiểm tra** | hệ thống không đủ căn cứ để kết luận: bản vẽ không ghi thuộc tính, không tìm thấy đối tượng, tiêu chí tham chiếu ngoài bản vẽ / chủ quan, AI không diễn giải được câu | luôn kèm **trang / vùng nên xem** nếu định vị được |

Quy tắc xuyên suốt:
1. **Không tìm thấy ≠ vi phạm.** Không thấy đối tượng → Cần kiểm tra (trừ mẫu "Không được có", xem M4).
2. **Không ghi ≠ ghi sai.** Bản vẽ có đối tượng nhưng không ghi thuộc tính → Cần kiểm tra, nói rõ thiếu gì.
3. **Độ tin cậy của kết luận = mức thấp nhất** của: diễn giải câu tiêu chí, xác định phạm vi trên bản vẽ, trích dữ liệu.
4. **Một dòng tiêu chí có thể gồm nhiều yêu cầu** (vd. "Vữa M75 dày min 20 mm, dốc min 1.5%" = 3 yêu cầu). Kết luận của dòng: có yêu cầu Không đạt → Không đạt; còn yêu cầu Cần kiểm tra → Cần kiểm tra; tất cả Đạt → Đạt. Lý do liệt kê từng yêu cầu.
5. Cùng một dữ liệu ghi ở nhiều trang mà **không thống nhất** → nêu ra trong lý do, hạ tin cậy.

## 2. Cổng áp dụng (trước mọi mẫu)

Không phải mẫu kiểm tra mà là bước quyết định **dòng tiêu chí này có áp dụng cho hồ sơ này không**. Đây là phần "AI tự hiểu tiêu chí nào áp dụng được".

- **Cần biết từ tiêu chí:** điều kiện áp dụng — loại nhà ("Shophouse, Shop Villa"), điều kiện có / không ("nếu có hầm", "đối với ban công diện tích ≥ 6 m²"), biến thể ("mái bằng" / "mái ngói"), vùng ("vùng biển"), điều kiện ngoài bản vẽ ("nêu trong Báo cáo NCKT").
- **Cần biết từ bản vẽ — đặc điểm hồ sơ:** mẫu nhà, số tầng, có hầm / tum, loại mái, có hồ bơi / bồn hoa / thang máy / ban công / mái đón…, vùng (nếu ghi).
- **Kết luận:**
  - điều kiện **không thỏa** (vd. "nếu có hầm" mà hồ sơ không có hầm) → dòng **không đưa vào checklist** (ghi lý do trong báo cáo phụ);
  - điều kiện **thỏa** → chuyển sang mẫu kiểm tra;
  - điều kiện **không xác định được từ bản vẽ** (vùng, Báo cáo NCKT) → vẫn kiểm, nhưng kết luận tối đa là **Cần kiểm tra**, ghi "tùy điều kiện …";
  - dòng **không thuộc phạm vi bản vẽ** (thủ tục bàn giao, khuyến cáo vận hành: "khuyến cáo chống mối định kỳ 6 tháng/lần") → **không đưa vào checklist**, liệt kê ở báo cáo phụ "tiêu chí ngoài phạm vi bản vẽ".

## 3. Danh mục mẫu kiểm tra

Ví dụ lấy từ bộ 4 SAO chỉ để minh họa ý nghĩa — **không** phải bảng tra trong code.

### M1 · So ngưỡng số

- **Ý nghĩa:** một đại lượng đo được của đối tượng phải nằm trong ngưỡng.
- **Tiêu chí cần cho biết:** phạm vi + đối tượng + đại lượng, phép so (≥, ≤, =, trong khoảng), giá trị + đơn vị.
- **Tìm trên bản vẽ:** con số **ghi** trên bản vẽ cho đại lượng đó (cao độ, kích thước ghi, chú thích "18 BẬC x 168"), hoặc **tính từ các số ghi** (chiều cao tầng = hiệu hai cao độ). Không đo bằng thước trên hình (tỉ lệ có thể sai).
- **Kết luận:** thỏa → Đạt (sát ngưỡng thì ghi "đạt sát ngưỡng") · trái → Không đạt · không tìm được số → Cần kiểm tra · nhiều chỗ ghi khác nhau → lấy số đông, nêu chỗ khác, hạ tin cậy.
- **Bằng chứng:** vị trí các con số đã dùng để tính.
- **Ví dụ:** "Chiều cao tầng 1 ≥ 4.0 m" · "Chiều cao bậc ≤ 180 mm" · "Lan can ≥ 1.1 m" · "Độ dốc hầm ≤ 18%".
- **Lưu ý:** đại lượng tính gián tiếp phải tự kiểm chéo khi được (số bậc × chiều cao bậc = chiều cao tầng) — vừa xác định đúng con số, vừa tăng tin cậy.

### M2 · Thuộc danh mục

- **Ý nghĩa:** giá trị của đối tượng phải là **một trong các giá trị** tiêu chí liệt kê.
- **Tiêu chí cần cho biết:** phạm vi + đối tượng + thuộc tính, danh sách giá trị cho phép (có thể chia nhóm: cửa đi mở / lùa, cửa sổ…).
- **Tìm trên bản vẽ:** giá trị của **từng** đối tượng thuộc phạm vi (mỗi cửa trong bảng thống kê cửa, số bậc mỗi tầng).
- **Kết luận (mỗi đối tượng một kết quả):** khớp đúng nhóm → Đạt · khớp nhưng ở nhóm khác → Cảnh báo (có thể phân loại đối tượng sai) · không khớp → Không đạt, nêu mục gần nhất · không xác định được nhóm của đối tượng → so với mọi nhóm, tối đa Cảnh báo.
- **Bằng chứng:** vị trí đối tượng + giá trị của nó.
- **Ví dụ:** danh mục kích thước cửa (1.4.x) · "Số bậc ∈ {17, 18, 21, 22, 25}".

### M3 · Phải có thành phần (kèm thông số)

- **Ý nghĩa:** trong phạm vi, phải có một thành phần / lớp cấu tạo, và thành phần đó phải đạt các thông số kèm theo.
- **Tiêu chí cần cho biết:** phạm vi + thành phần; danh sách thông số kèm theo, mỗi thông số là một yêu cầu nhỏ thuộc loại M1 (số: dày ≥ 40 mm, cuộn lên 300 mm, dốc ≥ 1.5%), M5 (vật liệu / loại: gốc PU, mác M200) hoặc quy cách (thép D4@250–300).
- **Tìm trên bản vẽ:** mô tả cấu tạo của đúng phạm vi — ưu tiên bảng (bảng thống kê cấu tạo sàn: vị trí → các lớp), rồi ghi chú lớp cấu tạo trên mặt cắt / chi tiết của phạm vi đó.
- **Kết luận:** không thấy mô tả cấu tạo của phạm vi → Cần kiểm tra · có mô tả nhưng **không có** thành phần → Không đạt (mô tả cấu tạo được coi là liệt kê đủ các lớp) · có thành phần → xét từng thông số: ghi trái → Không đạt; không ghi → Cần kiểm tra ("không ghi độ dày"); đều thỏa → Đạt.
- **Bằng chứng:** dòng mô tả thành phần (hoặc cả mô tả cấu tạo khi thiếu thành phần).
- **Ví dụ:** "Lớp chống thấm gốc PU, cuộn lên vách 300 mm" · "Bê tông đá mi M200, thép D4@250-300, dày min 40 mm" · "Lớp kết cấu sàn".

### M4 · Không được có thành phần / hạng mục

- **Ý nghĩa:** trong phạm vi, một thành phần / hạng mục **không được thực hiện**.
- **Tiêu chí cần cho biết:** phạm vi + thành phần bị cấm (+ ngoại lệ nếu có: "ngoại trừ công trình có hầm").
- **Tìm trên bản vẽ:** mọi chỗ thể hiện thành phần đó trong phạm vi — dòng cấu tạo, ghi chú, **tên trang** (vd. có hẳn trang "MẶT BẰNG CHỐNG MỐI").
- **Kết luận:** có thể hiện → Không đạt · ngoại lệ thỏa (đặc điểm hồ sơ) → không áp dụng · **không thấy** → Đạt nhưng tin cậy thấp hơn (vắng bằng chứng không chắc bằng có bằng chứng) — nếu không đọc được mô tả cấu tạo của phạm vi thì Cần kiểm tra.
- **Bằng chứng:** các chỗ thể hiện thành phần bị cấm (tối đa vài chỗ mỗi trang).
- **Ví dụ:** "Không bàn giao sàn bê tông tầng 1" · "Lớp hoàn thiện: không thực hiện" · "Không xử lý chống mối" · "Không chống thấm chân tường rào" · "Không trát vữa (cấu kiện trong nhà)".
- **Lưu ý:** phủ định nằm trong câu tiêu chí; AI diễn giải phải nhận ra để chọn M4 thay vì M3 — đúng ca đã gây sự cố D-18.

### M5 · Vật liệu / quy cách thuộc loại cho phép

- **Ý nghĩa:** đối tượng phải làm bằng một trong các loại vật liệu / quy cách tiêu chí nêu.
- **Tiêu chí cần cho biết:** phạm vi + đối tượng; các loại cho phép (mỗi loại có thể kèm thông số: "thạch cao chống ẩm 9 mm", "silicat 6 mm"); có "hoặc tương đương" hay không.
- **Tìm trên bản vẽ:** vật liệu ghi cho đối tượng trong phạm vi — bảng vật liệu hoàn thiện (mã + mô tả, kèm vị trí mã trên mặt bằng), bảng thống kê cửa, ghi chú.
- **Kết luận:** vật liệu thuộc loại cho phép → xét thông số kèm theo như M3 (thiếu → Cần kiểm tra) · **khác loại** → Không đạt · khác loại nhưng tiêu chí có "hoặc tương đương" → Cảnh báo (cần người xác nhận tương đương) · không ghi vật liệu ("TRẦN ĐỂ THÔ") → Cần kiểm tra.
- **Bằng chứng:** dòng bảng / ghi chú vật liệu; nếu có, vị trí mã vật liệu trên mặt bằng.
- **Ví dụ:** "Trần ngoài nhà: tấm silicat 6 mm hoặc thạch cao chống ẩm 9 mm" · "Kính cường lực 8 mm" · "Ngói sóng SCG / hoặc tương đương" · "Sơn nước ngoại thất".
- **Lưu ý:** nhận ra "cemboard" là **một loại tấm khác**, không phải thạch cao, là việc của AI (hiểu nghĩa vật liệu), không phải danh sách viết tay.

### M6 · Tham chiếu ngoài bản vẽ

- **Ý nghĩa:** tiêu chí giao việc xác định cho tài liệu khác: "theo PD CĐT", "theo Danh mục vật tư", "theo thiết kế được duyệt", "xem BVKC", "theo phân cấp sao".
- **Kết luận:** luôn **Cần kiểm tra**; hệ thống chỉ **định vị** chỗ trên bản vẽ có liên quan để người xem đối chiếu.
- **Ví dụ:** "Lớp hoàn thiện theo phân cấp sao" · "Phụ kiện theo Danh mục vật tư" · "Kết cấu seno – chi tiết xem BVKC".

### M7 · Đánh giá chủ quan

- **Ý nghĩa:** tiêu chí cần con mắt người: thẩm mỹ, "đơn giản", "tránh lồi gờ".
- **Kết luận:** luôn **Cần kiểm tra** + vùng liên quan (Q-08).
- **Ví dụ:** "Phào chỉ đơn giản theo TKYT" · "Úp viên ngói góc đảm bảo thẩm mỹ" · "Không dùng ống thoát tràn nổi gây mất thẩm mỹ".

### Không mẫu nào khớp

AI không chọn được mẫu đủ chắc → **Cần kiểm tra** + trang liên quan (nếu định vị được) + lý do "chưa tự kiểm được dòng này". Đây là trạng thái bình thường, không phải lỗi.

## 4. Định vị — dùng chung cho mọi dòng

Mọi dòng trong checklist, kể cả Cần kiểm tra, cố gắng kèm **trang / vùng nên xem**: từ phạm vi của tiêu chí tìm tới trang (mục lục từ khung tên), rồi tới bảng / hình trong trang (mục lục tên bảng, tên hình). Định vị sai chỉ làm người xem mất thêm thời gian, không sinh kết luận sai — nên đây là chỗ dùng AI an toàn nhất.

## 5. Phần nào là AI, phần nào là thuật toán cố định

| Việc | Loại | Ghi chú |
|---|---|---|
| Đọc bản vẽ: mục lục trang, bảng, cao độ, ghi chú, đặc điểm hồ sơ | thuật toán cố định | không phụ thuộc bộ tiêu chí |
| Cổng áp dụng: điều kiện trong câu tiêu chí ↔ đặc điểm hồ sơ | **AI** | |
| Câu tiêu chí → chọn mẫu M1–M7 + điền thông số | **AI** | không chắc → Cần kiểm tra |
| Khớp tên giữa tiêu chí và bản vẽ (phạm vi, vật liệu, viết tắt "BTCT") | **AI** | |
| Định vị trang / vùng | **AI** | an toàn nhất |
| Thực thi mẫu M1–M7 và quy tắc trạng thái | thuật toán cố định | file này |
