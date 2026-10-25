#!/usr/bin/env bash
# Cài / cập nhật MAIN ở chế độ chấm cho đối tác trên máy Oracle (Ubuntu). Chạy lại được nhiều lần.
#   REVIEW_PASSWORD='mật-khẩu-chung' bash setup.sh ~/review-bundle.tar.gz
# Hướng dẫn đầy đủ: docs/deploy-review.md
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

BUNDLE="${1:?Cách dùng: REVIEW_PASSWORD=... bash setup.sh <review-bundle.tar.gz>}"
APP_DIR="$HOME/drawing-checker"
APP_USER="$(id -un)"

. /etc/os-release
if [ "${ID:-}" != "ubuntu" ]; then
  echo "Script này viết cho Ubuntu (máy đang là: ${PRETTY_NAME:-không rõ})." >&2
  exit 1
fi
echo "== Máy: $PRETTY_NAME · $(uname -m) · RAM $(awk '/MemTotal/ {printf "%.1f GB", $2/1048576}' /proc/meminfo)"

# 1. Gói hệ thống + Caddy (tự cấp HTTPS).
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip curl gnupg debian-keyring debian-archive-keyring \
  apt-transport-https iptables-persistent
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg /etc/apt/sources.list.d/caddy-stable.list
  sudo apt-get update -y
  sudo apt-get install -y caddy
fi

# 2. Máy RAM nhỏ (gói Micro 1 GB): thêm 2 GB swap để cài PyMuPDF không bị hết bộ nhớ.
if [ "$(awk '/MemTotal/ {print $2}' /proc/meminfo)" -lt 2000000 ] && [ ! -f /swapfile ]; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

# 3. Mã nguồn + lượt viewer. Giữ nguyên data/reviews (kết quả chấm) khi cập nhật.
mkdir -p "$APP_DIR/data/reviews"
rm -rf "$APP_DIR/src"
tar -xzf "$BUNDLE" -C "$APP_DIR"
cd "$APP_DIR"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -e . -q

# 4. Cấu hình. Mật khẩu: lấy từ REVIEW_PASSWORD, không có thì giữ cái cũ, chưa có cái cũ thì sinh ngẫu nhiên.
if [ -n "${REVIEW_PASSWORD:-}" ] || [ ! -f .env ]; then
  PW="${REVIEW_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(9))')}"
  cat > .env <<EOF
MAIN_REVIEW_ONLY=true
MAIN_REVIEW_PASSWORD=$PW
MAIN_INSPECT_ENABLED=true
MAIN_INSPECT_DIR=data/inspect
MAIN_REVIEWS_DIR=data/reviews
MAIN_AI_PROVIDER=off
EOF
  chmod 600 .env
  echo "== Mật khẩu chung cho đối tác: $PW"
fi

# 5. Dịch vụ MAIN (chỉ nghe 127.0.0.1 — ra ngoài qua Caddy).
sudo tee /etc/systemd/system/drawing-checker.service >/dev/null <<EOF
[Unit]
Description=Arch Drawing Checker MAIN (chế độ chấm cho đối tác)
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/uvicorn drawing_checker.app:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 6. HTTPS qua <IP>.sslip.io (tên miền miễn phí trỏ về IP, không cần mua domain).
PUBLIC_IP="${PUBLIC_IP:-$(curl -4 -s https://ifconfig.me)}"
HOST="${PUBLIC_IP//./-}.sslip.io"
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
$HOST {
	redir / /debug/inspect/
	reverse_proxy 127.0.0.1:8000
}
EOF

# 7. Tường lửa trong máy: ảnh Ubuntu của Oracle chặn mọi cổng trừ 22 → mở 80 (cấp chứng chỉ) + 443.
for port in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$port" -m conntrack --ctstate NEW -j ACCEPT 2>/dev/null \
    || sudo iptables -I INPUT 1 -p tcp --dport "$port" -m conntrack --ctstate NEW -j ACCEPT
done
sudo netfilter-persistent save

sudo systemctl daemon-reload
sudo systemctl enable --now drawing-checker
sudo systemctl restart drawing-checker caddy

sleep 2
curl -fsS http://127.0.0.1:8000/health >/dev/null && echo "== MAIN chạy OK"
echo "== Địa chỉ cho đối tác: https://$HOST/"
echo "   (Nếu không mở được: kiểm tra Security List của Oracle đã mở cổng 80 + 443 — xem hướng dẫn bước 2.)"
