#!/usr/bin/env bash
# Production mode: build the frontend once, then serve everything from FastAPI.
set -e
cd "$(dirname "$0")"

(cd frontend && npm run build)
cd backend && exec ../.venv/bin/uvicorn app.main:app --port 8700
