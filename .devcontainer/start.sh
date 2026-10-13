#!/usr/bin/env bash
# Runs every time the Codespace / dev container starts: serves the API and the
# built web app together on port 8000 (logs in /tmp/growth-os.log).
set -euo pipefail
cd "$(dirname "$0")/../backend"

if curl -fsS http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
  echo "Growth OS is already running on port 8000"
  exit 0
fi

setsid nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/growth-os.log 2>&1 < /dev/null &

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
    echo "Growth OS is running on port 8000. Open the Ports tab if the browser didn't open."
    exit 0
  fi
  sleep 1
done
echo "Growth OS did not start; see /tmp/growth-os.log" >&2
exit 1
