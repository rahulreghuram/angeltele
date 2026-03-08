#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/dashboard.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Dashboard is not running (no PID file)."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID"
  echo "Dashboard stopped (PID $PID)."
else
  echo "Dashboard process not found."
fi

rm -f "$PID_FILE"
