#!/usr/bin/env bash
set -euo pipefail

# Générer une clé admin si non définie
if [ -z "${ADMIN_API_KEY:-}" ]; then
  ADMIN_API_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
  export ADMIN_API_KEY
  echo "============================================================"
  echo "  ADMIN_API_KEY auto-générée (non définie dans l'environnement)"
  echo "  ADMIN_API_KEY=${ADMIN_API_KEY}"
  echo "  Récupérez-la avec : docker logs <container> | grep ADMIN_API_KEY"
  echo "============================================================"
else
  echo "ADMIN_API_KEY définie via l'environnement."
fi

# Appliquer les migrations de base de données
echo "Running database migrations..."
python /app/scripts/migrate.py || echo "Migrations returned non-zero status"

# Scanner data/pdfs/ pour importer tous les PDFs présents (toutes villes détectées)
PDFS_DIR="/app/data/pdfs"
if [ -d "$PDFS_DIR" ]; then
  shopt -s nullglob
  pdf_files=("$PDFS_DIR"/*.pdf)
  if [ ${#pdf_files[@]} -gt 0 ]; then
    for pdf_file in "${pdf_files[@]}"; do
      echo "Found PDF: $pdf_file — running parser (all detected cities)"
      python /app/scripts/parse_calendar.py --pdf "$pdf_file" || echo "Parser returned non-zero for $pdf_file"
    done
  else
    echo "No PDF files found in $PDFS_DIR — skipping parser"
  fi
else
  echo "Directory $PDFS_DIR does not exist — skipping parser"
fi

# Exec the main command (uvicorn by default)
exec "$@"
