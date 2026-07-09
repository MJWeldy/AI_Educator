#!/usr/bin/env bash
# Production mode: build the frontend once, then serve everything from FastAPI.
#
#   ./run.sh            serve on this machine only (localhost:8700)
#   ./run.sh --lan      also reachable from other devices on your network
#                       (anyone on the network shares one set of profiles)
#   ./run.sh --server   multi-user: reachable on your network AND each person
#                       logs in with their own account (separate progress)
set -e
cd "$(dirname "$0")"

HOST="127.0.0.1"
MODE="${1:-}"
if [ "$MODE" = "--lan" ]; then
  HOST="0.0.0.0"
elif [ "$MODE" = "--server" ]; then
  HOST="0.0.0.0"
  export EDUCATOR_REQUIRE_AUTH=1
fi

(cd frontend && npm run build)

if [ "$HOST" = "0.0.0.0" ]; then
  IP=$(hostname -I 2>/dev/null | awk '{print $1}')
  echo
  echo "Serving on your network — other devices can open:  http://${IP:-<machine-ip>}:8700"
  if [ "$MODE" = "--server" ]; then
    echo "Multi-user mode: everyone signs up / logs in with their own account."
  else
    echo "(anyone on the network can use the app and switch profiles — home networks only)"
  fi
  echo
fi

cd backend && exec ../.venv/bin/uvicorn app.main:app --host "$HOST" --port 8700
