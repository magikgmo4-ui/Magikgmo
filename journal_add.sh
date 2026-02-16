#!/bin/bash
set -euo pipefail

export TZ=America/Montreal
TODAY=$(date +%F)
FILE="/opt/trading/journal/$TODAY.md"

TITLE="${1:-}"
if [ -z "$TITLE" ]; then
  echo "Usage: $0 \"Titre de session\""
  exit 1
fi

mkdir -p /opt/trading/journal

if [ ! -f "$FILE" ]; then
  touch "$FILE"
fi

echo "" >> "$FILE"
echo "## $(date '+%Y-%m-%d %H:%M:%S') — $TITLE" >> "$FILE"
echo "" >> "$FILE"

cd /opt/trading
git add journal
git commit -m "Journal update: $TITLE" || echo "Nothing to commit."
git push
