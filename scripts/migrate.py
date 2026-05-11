#!/usr/bin/env python3
"""
Script de migration de la base de données.
Applique les migrations manquantes de façon idempotente au démarrage.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine
from sqlalchemy import text


MIGRATIONS = [
    (
        "uq_collection_date_type_city",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_date_type_city
        ON collections (date, waste_type, city)
        """,
    ),
]


def run_migrations():
    with engine.connect() as conn:
        for name, sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[migrate] OK: {name}")
            except Exception as e:
                print(f"[migrate] SKIP ({name}): {e}")


if __name__ == "__main__":
    run_migrations()
