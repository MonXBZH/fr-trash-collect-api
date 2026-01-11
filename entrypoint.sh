#!/usr/bin/env bash
set -euo pipefail

# Si un fichier PDF existe dans data/, on lance le parser pour remplir la DB
PDF_PATH="/app/data/calendar.pdf"
if [ -f "$PDF_PATH" ]; then
  echo "Found calendar PDF at $PDF_PATH — running parser to populate metadata/db"
  python /app/scripts/parse_calendar.py --pdf "$PDF_PATH" || echo "Parser returned non-zero status"
else
  echo "No calendar PDF found at $PDF_PATH — skipping parser"
fi

# Exec the main command (uvicorn by default)
exec "$@"
