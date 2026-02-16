#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
LOG="logs/diagnostics/diag_${TS}.log"

WEBHOOK_BASE="${WEBHOOK_BASE:-http://127.0.0.1:8000}"
BASE="${BASE:-http://127.0.0.1:8010}"

mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

echo "===== DIAG START $TS ====="
echo "pwd: $(pwd)"
echo "user: $(id -un)"
echo "git head: $(git rev-parse --short HEAD 2>/dev/null || echo '?')"
echo

echo "== git status (porcelain) =="
git status --porcelain || true
echo

echo "== python/venv =="
if [ -x venv/bin/python ]; then
  venv/bin/python -V || true
  venv/bin/python -c "import sys; print('executable:', sys.executable)" || true
else
  echo "venv/bin/python missing"
fi
echo

echo "== systemd tv-webhook.service =="
sudo systemctl status tv-webhook.service --no-pager -l || true
echo

echo "== recent logs tv-webhook.service (last 40) =="
sudo journalctl -u tv-webhook.service -n 40 --no-pager || true
echo

echo "== endpoints check =="
echo "-- webhook /api/state (GET) $WEBHOOK_BASE/api/state"
curl -sS -i "$WEBHOOK_BASE/api/state" | sed -n '1,20p' || true
echo
echo "-- perf /perf/summary (GET) $BASE/perf/summary"
curl -sS -i "$BASE/perf/summary" | sed -n '1,40p' || true
echo
echo "-- perf /perf/open (GET) $BASE/perf/open"
curl -sS -i "$BASE/perf/open" | sed -n '1,30p' || true
echo

echo "== smoke (BASE) =="
if [ -x scripts/smoke.sh ]; then
  BASE="$BASE" ./scripts/smoke.sh || echo "SMOKE FAILED"
else
  echo "scripts/smoke.sh missing"
fi
echo

echo "== curl quick map ports 8000/8010 =="
for p in 8000 8010; do
  echo "--- port $p ---"
  curl -sS -D- -o /dev/null "http://127.0.0.1:$p/api/state" | head -n 5 || true
  curl -sS -D- -o /dev/null "http://127.0.0.1:$p/perf/summary" | head -n 5 || true
done
echo

echo "== permissions sanity =="
ls -la venv/bin/python 2>/dev/null || true
ls -la scripts/smoke.sh 2>/dev/null || true
echo

echo "===== DIAG END $TS ====="
echo "LOG: $LOG"
