# Đưa hệ thống lên mạng có kiểm soát — kế hoạch và tiến độ (cả 3 repo)

> File theo dõi chung cho FE · BE · MAIN, cập nhật sau mỗi bước. Quyết định: D-21 (hạ tầng), D-20 (vòng duyệt làm dữ liệu huấn luyện). Người dùng là chủ cả 3 repo và cho AI toàn quyền sửa FE / BE (2026-10-08).

## Yêu cầu của người dùng (2026-10-08)

1. Web online; PDF có nơi lưu để FE render.
2. Đối tác duyệt hồ sơ online trên máy họ; dữ liệu duyệt (để huấn luyện) về **cloud của người dùng**. Giới hạn ~**10 bộ hồ sơ khác nhau** để nằm trong gói miễn phí.
3. **Không lưu PDF trùng nội dung** (nhận ra bằng mã băm, kể cả khác tên). Tạo hồ sơ với file trùng → BE **không gọi MAIN**, trả cảnh báo; FE báo trùng, hỏi có muốn kiểm tra lại không, xác nhận thì đưa tới đúng hồ sơ cũ.
4. Cùng một bộ hồ sơ kiểm nhiều lần phải cho kết quả **nhất quán** (đại cục).
5. **Ủ** (thiết kế trước, làm ở phase sau): kiểm tra lại **bản sửa** — tập trung vào lỗi đã có và phần đã thay đổi, tiết kiệm thời gian và chi phí.

## Hạ tầng đã chốt (D-21)

| Thành phần | Chọn | Gói miễn phí (tra cứu 2026-10-08) |
|---|---|---|
| Máy chạy FE + BE + MAIN | **Oracle Cloud Always Free** (ARM) — không tạo được thì VPS trả phí nhỏ | 4 nhân / 24 GB (có tin đã giảm còn 2 / 12, áp dụng chưa nhất quán), 200 GB đĩa |
| Cơ sở dữ liệu | **Neon Postgres** | 0,5 GB, 100 giờ tính toán / tháng, ngủ sau 5 phút không dùng, khôi phục 6 giờ |
| Lưu PDF + dữ liệu huấn luyện ("cloud của tôi") | **Cloudflare R2** của người dùng | 10 GB, không tính phí tải ra |
| Kiểm soát truy cập | **Cloudflare Access** + **Cloudflare Tunnel** | ≤ 50 người dùng; không mở cổng máy chủ ra Internet |

Đã loại: Vercel Hobby (cấm dùng thương mại), Supabase free (tự dừng sau 1 tuần không dùng), máy cá nhân (phải bật liên tục).

Ước lượng dung lượng: PDF mẫu ~20 MB → 10 bộ ~200 MB (R2 dư sức); dữ liệu bảng của 10 bộ ≪ 0,5 GB.

## Các giai đoạn

