#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v python >/dev/null 2>&1; then echo "Python is required."; exit 1; fi
if ! command -v npm >/dev/null 2>&1; then echo "Node.js/npm is required for the frontend."; exit 1; fi

python -m venv "$ROOT/.venv"
if [ -f "$ROOT/.venv/bin/activate" ]; then source "$ROOT/.venv/bin/activate"; else source "$ROOT/.venv/Scripts/activate"; fi
pip install -r "$ROOT/target_app/requirements.txt" -r "$ROOT/backend/requirements.txt"
(cd "$ROOT/target_app" && uvicorn app.main:app --reload --port 8001) &
TARGET_PID=$!
(cd "$ROOT/backend" && TARGET_BASE_URL=http://127.0.0.1:8001 uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!
(cd "$ROOT/frontend" && npm install && npm run dev -- --host 0.0.0.0) &
FRONTEND_PID=$!
trap 'kill "$TARGET_PID" "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' EXIT
wait
