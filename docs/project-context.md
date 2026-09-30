# Ngữ cảnh dự án

## 1. Bài toán

Chủ đầu tư (bộ tiêu chí mẫu là của Novaland — "Công ty CP Tập đoàn Đầu tư Địa ốc No Va") ban hành **bộ tiêu chí chuẩn hóa thiết kế (CHTK)** cho nhà ở thấp tầng. Đơn vị thiết kế (DMD / TVTK) nộp bộ bản vẽ; người kiểm tra phải lật từng trang để đối chiếu với tiêu chí rồi ghi comment lên PDF. MAIN tự động hóa việc đối chiếu này: **đọc được các phần yêu cầu trong bản vẽ và so sánh với tiêu chí đề ra**, kèm bằng chứng vị trí.

Giai đoạn hiện tại là **đánh giá tính khả thi** trên file PDF/CAD rất nặng, đồ họa cao.

## 2. Dữ liệu mẫu thật

| File | Nội dung |
|---|---|
| `D:\Downloads\tieuchuan\TIEU CHI CHTK NHA O THAP TANG_gui CDS.xlsx` | Bộ tiêu chí. Sheet có dữ liệu: **"4 SAO"** (127 dòng, 5 nhóm). Các sheet khác là rác (1 ô) |
| `D:\Downloads\tieuchuan\PN2.DN-Ban ve mau demo test AI.pdf` | Bộ bản vẽ mẫu 48 trang, ~20MB, khổ 1445×1162 pt. Mẫu nhà **SH1**, lô 6×20m, 3 tầng + mái |
| `D:\Downloads\tieuchuan\PN2.DN-Ban ve mau demo test AI - comment check.pdf` | Cùng bộ bản vẽ, **có comment của người kiểm tra** (đám mây đỏ + chữ). Là đáp án mẫu để đo độ chính xác |
| `samples/criteria/ruleset-4sao.json` | JSON bộ tiêu chí do BE sinh từ Excel (bản sao của `D:\Downloads\response_1790518856429.json`) |
| `samples/ground-truth/pn2-dn-reviewer-comments.json` | Comment của người kiểm tra, tự trích bằng cách so chữ giữa hai PDF (29 khối trên 9 trang; **cần người làm sạch** — có khối lẫn ký tự rời) |
| FE `public/mock/PN2-DN-01.pdf`, `D:\Downloads\PN2-DN-01.pdf` | Cùng bộ bản vẽ, dùng cho viewer mock ở FE |

Đặc điểm PDF (đã kiểm chứng, xem `research-log.md`):
- **Vector hoàn toàn**: mỗi trang 1.000–5.000 ký tự trích được kèm tọa độ; 1.600 → 316.000 nét vẽ/trang. Render 1 trang ≈ 0.3 s.
- Các loại trang: mặt bằng kiến trúc tầng 1/2/3/mái (TL 1/50), mặt bằng kích thước, hoàn thiện sàn, trần, hoàn thiện tường, mặt đứng, mặt đứng trích đoạn (1/25), mặt cắt A-A/B-B/C-C, chi tiết cấu tạo (nhiều ô chi tiết trên một trang), mặt bằng thang, bảng thống kê / định vị cửa đi – cửa sổ, keyplan (1/10000).
- **Một trang có nhiều tỉ lệ** (bản vẽ chính 1/50 + keyplan 1/10000 + chi tiết 1/25).
- **Bản vẽ không ghi loại nhà** (chỉ có mã mẫu "SH1"). Loại nhà do người dùng chọn ở form tạo hồ sơ bên FE.

## 3. Bộ tiêu chí (tóm tắt)

5 nhóm: (1) Mặt ngoài công trình — hoàn thiện, lan can, hệ cửa + danh mục kích thước cửa, cote; (2) Kích thước công trình — chiều cao tầng, chiều rộng lọt lòng các phòng; (3) Thang bộ – ramp — rộng/cao bậc, số bậc, độ dốc; (4) Chi tiết cấu tạo điển hình — tường, trát, ron, sàn, mái, sê nô, khe hở 2 nhà, chống mối, chống thấm; (5) Chi tiết hoàn thiện điển hình — trần ngoài nhà, chân tường, ban công, trụ đấu nối.

Theo loại kiểm tra (ước lượng khi đọc, **chưa đếm chính xác**):
- Vật liệu / cấu tạo dạng chữ: ~60%
- Con số trong bảng / cao độ / thang / cửa: ~30%
- Hình học mặt bằng (chiều rộng lọt lòng phòng, kích thước nhà xe): ~6%
- Không kiểm được từ bản vẽ (chống mối định kỳ, vận hành): ~4%

Comment thật của người kiểm tra gần như toàn bộ thuộc loại **so chữ / thông số** (chống thấm, trần thạch cao 9mm, bê tông M200, kính 12.76mm, kích thước cửa…), không phải nhận dạng hình.

## 4. Từ vựng ngành

| Từ | Nghĩa |
|---|---|
| CHTK | Chuẩn hóa thiết kế — bộ tiêu chí của chủ đầu tư |
| DMD / TVTK | Đơn vị thiết kế / tư vấn thiết kế |
| CĐT | Chủ đầu tư |
| TKYT | Thiết kế ý tưởng |
| VE | Value engineering — rà soát tối ưu chi phí |
| BVKC | Bản vẽ kết cấu |
| FFL | Finish floor level — cao độ sàn hoàn thiện |
| SSL | Structural slab level — cao độ sàn kết cấu |
| Cote / cao độ | Cao độ so với mốc ±0.000 (hòn dấu tại vỉa hè) |
| TL 1/50 | Tỉ lệ bản vẽ |
| Lọt lòng / thông thủy | Kích thước tính từ mặt trong kết cấu |
| Kicker | Gờ bê tông chân tường chống thấm |
| Ron âm | Rãnh chìm trang trí / ngắt trên mặt tường |
| Sê nô | Máng thu nước mái |
| Ô fix | Ô kính cố định trên / cạnh cửa |
| Shophouse, Townhouse, Semi Villa, Single Villa, Shop Villa | 5 loại nhà (HouseType) |
