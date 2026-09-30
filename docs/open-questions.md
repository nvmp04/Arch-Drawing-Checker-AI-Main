# Câu hỏi đang bỏ ngỏ

Người dùng yêu cầu (2026-09-27): **không đào sâu nữa, để ngỏ.** Không tự quyết các mục dưới đây; khi người dùng quay lại thì hỏi. Chốt được mục nào → chuyển sang `decisions.md`.

| # | Vấn đề | Hiện trạng / đề xuất đã nêu |
|---|---|---|
| Q-01 | **Hệ tọa độ polygon** | BE/FE đã có quy ước `boundingBox` **% 0–100 của trang đang hiển thị (đã áp /Rotate), gốc trên-trái**. Đề xuất: đỉnh polygon dùng cùng quy ước % (khung MAIN đã viết theo hướng này). Trong phiên từng đề xuất đơn vị point PDF — **chưa chốt** |
| Q-02 | **Loại nhà của bản vẽ** | Bản vẽ không ghi loại nhà; người dùng "chưa rõ vùng này". Form tạo hồ sơ ở FE **đã có ô chọn loại nhà** và BE gửi `houseType` trong dispatch → có thể đã giải quyết bằng người dùng chọn; cần xác nhận |
| Q-03 | Chuẩn hóa `value` của rule (`"1.1m"`, `"2.8 x 5.6m"`, `"18%"`, `"1.2m - 2.6m"`) | Đề xuất: MAIN tự parse (vì phần diễn giải luật nằm ở MAIN). Chưa chốt ai làm |
| Q-04 | Rule biến thể `code: null` | Đề xuất: định danh bằng `id` + `parentCode` (BE ADR-17 cũng hướng vậy) |
| Q-05 | Có file DWG gốc không | Người dùng: **khả năng là không**. **Cập nhật 2026-09-28:** PDF mẫu đã mang sẵn 378 layer CAD trên cả chữ lẫn nét (research-log §6) → phần lớn lợi ích của DWG đã có. Còn mở: quy ước tên layer có ổn định giữa các đơn vị thiết kế không; block/thuộc tính thì PDF không có |
| Q-06 | Số bộ bản vẽ đã kiểm tra (kèm comment) xin được | **Chưa rõ.** Quyết định khi nào train được model; hiện chỉ có 1 bộ (~29 khối comment) |
| Q-07 | Bước **diễn giải luật** tách riêng + người duyệt | Đề xuất: endpoint riêng, chạy 1 lần/bộ rules, lưu theo `rule.id` + hash, người sửa được. Hoãn cùng `checkType` |
| Q-08 | Loại "phán đoán chủ quan" | Đề xuất: giữ, MAIN chỉ khoanh vùng liên quan và trả `pending`, không phán quyết. Người dùng nghĩ có thể bỏ |
| Q-09 | `severity` trong kết quả | BE `RawFindingDto` bắt buộc `severity`; MAIN không có cơ sở suy. Đề xuất: BE tự gán theo rule, hoặc MAIN gửi mặc định. (BE ADR-05 cũng liệt kê câu hỏi này) |
| Q-10 | Kết quả theo `requirementLine` vs Finding của BE theo rule × trang | Cần BE thêm chỉ số dòng / nhiều bằng chứng. Xem `integration-contract.md` |
| ~~Q-11~~ | Xác thực BE → MAIN | **Đã chốt → D-13** (`Authorization: Bearer`) |
| Q-12 | Model cụ thể cho từng phần (bge-m3, PhoBERT, GNN trên nét vẽ…) | Chỉ là định hướng; chọn khi có dữ liệu và đo được |
