# Danh mục checker

Mỗi checker kiểm một loại tiêu chí CHTK. File này ghi **công năng** (kiểm cái gì), **cách hiện thực** (lấy dữ liệu ở đâu, kết luận bằng gì) và **mức phụ thuộc vào file tiêu chí** của từng checker. Cập nhật mỗi khi thêm / sửa / gỡ checker.

- Code: `src/drawing_checker/features/rules/checkers.py` · bảng rule → checker: `rules/plan_table.py` · trích dữ liệu: `extraction/service.py`.
- Kết quả đo trên bộ mẫu PN2 (shophouse, bộ tiêu chí 4 SAO): `research-log.md` §7.
- **Phương pháp** hiện có một loại: **rule engine** (luật viết tay, không model AI).

## 0. Điều phải biết trước: checker đang gắn với file tiêu chí như thế nào

Một checker có hai nửa:

| Nửa | Là gì | Phụ thuộc file tiêu chí? |
|---|---|---|
| **Đọc bản vẽ + so sánh** (trích cao độ, bậc thang, bảng cửa; so ngưỡng) | thuật toán cố định | Không |
| **Biết dòng tiêu chí nào cần kiểm cái gì** (`plan_table.py`) | **bảng viết tay theo mã rule của bộ 4 SAO** — không sinh ra khi chạy, không phải thuật toán | **Có** |

Hệ quả khi nạp bộ tiêu chí khác: rule **trùng mã** vẫn được nối vào checker cũ (ngưỡng thì đọc từ rule mới, nhưng "đo cái gì" là cách hiểu cũ); rule **mã khác** → "chưa hỗ trợ". Bước sinh kế hoạch kiểm tra từ câu tiêu chí bất kỳ (**diễn giải luật — Q-07**) chưa có; đó là phần ngữ nghĩa, cần AI.

**Quy tắc (D-18, 2026-10-02): không viết cứng ngữ nghĩa của câu tiêu chí vào code.** Tiêu chí dạng chữ / vật liệu / cấu tạo / "không thực hiện…" chỉ được kiểm khi có bước diễn giải sinh kế hoạch từ chính câu tiêu chí. Bốn checker vi phạm quy tắc này đã bị gỡ (xem §2).

## 1. Đang hoạt động — 6 checker tiêu chí số

Độ phủ: **35 / 223** dòng tiêu chí áp dụng cho shophouse (16%).

| # | Checker | Tiêu chí | Phương pháp | Đọc từ rule | Viết cứng theo mã rule |
|---|---|---|---|---|---|
| 1 | Chênh cote tầng 1 – vỉa hè | 1.8 | rule engine — so ngưỡng | ngưỡng (`operator`, `value`), loại nhà | "rule 1.8 = đo chênh cote tầng 1 – vỉa hè" |
| 2 | Chiều cao tầng | 2.1.1 – 2.1.4 | rule engine — so ngưỡng | ngưỡng, loại nhà | rule nào ứng với tầng nào |
| 3 | Chiều cao bậc thang | 3.4 | rule engine — so ngưỡng + khớp chéo | ngưỡng | "rule 3.4 = chiều cao bậc" |
| 4 | Số bậc thang mỗi tầng | 3.5 | rule engine — thuộc danh sách | danh sách số bậc | "rule 3.5 = số bậc" |
| 5 | Chiều rộng bậc thang | 3.2 | rule engine — so ngưỡng | ngưỡng | "rule 3.2 = chiều rộng bậc"; ghi chú điều kiện NCKT |
| 6 | Danh mục kích thước cửa (cửa đi mở / lùa, cửa sổ mở / lùa / cố định) | 1.4.1 – 1.4.5 | rule engine — tra danh mục | các kích thước cho phép (đọc từ câu tiêu chí) | rule nào là loại cửa nào |

Sáu checker này **vẫn phụ thuộc mã rule** của bộ 4 SAO ở cột cuối. Chúng được giữ vì là tiêu chí số: giá trị so sánh lấy từ trường có cấu trúc của rule, không phải từ việc hiểu câu chữ. Có gỡ nốt hay không: chờ người dùng quyết.

