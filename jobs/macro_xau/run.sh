#!/bin/bash
set -euo pipefail

BASE_DIR="/opt/trading/jobs/macro_xau"
VENV="/opt/trading/venv"
LOG="/var/log/trading/macro_xau.log"
LOCK="/var/lock/macro_xau.lock"

source "${VENV}/bin/activate"
cd "${BASE_DIR}"

# Empêche 2 exécutions en même temps
exec 200>"${LOCK}"
flock -n 200 || exit 0

echo "===== $(date) :: START macro_xau =====" >> "${LOG}"
python3 macro_xau.py >> "${LOG}" 2>&1
rc=$?
echo "===== $(date) :: END macro_xau (rc=${rc}) =====" >> "${LOG}"
exit $rc

