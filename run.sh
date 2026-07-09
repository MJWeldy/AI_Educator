#!/usr/bin/env bash
# Production mode: build the frontend once, then serve everything from FastAPI.
#
#   ./run.sh            serve on this machine only (localhost:8700)
#   ./run.sh --lan      also reachable from other devices on your network
#                       (anyone on the network shares one set of profiles)
#   ./run.sh --server   multi-user on your network: each person signs up and
#                       logs in with their own account (separate progress)
#   ./run.sh --web      multi-user for the internet, behind a tunnel (e.g. ngrok):
#                       serves on localhost only, HTTPS-safe cookies, sign-ups
#                       CLOSED (create accounts with app.manage). See DEPLOY.md.
set -e
cd "$(dirname "$0")"

HOST="127.0.0.1"
MODE="${1:-}"
UVICORN_EXTRA=()
if [ "$MODE" = "--lan" ]; then
  HOST="0.0.0.0"
elif [ "$MODE" = "--server" ]; then
  HOST="0.0.0.0"
  export EDUCATOR_REQUIRE_AUTH=1
elif [ "$MODE" = "--web" ]; then
  HOST="127.0.0.1"                       # only the tunnel reaches it, not the LAN
  export EDUCATOR_REQUIRE_AUTH=1
  export EDUCATOR_ALLOW_SIGNUP=0         # owner creates accounts (app.manage)
  export EDUCATOR_SECURE_COOKIES=1       # tunnel terminates HTTPS
  UVICORN_EXTRA=(--proxy-headers --forwarded-allow-ips=*)
fi

(cd frontend && npm run build)

if [ "$MODE" = "--web" ]; then
  echo
  echo "Web mode: serving on http://127.0.0.1:8700 — now expose it with your tunnel, e.g.:"
  echo "    ngrok http 8700"
  echo "Then share the https URL ngrok prints. Sign-ups are closed; create accounts with:"
  echo "    cd backend && ../.venv/bin/python -m app.manage create-user <name>"
  echo "(other tunnels and details: DEPLOY.md)"
  echo
elif [ "$HOST" = "0.0.0.0" ]; then
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

cd backend && exec ../.venv/bin/uvicorn app.main:app --host "$HOST" --port 8700 "${UVICORN_EXTRA[@]}"
