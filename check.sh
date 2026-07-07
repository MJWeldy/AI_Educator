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

echo "== latex =="
(cd backend && ../.venv/bin/python scripts/export_latex.py /tmp/educator-latex-check.json > /dev/null)
(cd frontend && node scripts/check-katex.mjs /tmp/educator-latex-check.json)

echo "All checks passed."