| # | Việc | Repo | Trạng thái |
|---|---|---|---|
| 1 | BE có CSDL thật (Drizzle + Postgres; dev / test dùng PGlite, production dùng Neon) cho hồ sơ + tiến trình | BE | ✅ 2026-10-08 (BE ADR-03, `progress/07`) |
| 1 | PDF đặt theo mã băm SHA-256 (nội dung giống → một file); tạo hồ sơ trùng → `409 DUPLICATE_PDF` kèm hồ sơ cũ, không gọi MAIN; `POST …/processing/recheck` | BE | ✅ 2026-10-08 (BE ADR-18) |
| 1 | Hạn mức số bộ hồ sơ khác nhau mỗi workspace (`MAX_REVIEWS_PER_WORKSPACE`, đối tác = 10) | BE | ✅ 2026-10-08 |
| 1 | FE: hộp thoại "file trùng" → mở hồ sơ cũ / kiểm tra lại | FE | ✅ 2026-10-08 (FE D-31, `context/progress/09`) — chưa xem bằng trình duyệt |
| 1b | FE dùng dữ liệu thật: trang `/processing` polling BE, viewer + xuất PDF dùng `GET …/file`, danh sách hồ sơ (BE `GET /reviews` đã hiện thực) | FE · BE | ✅ 2026-10-09 — chạy trên máy: `docs/local-run.md` |
| 2 | Driver lưu file S3 (R2) + script chép kho `storage:sync` | BE | ✅ code 2026-10-19 (BE `progress/09-storage-s3.md`) — ☐ bật với bucket R2 thật |
| 2 | Lưu bộ tiêu chí đã nạp (thay danh mục demo) + gửi nội dung rule cho MAIN (L-01) | BE | ☐ |
| 3 | Kết quả theo dòng tiêu chí (`RawFindingV1`): MAIN gửi, BE lưu, FE hiện | BE · FE · MAIN | ✅ 2026-10-19 (D-23, MAIN `progress/09`) |
| 3 | Thao tác duyệt có cấu trúc + kho chờ + xuất dữ liệu (integration-contract §5.4–5.5) | BE · FE | ☐ |
| 3 | Đo **độ ổn định** của AI (K = 10 lần độc lập, tắt cache) làm thước đo thành công cùng độ chính xác | MAIN | ☐ |
| 4 | Đóng gói Docker + Cloudflare Tunnel / Access + nhận diện người dùng từ Access + sao lưu | cả 3 | ☐ |
| 5 | **Ủ:** kiểm tra lại bản sửa (thiết kế) | — | ☐ |

## Thiết kế — độ nhất quán là thước đo thành công của AI (giai đoạn 3, chưa làm)

> **Sửa 2026-10-08 (người dùng):** "10 lần như một" là **thang đo đánh giá** AI — kiểm cùng một bộ hồ sơ nhiều lần **độc lập** thì kết luận phải giống nhau. **Không** khóa / trả lại kết quả cũ (bản thiết kế đầu hiểu sai). Mỗi lần kiểm tra lại là một lần chạy AI thật.

**Cách đo (chỉ số "độ ổn định"):**
1. Chạy **K = 10 lần độc lập** trên cùng hồ sơ + cùng bộ tiêu chí + cùng phiên bản hệ thống, **tắt mọi bộ nhớ đệm / ghi lại–phát lại**.
2. Với từng dòng tiêu chí: lấy trạng thái của 10 lần (Đạt / Không đạt / Cảnh báo / Cần kiểm tra) và trang bằng chứng.
3. Chỉ số:
   - **Ổn định tuyệt đối**: % dòng có cùng trạng thái ở cả 10 lần.
   - **Đồng thuận trung bình**: trung bình tỉ lệ số lần trùng với trạng thái chiếm đa số.
   - **Lật nghiêm trọng**: số dòng có lần Đạt, có lần Không đạt (tệ nhất — kết luận ngược nhau). Lật giữa "Cần kiểm tra" và một trạng thái khác ít nghiêm trọng hơn, đếm riêng.
   - **Ổn định bằng chứng**: % dòng trỏ cùng trang ở cả 10 lần.
   - Tách theo mẫu kiểm tra M1–M7 và theo bước (diễn giải / định vị / phán đoán) để biết bất ổn nằm ở đâu.
4. Báo cùng **độ chính xác** (so ground truth bạn chấm): AI tốt = vừa đúng vừa ổn định. Chính xác cao nhưng lật nhiều = may rủi.

**Khi độ ổn định thấp, cách nâng (đo lại sau mỗi thay đổi):**
- Phần nào thuật toán làm được thì code làm (đọc bản vẽ, so số, mẫu M1–M7) — phần đó ổn định 100%.
- AI chỉ trả theo khuôn cố định (JSON lược đồ, mã khối chữ trích dẫn); ngữ cảnh gửi đi sắp xếp cố định.
- Dòng hay lật: hỏi vài lần rồi lấy đa số (tốn thêm, chỉ dùng cho dòng khó), hoặc hạ về "Cần kiểm tra" khi các lần không đồng thuận.
- Bước diễn giải bộ tiêu chí cũng đo độ ổn định riêng (diễn giải 10 lần, so mẫu + thông số).