### 1. Chênh cote tầng 1 – vỉa hè (1.8) — `ground_floor_above_sidewalk`

- **Công năng:** cao độ sàn tầng 1 phải cao hơn vỉa hè tối thiểu theo loại nhà (shophouse ≥ 150 mm, townhouse ≥ 450 mm…).
- **Dữ liệu:** cao độ ghi trên mặt đứng / mặt cắt — nhãn ("TẦNG 1", "VỈA HÈ") với con số ngay bên dưới ("+0.250", "±0.000").
- **Cách làm:** ghép nhãn với số theo vị trí (số nằm dưới nhãn ≤ 20 pt) → gom cùng nhãn trên mọi trang, lấy số đông, ghi chú nếu có trang ghi khác → lấy hiệu hai cao độ → so ngưỡng của rule.
- **Tin cậy:** 0.95; hạ còn 0.9 / 0.7 khi các trang ghi không thống nhất.
- **PN2:** +0.250 − ±0.000 = 250 mm → đạt.

### 2. Chiều cao tầng (2.1.1 hầm · 2.1.2 tầng 1 · 2.1.3 tầng 2–3 · 2.1.4 tum) — `storey_height`

- **Công năng:** chiều cao mỗi tầng ≥ ngưỡng (vd. tầng 1 ≥ 4.0 m, tầng 2–3 ≥ 3.4 m).
- **Dữ liệu:** cùng bộ cao độ của checker 1 (dùng chung, trích một lần).
- **Cách làm:** chiều cao tầng = cao độ sàn tầng trên − cao độ sàn tầng này; tầng trên cùng tính tới cao độ "MÁI". Nhãn "TẦNG n" trùng cao độ mái thì coi là mái. Tầng hầm / tum không có nhãn → "không thấy dữ liệu" (tiêu chí chỉ áp dụng nếu có).
- **Tin cậy:** 0.95; tầng trên cùng 0.85 (giả định tính tới mái).
- **PN2:** tầng 1 = 4200 → đạt; tầng 2, 3 = 3400 → đạt sát ngưỡng, kèm cờ "trang 41 ghi +7.800 thay vì +7.850".
- **Giới hạn:** chỉ dùng số ghi, không đo hình (tỉ lệ bản vẽ có thể sai).

### 3. Chiều cao bậc thang (3.4) — `stair_riser`

- **Công năng:** chiều cao một bậc ≤ 180 mm.
- **Dữ liệu:** ghi chú vế thang dạng "18 BẬC x 168=3024".
- **Cách làm:** ghi chú "N BẬC x a" có thể là chiều cao bậc hoặc chiều rộng bậc — **không đoán theo giá trị**. Các vế cùng trị số trong một chuỗi kích thước cộng lại bằng chiều cao một tầng (25 × 168 = 4200) thì đó là chiều cao bậc của tầng ấy → so ngưỡng với bậc cao nhất.
- **Tin cậy:** 0.95 (hai nguồn số liệu độc lập khớp chéo).
- **PN2:** 168 mm (tầng 1→2), 162 mm (tầng 2→3) → đạt.
- **Giới hạn:** thiếu cao độ tầng thì không xác định được → "không thấy dữ liệu".

### 4. Số bậc thang mỗi tầng (3.5) — `stair_count`

- **Công năng:** tổng số bậc lên một tầng phải thuộc danh sách {17, 18, 21, 22, 25}.
- **Dữ liệu / cách làm:** cộng số bậc các vế đã nhận ra ở checker 3 theo từng tầng → kiểm thuộc danh sách.
- **Tin cậy:** 0.95.
- **PN2:** 25 và 21 bậc → đạt.

### 5. Chiều rộng bậc thang (3.2) — `stair_tread`

