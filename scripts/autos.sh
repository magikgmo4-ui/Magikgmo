#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/trading"
BASE="${BASE:-http://127.0.0.1:8010}"

cd "$ROOT"

echo "== restart services =="
sudo systemctl restart tv-webhook.service ngrok-tv.service 2>/dev/null || sudo systemctl restart tv-webhook.service
sleep 1

echo "== smoke =="
BASE="$BASE" ./scripts/smoke.sh

echo "== diagnose =="
./scripts/diagnose.sh

echo "== logs: tv-webhook =="
journalctl -u tv-webhook.service -n 80 --no-pager

echo "== logs: ngrok-tv =="
journalctl -u ngrok-tv.service -n 80 --no-pager 2>/dev/null || true

echo "== service: tv-perf (if any) =="
systemctl status tv-perf.service --no-pager 2>/dev/null || echo "tv-perf.service: NOT FOUND"
journalctl -u tv-perf.service -n 80 --no-pager 2>/dev/null || true

echo "== ngrok tunnels (public url) =="
if curl -sf http://127.0.0.1:4040/api/tunnels >/dev/null 2>&1; then
  curl -s http://127.0.0.1:4040/api/tunnels | python -m json.tool | head -n 120
else
  echo "ngrok local API not reachable on 127.0.0.1:4040"
fi

echo "== ngrok recent hits =="
if curl -sf http://127.0.0.1:4040/api/requests/http >/dev/null 2>&1; then
  curl -s http://127.0.0.1:4040/api/requests/http | head -c 1200 ; echo
fi

echo "== last diag file (tail) =="
ls -1t logs/diagnostics/diag_*.log 2>/dev/null | head -n 1 | xargs -r tail -n 140

echo "DONE"
