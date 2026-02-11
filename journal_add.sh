#!/bin/bash

export TZ=America/Montreal
TODAY=$(date +%F)
FILE="/opt/trading/journal/$TODAY.md"

mkdir -p /opt/trading/journal

if [ ! -f "$FILE" ]; then
  touch "$FILE"
fi

echo "" >> "$FILE"
echo "## $(date '+%Y-%m-%d %H:%M:%S') — $1" >> "$FILE"
echo "" >> "$FILE"

cd /opt/trading
git add journal
git commit -m "Journal update: $1"
