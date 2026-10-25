# Đưa viewer chấm kết quả AI lên mạng cho đối tác (D-24)

Mục đích: đối tác chấm kết quả AI (Đúng / Sai vị trí / Sai → kết luận đúng) qua mạng. Kết quả chấm kéo về máy dev đúng định dạng `data/reviews/<mã hồ sơ>.jsonl`, nên `run_ai_eval.py` chấm điểm được ngay.

Đây **không** phải web của khách hàng (FE / BE). Chỉ MAIN chạy ở chế độ chấm:
- `MAIN_REVIEW_ONLY=true`: chỉ mở `/health`, viewer `/debug/inspect/` (địa chỉ `/` tự chuyển vào đây) và API chấm `/debug/reviews/`. API nhận việc từ BE bị tắt. Thiếu mật khẩu thì MAIN không khởi động.
- `MAIN_REVIEW_PASSWORD`: mọi trang `/debug/*` đòi đăng nhập. **Tên đăng nhập = tên người chấm** (ghi vào trường `reviewer` của từng dòng), mật khẩu dùng chung.
- `MAIN_REVIEWS_DATABASE_URL` (có giá trị): kết quả chấm lưu vào Postgres, bảng `ai_reviews` tự tạo, thay cho file.

**Cách A (đang dùng): Render (miễn phí) + Neon Postgres (miễn phí).** Render miễn phí xóa ổ đĩa mỗi khi dịch vụ ngủ (sau 15 phút không ai truy cập), nên kết quả chấm phải nằm ở Neon. Người vào đầu tiên sau lúc ngủ phải chờ khoảng 1 phút.
**Cách B: máy Oracle** (khi tạo được máy, 2026-10-25 bị "Out of capacity").

Các lệnh trên Windows chạy ở **PowerShell**, tại thư mục repo MAIN.

## Cách A — Render + Neon

### A.1 Tạo CSDL Neon

console.neon.tech → **New project** → đặt tên `drawing-checker-review`, region **AWS Asia Pacific (Singapore)** (gần Việt Nam) → Create. Bấm **Connect**, chép **connection string** (dạng `postgresql://neondb_owner:<mật khẩu>@ep-<tên>…neon.tech/neondb?sslmode=require`; bấm biểu tượng con mắt hoặc *Show password* để chuỗi có mật khẩu thật). Đây là chuỗi bí mật: không commit, không gửi đối tác.

### A.2 Đóng gói rồi đưa lên một repo GitHub riêng tư

Repo MAIN bỏ qua thư mục `data/`, nên mình dùng **một repo riêng chỉ để triển khai**, dựng từ gói:

```powershell
python scripts/pack_review_bundle.py eval-20261019-005535-claude-opus-5-5
mkdir D:\Downloads\drawing-checker-review
tar -xzf dist\review-bundle.tar.gz -C D:\Downloads\drawing-checker-review
cd D:\Downloads\drawing-checker-review
git init -b main; git add .; git commit -m "review bundle"
```

Trên github.com tạo repo mới `drawing-checker-review`, chọn **Private**, không thêm README. Rồi:

```powershell
git remote add origin https://github.com/<tài-khoản>/drawing-checker-review.git
git push -u origin main
```

### A.3 Tạo dịch vụ trên Render

dashboard.render.com → **New → Web Service** → kết nối GitHub, chọn repo `drawing-checker-review`:

| Mục | Giá trị |
|---|---|
| Language | **Docker** |
| Region | **Singapore** |
| Dockerfile Path | `deploy/render/Dockerfile` (Docker Build Context để `.`) |
| Instance Type | **Free** |
| Health Check Path (Advanced) | `/health` |
| Environment Variables | `MAIN_REVIEW_PASSWORD` = mật khẩu chung · `MAIN_REVIEWS_DATABASE_URL` = chuỗi Neon ở A.1 |

