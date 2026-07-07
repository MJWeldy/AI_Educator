#!/usr/bin/env bash
# One-time setup: Python venv + backend deps, frontend deps, first build.
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "ERROR: python3 is required (3.12+)"; exit 1; }
command -v npm >/dev/null || { echo "ERROR: Node.js 18+ (with npm) is required"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' || {
  echo "ERROR: Python 3.12+ is required (found $(python3 --version))"; exit 1; }

echo "== creating Python virtualenv (.venv) =="
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r backend/requirements.lock

echo "== installing frontend dependencies =="
(cd frontend && npm install --no-fund --no-audit)

echo "== building frontend =="
(cd frontend && npm run build)

echo
echo "✓ Setup complete."
echo "  Start the app:   ./run.sh"
echo "  Then open:       http://localhost:8700"
echo
echo "AI features (hints, lesson generation, textbook upload) are optional."
echo "Point them at a local Ollama or paste a Claude API key in Settings."
