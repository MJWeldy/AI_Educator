#!/usr/bin/env bash
# Production mode: build the frontend once, then serve everything from FastAPI.
#
#   ./run.sh          serve on this machine only (localhost:8700)
#   ./run.sh --lan    also reachable from other devices on your network
set -e
cd "$(dirname "$0")"

HOST="127.0.0.1"
if [ "${1:-}" = "--lan" ]; then
  HOST="0.0.0.0"
fi

(cd frontend && npm run build)

if [ "$HOST" = "0.0.0.0" ]; then
  IP=$(hostname -I 2>/dev/null | awk '{print $1}')
  echo
  echo "Serving on your network — other devices can open:  http://${IP:-<this-machine's-IP>}:8700"
  echo "(anyone on the network can use the app and switch profiles — home networks only)"
  echo
fi

cd backend && exec ../.venv/bin/uvicorn app.main:app --host "$HOST" --port 8700
