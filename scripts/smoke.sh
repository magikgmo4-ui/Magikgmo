#!/usr/bin/env bash
set -Eeuo pipefail

PERF_BASE="${BASE:-http://127.0.0.1:8010}"
WEBHOOK_BASE="${WEBHOOK_BASE:-http://127.0.0.1:8000}"

say(){ echo "$*"; }
die(){ echo "❌ $*"; exit 1; }

say "[1/4] webhook health (best-effort)"
curl -fsS "$WEBHOOK_BASE/api/state" >/dev/null 2>&1 || true

say "[2/4] perf summary (wait-ready)"
for i in {1..50}; do
  if curl -fsS "$PERF_BASE/perf/summary" >/dev/null 2>&1; then break; fi
  sleep 0.2
  [[ "$i" == "50" ]] && die "perf not ready at $PERF_BASE"
done

say "[3/4] create dummy trade OPEN/CLOSE"
TID="T_SMOKE_$(date +%Y%m%d_%H%M%S)_${RANDOM}_${RANDOM}"

open_json="$(curl -fsS "$PERF_BASE/perf/event" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"OPEN\",\"trade_id\":\"$TID\",\"engine\":\"SMOKE\",\"symbol\":\"XAUUSD\",\"side\":\"LONG\",\"entry\":1.0,\"stop\":0.9,\"qty\":1.0,\"risk_usd\":0.1}")" || die "OPEN failed"

echo "$open_json" | python3 -m json.tool >/dev/null 2>&1 || die "OPEN response not JSON: $open_json"

close_json="$(curl -fsS "$PERF_BASE/perf/event" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"CLOSE\",\"trade_id\":\"$TID\",\"exit\":1.1}")" || die "CLOSE failed"

echo "$close_json" | python3 -m json.tool >/dev/null 2>&1 || die "CLOSE response not JSON: $close_json"

say "[4/4] verify trade appears"
found="0"
for i in {1..30}; do
  if curl -fsS "$PERF_BASE/perf/trades?limit=50" | grep -q "$TID"; then found="1"; break; fi
  sleep 0.2
done
[[ "$found" == "1" ]] || die "Trade not found in /perf/trades: $TID"

echo "OK"