Bấm **Deploy**. Lần dựng đầu mất vài phút. Xong thì địa chỉ có dạng `https://drawing-checker-review.onrender.com`. Mở địa chỉ đó → hộp đăng nhập → nhập tên của bạn + mật khẩu → lượt `eval-20261019-…` → tab **Kiểm tra**. Bấm chấm thử một dòng rồi kéo về (A.5) để chắc dữ liệu vào Neon.

### A.4 Gửi đối tác

Gửi địa chỉ, mật khẩu chung và đoạn hướng dẫn ở **B.5** bên dưới (giống nhau cho cả hai cách). Báo trước: lần đầu mở sau lúc lâu không dùng phải chờ khoảng 1 phút.

### A.5 Kéo kết quả chấm về máy dev

Thêm vào `.env` của **repo MAIN** (`D:\Downloads\arch-drawing-checker-main\.env`, một lần) **chuỗi thật** chép từ Neon → Connect, giống hệt giá trị đã đặt trên Render. Chuỗi thật có dạng `postgresql://neondb_owner:<mật khẩu>@ep-<tên>.<vùng>.aws.neon.tech/neondb?sslmode=require`:

```
MAIN_REVIEWS_DATABASE_URL=<dán chuỗi kết nối Neon vào đây>
```

```powershell
cd D:\Downloads\arch-drawing-checker-main   # repo MAIN, KHÔNG phải thư mục drawing-checker-review
python scripts/pull_reviews.py
python scripts/run_ai_eval.py "D:\Downloads\PN2-DN-01.pdf" --replay --calls-dir data/ai-agent/calls --max-rules 0 --no-viewer --no-table-grid
```

`pull_reviews.py` ghi lại `data/reviews/<mã>.jsonl` từ Neon. File cũ khác nội dung được giữ thành `.jsonl.bak`. Khi `.env` có biến này, viewer trên máy dev cũng ghi thẳng vào Neon, nên mọi kết quả chấm nằm một chỗ.

### A.6 Cập nhật (sửa code, thêm lượt)

```powershell
python scripts/pack_review_bundle.py <các lượt>
cd D:\Downloads\drawing-checker-review
Get-ChildItem -Exclude .git | Remove-Item -Recurse -Force
tar -xzf D:\Downloads\arch-drawing-checker-main\dist\review-bundle.tar.gz -C .
git add -A; git commit -m "update"; git push
```

Render tự dựng lại sau khi push. Kết quả chấm nằm ở Neon nên không mất.

## Cách B — máy Oracle

Kết quả chấm ghi vào `data/reviews/` **trên máy Oracle** (không cần Neon). Caddy đứng trước, tự cấp HTTPS cho `<IP-nối-bằng-gạch>.sslip.io` (tên miền miễn phí trỏ về IP, không cần mua domain). MAIN chỉ nghe `127.0.0.1:8000`. Lệnh trên máy Oracle chạy trong cửa sổ SSH.

### B.0 — Tạo máy (instance) trên Oracle Cloud (làm một lần)

Oracle Console (cloud.oracle.com) → menu ☰ → **Compute → Instances** → **Create instance**. Góc trên phải phải là **vùng nhà (home region)**, vùng chọn lúc đăng ký: máy ARM miễn phí chỉ tạo được ở vùng này.

| Mục | Chọn |
|---|---|
| Name | `drawing-checker` |
| Image | **Change image → Ubuntu → Canonical Ubuntu 24.04** (hoặc 22.04). Không chọn Oracle Linux: script viết cho Ubuntu |
| Shape | **Change shape → Ampere → `VM.Standard.A1.Flex`**, 2 OCPU + 12 GB RAM (miễn phí tới 4 OCPU / 24 GB; 1 OCPU / 6 GB cũng đủ). Phải thấy nhãn *Always Free-eligible* |
| Networking | Để mặc định *Create new virtual cloud network* + *public subnet*; bật **Automatically assign public IPv4 address** |
| Add SSH keys | **Generate a key pair for me** → bấm **Save private key** (file `.key`). **Chỉ tải được lúc này**, mất thì phải tạo lại máy |
| Boot volume | Để mặc định (~47 GB, nằm trong 200 GB miễn phí) |

