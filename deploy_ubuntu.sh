#!/bin/bash
# ==============================================================================
# Ubuntu 22.04 / 24.04 One-Click Production Deployment Script
# WhatsApp Order Bot - 24/7 Gunicorn + Nginx + Cloudflare/DuckDNS Ready
# ==============================================================================

set -e

echo "🚀 Starting Ubuntu 22.04/24.04 Deployment for WhatsApp Order Bot..."

# 1. Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git curl wget nginx certbot python3-certbot-nginx

# 2. Setup Virtual Environment & Install Dependencies
echo "🐍 Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 3. Create Systemd Service for 24/7 Auto-Restart
PROJECT_DIR=$(pwd)
USER_NAME=$(whoami)

echo "⚙️ Creating 24/7 Systemd Service: /etc/systemd/system/whatsapp-bot.service..."

sudo bash -c "cat <<EOF > /etc/systemd/system/whatsapp-bot.service
[Unit]
Description=WhatsApp Order Bot Service
After=network.target

[Service]
User=${USER_NAME}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 main:app
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF"

# 4. Enable and Start Systemd Service
echo "🔄 Reloading and Starting WhatsApp Bot Service..."
sudo systemctl daemon-reload
sudo systemctl enable whatsapp-bot
sudo systemctl restart whatsapp-bot

# 5. Check Service Status
echo "✅ Checking Service Status:"
sudo systemctl status whatsapp-bot --no-pager

echo ""
echo "🎉 WhatsApp Order Bot is now running 24/7 on local port 5000!"
echo "Useful Commands:"
echo "  - Check Logs:   sudo journalctl -u whatsapp-bot -f"
echo "  - Restart Bot:  sudo systemctl restart whatsapp-bot"
echo "  - Stop Bot:     sudo systemctl stop whatsapp-bot"