**Chi phí đo** (ước lượng, chưa đo): 10 lần × ~0,5–1,5 USD ≈ 5–15 USD mỗi lần đo trên PN2; Batch API giảm 50%. Chỉ đo ở các mốc, không đo mỗi ngày.

**Bộ nhớ đệm / ghi lại–phát lại** vẫn dùng **khi phát triển** để tiết kiệm (sửa code đọc bản vẽ không phải gọi lại AI), nhưng **luôn tắt** khi đo độ ổn định và khi người dùng bấm "kiểm tra lại".

## Ủ — kiểm tra lại bản sửa (phase sau, chưa làm)

Khi đơn vị thiết kế sửa bản vẽ đã có lỗi rồi nộp lại, không coi là lần kiểm mới mà:

1. **Liên kết phiên bản**: hồ sơ mới khai là "bản sửa của hồ sơ X" (hoặc hệ thống gợi ý khi tên / khung tên / số hiệu bản vẽ trùng) → `review.revisionOf`.
2. **So khác theo từng trang** bằng dấu vân tay nội dung (mã băm chữ + nét vẽ của trang, đã có từ ingest) và số hiệu bản vẽ trong khung tên (đã đọc được — giai đoạn A): trang giữ nguyên / sửa / thêm / bỏ.
3. **Phạm vi kiểm lại** = (a) mọi dòng tiêu chí từng **Không đạt / Cảnh báo / Cần kiểm tra** ở bản trước, (b) mọi dòng có bằng chứng nằm trên trang **đã sửa**, (c) dòng gắn với trang thêm mới. Dòng **Đạt** có bằng chứng trên trang không đổi → **chuyển kết quả cũ sang** (ghi "kế thừa từ bản trước").
4. **Báo cáo theo lỗi cũ**: lỗi nào đã sửa, lỗi nào còn, lỗi mới phát sinh — đúng thứ người kiểm tra cần khi duyệt bản sửa.
5. Dữ liệu đặc thù của hồ sơ (mục lục trang, bảng viết tắt, vai trò layer, diễn giải tiêu chí) dùng lại từ bản trước nếu trang nguồn không đổi.

Phụ thuộc: kết quả theo dòng tiêu chí lưu ở BE (giai đoạn 3), dấu vân tay trang ở MAIN.

## Nhật ký

- **2026-10-08** — Chốt hạ tầng (D-21). Giai đoạn 1 xong phần BE + FE: CSDL thật, file trùng, kiểm tra lại, hạn mức. BE: 61 unit + 28 e2e đạt; FE: `tsc` + `eslint` sạch. Phát hiện: trang `/processing` và viewer của FE còn dùng dữ liệu giả → thêm bước 1b.
- **2026-10-08** — Sửa thiết kế "nhất quán": là thước đo độ ổn định của AI (chạy độc lập K lần), không phải khóa kết quả bằng cache.
- **2026-10-09** — Người dùng tạo xong **Oracle Cloud** và **Neon**. Đã kết nối Neon (PostgreSQL 18.6) từ máy dev và áp migration (`reviews`, `__drizzle_migrations`). Chuỗi kết nối lưu ở `arch-drawing-checker-backend/.env.production` (không commit); `.env` của máy dev vẫn dùng PGlite để không ghi vào CSDL thật. Nhắc người dùng đặt lại mật khẩu Neon (đã dán vào hội thoại). Quy tắc mới: không tự gọi Claude API để test (AGENTS.md §6).
- **2026-10-09** — Oracle bị treo ~6 giờ → chạy cả hệ thống **trên máy người dùng** để thử tính năng trước (`docs/local-run.md`). Đã kiểm luồng thật với PN2 qua API: tải lên → MAIN xử lý 100% → tải lại cùng file tên khác → `409 DUPLICATE_PDF` → kiểm tra lại `202`. Bước 1b xong: BE `GET /reviews` (lọc / sắp / phân trang trong bộ nhớ), FE tiến độ thật + PDF thật + danh sách thật. BE 61 unit + 29 e2e đạt; FE `tsc` + `eslint` sạch, 4 trang trả 200. Đo RAM MAIN trên PN2: đỉnh ~660 MB → máy chủ cần ≥ 1 GB.
- **2026-10-09** — Nối **Claude API** vào MAIN (D-22): hạn mức 5 USD/tháng, mặc định tắt, AI kiểm các dòng rule engine chưa hỗ trợ, kết quả ở viewer debug. Script đo `scripts/run_ai_eval.py` (độ chính xác + độ ổn định K lần). Chưa gọi API thật lần nào.
- **2026-10-25** — Đối tác cần chấm kết quả AI gấp → **viewer chấm của MAIN** (không phải web khách hàng) lên Oracle bằng IP + Caddy + `sslip.io` + mật khẩu chung (D-24, tạm thay Tunnel / Access vì chưa có tên miền). Chế độ `MAIN_REVIEW_ONLY` + `MAIN_REVIEW_PASSWORD`, tên đăng nhập = người chấm. Hướng dẫn: `docs/deploy-review.md`. 104 test đạt; đã chạy thử gói trên máy dev.
- **2026-10-25** — Oracle hết chỗ cho máy miễn phí → viewer chấm chuyển sang **Render + Neon** (D-24 sửa). Kết quả chấm vào Neon (`ai_reviews`), `scripts/pull_reviews.py` kéo về jsonl. 106 test đạt; chưa dựng thử Docker (máy dev không có Docker).

