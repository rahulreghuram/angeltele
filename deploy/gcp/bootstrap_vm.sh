#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/angel_bot}"
APP_USER="${APP_USER:-$(whoami)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -d "$APP_DIR" ]]; then
  echo "APP_DIR not found: $APP_DIR"
  echo "Clone or copy the repo first, then rerun with APP_DIR=/path/to/angel_bot"
  exit 1
fi

cd "$APP_DIR"

sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Prepare runtime setting file if missing.
if [[ ! -f bot_settings.json ]]; then
  cat > bot_settings.json << 'JSON'
{
  "telegram": true,
  "autotrade": false,
  "bot_running": true,
  "ai_strategy_enabled": false,
  "strategy_mode": "manual"
}
JSON
fi

# Install systemd units with resolved absolute paths.
sed "s|__APP_DIR__|$APP_DIR|g; s|__APP_USER__|$APP_USER|g" deploy/systemd/angel-dashboard.service | sudo tee /etc/systemd/system/angel-dashboard.service >/dev/null
sed "s|__APP_DIR__|$APP_DIR|g; s|__APP_USER__|$APP_USER|g" deploy/systemd/angel-bot-daemon.service | sudo tee /etc/systemd/system/angel-bot-daemon.service >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable angel-dashboard.service angel-bot-daemon.service
sudo systemctl restart angel-dashboard.service angel-bot-daemon.service

echo "Done. Service status:"
sudo systemctl --no-pager --full status angel-dashboard.service | sed -n '1,12p'
sudo systemctl --no-pager --full status angel-bot-daemon.service | sed -n '1,12p'

echo "Dashboard should be on: http://<VM_EXTERNAL_IP>:8501"
