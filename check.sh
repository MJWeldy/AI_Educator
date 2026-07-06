#!/usr/bin/env bash
# Full verification gate: backend tests, type check, frontend build.
set -e
cd "$(dirname "$0")"

echo "== pytest =="
(cd backend && ../.venv/bin/python -m pytest -q)

echo "== tsc =="
(cd frontend && npx tsc --noEmit -p tsconfig.app.json)

echo "== vite build =="
(cd frontend && npm run build)

echo "All checks passed."
