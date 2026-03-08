#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/dashboard.pid"
LOG_FILE="$ROOT_DIR/dashboard.log"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" >/dev/null 2>&1; then
    echo "Dashboard already running on PID $PID"
    exit 0
  else
    rm -f "$PID_FILE"
  fi
fi

cd "$ROOT_DIR"
nohup "$ROOT_DIR/.venv/bin/streamlit" run "$ROOT_DIR/dashboard.py" --server.address 0.0.0.0 --server.port 8501 >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Dashboard started on PID $(cat "$PID_FILE")"
