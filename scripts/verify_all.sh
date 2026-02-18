#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."  # repo root

TS="$(date +%Y%m%d_%H%M%S)"
OUT="tmp/verify_${TS}.log"
mkdir -p tmp

{
  echo "===== VERIFY START ${TS} ====="
  echo "pwd: $(pwd)"
  echo "user: $(whoami)"
  echo

  echo "== git =="
  git rev-parse --short HEAD || true
  git status --porcelain || true
  echo

  echo "== python compile (syntax) =="
  python3 -m py_compile webhook_server.py
  python3 -m py_compile perf/perf_app.py
  python3 -m py_compile adapters/webhook_to_perf.py
  python3 -m py_compile strategy_logic.py
  echo "OK py_compile"
  echo

  echo "== smoke =="
./scripts/smoke.sh
SMOKE_RC=$?
echo "smoke rc: ${SMOKE_RC}"
  echo

  echo "== diagnose =="
./scripts/diagnose.sh
DIAG_RC=$?
echo "diagnose rc: ${DIAG_RC}"
  echo

  echo "===== VERIFY END ${TS} ====="
} 2>&1 | tee "${OUT}"

echo
echo "Saved log: ${OUT}"


if [[ "${SMOKE_RC:-0}" -ne 0 || "${DIAG_RC:-0}" -ne 0 ]]; then
  exit 1
fi