## Hướng dẫn tạo Cloudflare R2 (người dùng tự làm, 2026-10-19)

> Driver S3 của BE đã có (2026-10-19). Không commit khóa bí mật. Đổi kho / bàn giao: chỉ đổi biến `S3_*` + chép bằng `npm run storage:sync` (BE `progress/09-storage-s3.md`).

1. Đăng nhập dash.cloudflare.com → menu **R2 Object Storage**. Lần đầu phải bật R2 và **thêm phương thức thanh toán** (bắt buộc kể cả gói miễn phí; dưới 10 GB lưu trữ thì không mất phí).
2. **Create bucket**: tên `adc-prod` (chữ thường, số, gạch ngang); Location: *Automatic*, gợi ý **Asia-Pacific (APAC)**; Default storage class: **Standard** (không chọn Infrequent Access — gói miễn phí chỉ áp cho Standard).
3. Trong bucket → **Settings**: để **Public access tắt** (không bật r2.dev, không gắn custom domain). FE không tải PDF trực tiếp từ R2 mà qua BE (`GET …/file`) → không cần CORS.
4. **API token**: trang R2 → *Manage API tokens* → **Create API token** (loại *Account API token* nếu có lựa chọn) → quyền **Object Read & Write** → *Specify bucket*: chỉ `adc-prod` → TTL: Forever (hoặc đặt hạn và nhớ xoay vòng). Tạo xong, Cloudflare hiện **một lần duy nhất**: *Access Key ID*, *Secret Access Key*, và *endpoint* `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` → lưu vào trình quản lý mật khẩu.
5. Điền vào `.env.production` của BE (máy chủ, không commit):
   ```
   STORAGE_DRIVER=s3
   S3_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   S3_REGION=auto
   S3_BUCKET=adc-prod
   S3_ACCESS_KEY_ID=<Access Key ID>
   S3_SECRET_ACCESS_KEY=<Secret Access Key>
   ```
6. Quy ước khóa trong bucket: `review-pdfs/<workspace>/sha256/<mã băm>.pdf` (giống driver local) · `training/…` cho dữ liệu duyệt xuất ra (D-20). Một bucket, tách bằng tiền tố.
7. Theo dõi hạn mức: R2 → *Metrics* (dung lượng, số thao tác). Gói miễn phí (tra cứu 2026-10-08): 10 GB lưu trữ, 1 triệu thao tác ghi + 10 triệu thao tác đọc / tháng, không tính phí tải ra.

