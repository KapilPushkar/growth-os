#!/usr/bin/env bash
# Runs once when the Codespace / dev container is created: installs both
# halves of the app, builds the web UI and loads the demo data.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Backend dependencies"
python -m venv backend/.venv
backend/.venv/bin/pip install --quiet --upgrade pip
backend/.venv/bin/pip install --quiet -r backend/requirements-dev.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env

echo "==> Web app build"
(cd frontend && npm ci --no-audit --no-fund && npm run build)

echo "==> Demo data"
(cd backend && .venv/bin/python -m app.seed)