Bấm **Create** và đợi trạng thái chuyển sang **Running** (1–3 phút). Ở trang chi tiết máy, chép **Public IP address**. Đó là `<IP>` dùng ở các bước sau.

Gặp **"Out of capacity for shape VM.Standard.A1.Flex"** (lỗi hay gặp với ARM miễn phí):
- Thử *Availability domain* khác (AD-1 / AD-2 / AD-3) trong mục Placement, hoặc giảm còn 1 OCPU / 6 GB.
- Thử lại sau vài giờ (đêm khuya thường dễ hơn).
- Đường lùi: shape **AMD `VM.Standard.E2.1.Micro`** (1 GB RAM, cũng miễn phí). Script tự thêm swap, chạy được việc xem / chấm nhưng chậm hơn.
- Nâng tài khoản lên **Pay As You Go** (vẫn không tính tiền nếu chỉ dùng tài nguyên Always Free) thường hết lỗi hết chỗ. Nên đặt cảnh báo ngân sách (Billing → Budgets) cho chắc.

### B.1 — Vào được máy Oracle bằng SSH

Cần: **IP công khai** (Oracle Console → Compute → Instances → bấm vào máy → *Public IP address*) và **file khóa riêng** (`.key`) đã tải lúc tạo máy.

```powershell
# Windows từ chối khóa nếu người khác đọc được file → khóa quyền một lần:
icacls "C:\duong\dan\ssh-key.key" /inheritance:r /grant:r "$($env:USERNAME):R"
ssh -i "C:\duong\dan\ssh-key.key" ubuntu@<IP>
```

Ảnh Ubuntu dùng user `ubuntu`, ảnh Oracle Linux dùng `opc`. Vào được rồi thì xem máy là loại gì:

```bash
uname -m; . /etc/os-release; echo $PRETTY_NAME; free -h
```

- `aarch64` là máy ARM (Ampere), `x86_64` là máy AMD. Cả hai đều chạy được.
- Script cài đặt chỉ viết cho **Ubuntu**. Nếu máy là Oracle Linux, dừng lại và báo để viết bản cho Oracle Linux.
- RAM dưới 2 GB (gói Micro 1 GB): script tự thêm 2 GB swap. Việc xem / chấm nhẹ, đủ chạy.

### B.2 — Mở cổng 80 + 443 ở Oracle Console (làm một lần)

Oracle Console → Networking → Virtual Cloud Networks → VCN của máy → Subnet → **Security List** (`Default Security List…`) → **Add Ingress Rules**, thêm 2 dòng:

| Source CIDR | IP Protocol | Destination Port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

Cổng 80 cần cho Caddy xin chứng chỉ HTTPS. Mọi trang đều đòi mật khẩu. Tường lửa **bên trong** máy (iptables) do script tự mở.

### B.3 — Đóng gói trên Windows rồi chép lên máy

```powershell
python scripts/pack_review_bundle.py eval-20261019-005535-claude-opus-5-5
# → dist\review-bundle.tar.gz (~32 MB: mã nguồn + lượt 2, không gồm data/reviews)
scp -i "C:\duong\dan\ssh-key.key" dist\review-bundle.tar.gz deploy\oracle\setup.sh ubuntu@<IP>:~/
```

Muốn đưa thêm lượt khác thì ghi thêm tên thư mục trong `data/inspect` sau lệnh đóng gói.

### B.4 — Cài đặt trên máy Oracle

```bash
REVIEW_PASSWORD='dat-mat-khau-chung-o-day' bash ~/setup.sh ~/review-bundle.tar.gz
```

Script lo hết: Python + venv, Caddy, swap (máy RAM nhỏ), tường lửa, dịch vụ `drawing-checker` (tự chạy lại khi máy khởi động lại). Cuối cùng script in địa chỉ, ví dụ `https://152-67-1-2.sslip.io/`. Bỏ `REVIEW_PASSWORD=` thì script sinh mật khẩu ngẫu nhiên và in ra.

