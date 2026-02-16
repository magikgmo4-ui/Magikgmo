#!/usr/bin/env bash
set -euo pipefail

# Remove python bytecode/cache artifacts that should never be committed
find . -name '__pycache__' -type d -prune -exec rm -rf {} +
find . -name '*.pyc' -delete

# Optional: editor/OS cruft
find . -name '.DS_Store' -delete

echo "OK: cleaned __pycache__/ and *.pyc" 
