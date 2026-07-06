#!/usr/bin/env bash
# Start backend (with reload) and frontend dev server. Ctrl-C stops both.
set -e
cd "$(dirname "$0")"

trap 'kill 0' EXIT

(cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8700) &
(cd frontend && npm run dev) &
wait