Kiểm tra: mở địa chỉ đó bằng trình duyệt → hộp đăng nhập → nhập tên của bạn + mật khẩu → danh sách lượt → bấm lượt `eval-20261019-…` → tab **Kiểm tra**.

### B.5 — Gửi đối tác

Gửi đối tác **địa chỉ** và **mật khẩu chung**, kèm hướng dẫn ngắn:

> 1. Mở link, đăng nhập: **tên đăng nhập là tên của anh/chị** (không dấu, ví dụ `nguyen.an`), mật khẩu chung.
> 2. Bấm lượt kiểm tra → tab **Kiểm tra**. Ô "Hiện" chọn **Chưa duyệt** để chỉ thấy dòng chưa chấm.
> 3. Mỗi dòng: bấm vào để xem bằng chứng trên bản vẽ, rồi chọn:
>    - **Đúng**: kết luận và vị trí bằng chứng đều đúng.
>    - **Sai vị trí**: kết luận đúng, nhưng chỗ khoanh trên bản vẽ sai.
>    - **Sai →** chọn kết luận đúng (Đạt / Không đạt / Cảnh báo / Cần kiểm tra / Không áp dụng).
>    - Có thể ghi chú thêm. Chấm lại một dòng thì lần chấm sau thay lần trước.
> 4. Tùy chọn **Chấm mù**: ẩn kết luận của hệ thống cho tới khi chấm xong dòng, để không bị ảnh hưởng.

Tên đăng nhập nên **không dấu**: một số trình duyệt mã hóa tên có dấu khác nhau. Nhiều người chấm cùng một dòng thì **lần chấm sau cùng** được dùng để tính điểm. Cả hai lần vẫn nằm trong file, mỗi lần kèm `reviewer`.

### B.6 — Kéo kết quả chấm về máy dev và tính độ chính xác

```powershell
scp -i "C:\duong\dan\ssh-key.key" "ubuntu@<IP>:drawing-checker/data/reviews/*.jsonl" data\reviews\
python scripts/run_ai_eval.py "D:\Downloads\PN2-DN-01.pdf" --replay --calls-dir data/ai-agent/calls --max-rules 0 --no-viewer --no-table-grid
```

⚠ Lệnh `scp` **ghi đè** file `data\reviews\<mã>.jsonl` trên máy dev. Từ khi đưa lên Oracle, chỉ chấm trên Oracle. Nếu đã lỡ chấm trên máy dev thì chép file đó ra chỗ khác trước khi kéo về.

### Cập nhật (sửa code, thêm lượt mới)

Làm lại bước 3 + 4, bỏ `REVIEW_PASSWORD=` nếu muốn giữ mật khẩu cũ. Script **giữ nguyên `data/reviews`**: gói không chứa thư mục này, và giải nén không xóa nó.

### Sự cố thường gặp

| Hiện tượng | Xem |
|---|---|
| Trình duyệt không mở được trang (hết thời gian chờ) | Bước 2 (Security List); `sudo iptables -L INPUT -n --line-numbers` phải có ACCEPT cổng 80, 443 ở trên dòng REJECT |
| Lỗi chứng chỉ HTTPS | `sudo journalctl -u caddy -n 50`. sslip.io dùng chung giới hạn cấp chứng chỉ Let's Encrypt; Caddy tự thử ZeroSSL, đợi vài phút rồi tải lại |
| `502 Bad Gateway` | MAIN chưa chạy: `sudo systemctl status drawing-checker`, `sudo journalctl -u drawing-checker -n 50` |
| Quên mật khẩu | `cat ~/drawing-checker/.env` trên máy Oracle |
| Đổi mật khẩu | `REVIEW_PASSWORD='mới' bash ~/setup.sh ~/review-bundle.tar.gz` |