- **Công năng:** chiều rộng mặt bậc ≥ 250 mm (biến thể ≥ 280 mm khi "được nêu trong Báo cáo NCKT").
- **Dữ liệu / cách làm:** các vế "N BẬC x a" **không** khớp chiều cao tầng nào (loại trừ sau checker 3) là vế ghi chiều rộng bậc → so ngưỡng với trị số nhỏ nhất. Biến thể có điều kiện không kiểm được từ bản vẽ → "chờ người".
- **Tin cậy:** 0.85 (suy ra bằng loại trừ).
- **PN2:** 250 mm → đạt sát ngưỡng; biến thể 280 → chờ người.

### 6. Danh mục kích thước cửa (1.4.1 – 1.4.5) — `opening_catalog`

Năm rule là năm nhóm của **một danh mục**: 1.4.1 cửa đi mở · 1.4.2 cửa đi lùa · 1.4.3 cửa sổ mở · 1.4.4 cửa sổ lùa · 1.4.5 cửa sổ cố định. Một checker xét chung cả năm.

- **Công năng:** mỗi cửa trong bảng thống kê cửa phải có kích thước (cao × rộng) nằm trong danh mục CHTK của đúng loại cửa.
- **Dữ liệu:** bảng thống kê cửa (PN2 trang 47–48): mỗi cột một cửa — mã ("DR-01", "WD-01"), kích thước ("4800w x 3000h"), mô tả loại ("Cửa Khung nhôm trượt…"), vị trí.
- **Cách làm:** chia cột theo vị trí chữ kích thước → lấy mã, mô tả, vị trí trong cột. Phân loại: cửa đi / cửa sổ theo mã và mô tả; kiểu mở theo từ khóa ("trượt", "lùa" → lùa; "mở", "bật" → mở; "cố định", "vách" → cố định). Danh mục cho phép đọc từ các dòng tiêu chí ("2800 x 1100/1200mm"). Mỗi cửa một kết quả, gắn với mục danh mục gần nhất.
- **Kết luận:** khớp đúng nhóm → đạt (0.9) · có trong danh mục nhưng ở nhóm khác → cảnh báo (0.75) · không có → không đạt (0.9; chỉ 0.75 khi không xác định được loại cửa).
- **PN2:** DR-01…06, WD-01: 7/7 không đạt — trùng comment người kiểm tra (trang 31, 47).
- **Giới hạn:** mục không có mã (cửa thăm mái) bỏ qua; chỉ nhận dạng bảng cửa kiểu "NNNNw x NNNNh".



## 2. Đã gỡ ngày 2026-10-02 — checker ngữ nghĩa viết cứng theo file tiêu chí

**Sự cố:** người dùng sửa câu tiêu chí 4.2.1 dòng 0 từ "Không bàn giao sàn bê tông tầng 1…" thành "Sàn bê tông cốt thép" / "Sàn btct" (nghĩa ngược lại). Checker vẫn kết luận "không đạt — tiêu chí yêu cầu không thực hiện sàn bê tông tầng 1", vì nó không đọc câu tiêu chí: cách hiểu từng dòng nằm sẵn trong `plan_table.py`, do AI viết tay khi đọc bộ 4 SAO. Đó là làm thay phần ngữ nghĩa bằng tay cho đúng một file — sai nguyên tắc dự án (bộ tiêu chí thay đổi theo file nạp vào).

| Checker đã gỡ | Tiêu chí | Phần viết cứng |
|---|---|---|
| Vật liệu trần ngoài nhà (`exterior_ceiling`) | 5.1.1, 5.1.2 | rule nào là "trần ngoài nhà", dòng nào là trát / sơn; từ điển vật liệu, từ khóa "ngoài nhà" |
| Cấu tạo sàn theo vị trí (`floor_assembly`) | 4.2.1, 4.2.4, 4.2.5, 4.5.3, 4.5.5 | **toàn bộ**: vị trí, lớp cần tìm, có / không, mác, độ dày, thép, gốc chống thấm |
| Chống mối (`forbidden_topic`) | 4.4.1 | **toàn bộ**: "không được có chống mối" |
| Kính cửa (`opening_glass`) | 1.4 | dòng nào là cửa đi / cửa sổ (độ dày kính thì đọc từ câu tiêu chí) |

