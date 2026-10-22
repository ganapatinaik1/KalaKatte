#!/usr/bin/env bash
# deploy.sh — one-shot deploy script
# Run from your LOCAL machine:
#   bash deploy.sh
#
# Prerequisites on the Oracle instance (this script handles it):
#   - Oracle Linux with Python 3.8+ available as python3
#   - Internet access from the instance

set -e
REMOTE="${SSH_REMOTE:-opc@129.159.239.139}"
KEY="${SSH_KEY:-$HOME/Downloads/ssh-key-2026-10-19.key}"
PROJECT_LOCAL="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_REMOTE="/home/opc/KalaKatte"

echo "==> Syncing project files to Oracle instance..."
rsync -avz --exclude '.git' --exclude 'backend/venv' --exclude 'backend/kalakatte.db' \
  -e "ssh -i $KEY" \
  "$PROJECT_LOCAL/" "$REMOTE:$PROJECT_REMOTE/"

echo "==> Running remote setup..."
ssh -i "$KEY" "$REMOTE" bash <<'REMOTE_SCRIPT'
set -e

cd /home/opc/KalaKatte/backend

# --- Python venv ---
if [ ! -d venv ]; then
  echo "[1/6] Creating Python venv..."
  python3 -m venv venv
fi

echo "[2/6] Installing Python dependencies..."
venv/bin/pip install -q -r requirements.txt

# --- Generate secret key if not set ---
if ! grep -q "KK_SECRET_KEY" /etc/environment 2>/dev/null; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  echo "KK_SECRET_KEY=$SECRET" | sudo tee -a /etc/environment
  echo "[3/6] Secret key written to /etc/environment"
else
  echo "[3/6] Secret key already set."
fi
source /etc/environment

# --- nginx ---
echo "[4/6] Setting up nginx..."
sudo dnf install -y nginx 2>/dev/null || sudo yum install -y nginx 2>/dev/null
mkdir -p /home/opc/KalaKatte/backend/uploads
sudo setsebool -P httpd_can_network_connect 1 2>/dev/null || true
sudo cp /home/opc/KalaKatte/backend/nginx-kalakatte.conf /etc/nginx/conf.d/kalakatte.conf
sudo nginx -t
sudo systemctl enable nginx --now
sudo systemctl restart nginx

# --- firewall ---
echo "[5/6] Opening ports 80 and 443..."
sudo firewall-cmd --permanent --add-service=http  2>/dev/null || true
sudo firewall-cmd --permanent --add-service=https 2>/dev/null || true
sudo firewall-cmd --reload 2>/dev/null || true

# --- systemd service ---
echo "[6/6] Installing kalakatte systemd service..."
sudo cp /home/opc/KalaKatte/backend/kalakatte.service /etc/systemd/system/kalakatte.service
sudo systemctl daemon-reload
sudo systemctl enable kalakatte
sudo systemctl restart kalakatte
sleep 2
sudo systemctl status kalakatte --no-pager

echo ""
echo "✅ Deploy complete! Visit http://kalakatte.duckdns.org"
REMOTE_SCRIPT

echo "==> Done."