Gỡ cùng: `rules/materials.py`, các dòng tương ứng trong `plan_table.py`, phần trích ghi chú trần / ghi chú chống mối / gợi ý "ngoài nhà". Các dòng tiêu chí trên nay trả **"chưa hỗ trợ"** (có test bảo vệ: `test_semantic_lines_are_unsupported_not_hardcoded`).

Kết quả từng đạt trên PN2 trước khi gỡ (research-log §8, §10) chỉ chứng minh nửa "đọc bản vẽ + so sánh" làm được; **không** chứng minh hệ thống hiểu tiêu chí.

## 3. Giữ lại — đọc bảng trên bản vẽ (không phụ thuộc file tiêu chí)

Thuật toán cố định, chỉ đọc bản vẽ; chưa có checker nào dùng. Là đầu vào cho bước diễn giải + kiểm tra sau này.

| Trích xuất | Kết quả trên PN2 |
|---|---|
| Bảng vật liệu hoàn thiện (`extract_finish_tables`) — mã + mô tả + bề mặt theo tiêu đề bảng | 108 dòng (80 tường, 28 trần), trang 3, 22–36, 43, 44 |
| Bảng thống kê cấu tạo sàn (`extract_floor_assemblies`) — mã, vị trí, nhóm tầng, từng lớp cấu tạo | 8 dòng / 38 lớp, trang 5, 37–39 |
| Độ dày kính trong bảng thống kê cửa (`glass_mm`) | DR-01…06: 8 mm, WD-01: 6 mm |
| Ingest: chuẩn hóa NFC, giải mã font VNI, nối dòng chữ bị tách (research-log §9) | toàn bộ 48 trang |

## 4. Việc tiếp theo cho tiêu chí chữ / vật liệu

Không viết thêm checker loại này cho tới khi chốt **bước diễn giải luật (Q-07)**: câu tiêu chí bất kỳ → kế hoạch kiểm tra, chạy một lần khi nạp bộ tiêu chí. Các hướng đã nêu với người dùng (chưa chốt): AI local diễn giải · AI đề xuất + người duyệt · người khai báo hoàn toàn.

## 5. AI kiểm dòng tiêu chí (Claude) — `semantic.SemanticService` (D-22, 2026-10-09, mặc định TẮT)

Không phải checker viết tay: kiểm **mọi dòng rule engine chưa hỗ trợ** (chữ, vật liệu, cấu tạo, điều kiện áp dụng).

| Phần | Đọc từ rule / bản vẽ | Viết cứng trong code |
|---|---|---|
| Câu tiêu chí, mã, đề mục, giá trị chuẩn | gửi **nguyên văn** mỗi lần gọi | không |
| Nghĩa câu tiêu chí, chọn mẫu M1–M7, phạm vi | **AI** suy ra mỗi lần | không (phép thử D-18: `test_criterion_text_is_sent_verbatim…`) |
| Chữ trên bản vẽ + mã khối, khung tên, bảng viết tắt | đọc từ PDF (`semantic/digest.py`) | quy tắc trình bày: lược khối chỉ có số, chia vùng XY-cut |
| Cách làm việc: cổng áp dụng, mô tả M1–M7, 4 trạng thái, quy tắc trích dẫn | — | prompt hệ thống (`semantic/service.py`), chung cho mọi bộ tiêu chí |
| Hậu kiểm: mã khối phải tồn tại, M6/M7 → Cần kiểm tra, không bằng chứng → Cần kiểm tra, M4 vắng mặt → Đạt ≤ 0.6 | — | code (`interpret_response`) |

Kết quả có tiền tố `[AI · Mx]` trong lý do. Chi phí mỗi lần chạy hiện ở tab "Kiểm tra". Chưa đo độ chính xác — chờ người dùng chạy `scripts/run_ai_eval.py --live` với file đáp án.
