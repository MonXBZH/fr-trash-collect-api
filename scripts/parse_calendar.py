#!/usr/bin/env python3
"""
Parser de calendrier PDF pour extraire les collectes de déchets.
Génère les dates de collecte basées sur les règles:
- Ordures ménagères: Lundi semaine paire
- Déchets recyclables: Jeudi semaine impaire
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import typer
from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine
from app import models, schemas, crud

app = typer.Typer()


JOURS_FERIES_2025_2026 = [
    date(2025, 1, 1),   # Jour de l'an
    date(2025, 4, 21),  # Lundi de Pâques
    date(2025, 5, 1),   # Fête du travail
    date(2025, 5, 8),   # Victoire 1945
    date(2025, 5, 29),  # Ascension
    date(2025, 6, 9),   # Lundi de Pentecôte
    date(2025, 7, 14),  # Fête nationale
    date(2025, 8, 15),  # Assomption
    date(2025, 11, 1),  # Toussaint
    date(2025, 11, 11), # Armistice 1918
    date(2025, 12, 25), # Noël
    date(2026, 1, 1),   # Jour de l'an
]


def get_week_number(d: date) -> int:
    """Retourne le numéro de semaine ISO"""
    return d.isocalendar()[1]


def is_even_week(d: date) -> bool:
    """Vérifie si la date est dans une semaine paire"""
    return get_week_number(d) % 2 == 0


def get_day_name(d: date) -> str:
    """Retourne le nom du jour en français"""
    days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    return days[d.weekday()]


def get_next_day(d: date, target_weekday: int) -> date:
    """Retourne la prochaine date pour un jour de la semaine donné"""
    days_ahead = target_weekday - d.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days_ahead)


def is_holiday_or_weekend(d: date) -> bool:
    """Vérifie si une date est un jour férié ou un weekend"""
    return d in JOURS_FERIES_2025_2026 or d.weekday() >= 5


def apply_holiday_shift(collection_date: date) -> tuple[date, bool, str | None]:
    """
    Applique le décalage en cas de jour férié.
    Retourne: (nouvelle_date, est_décalé, note)
    """
    if not is_holiday_or_weekend(collection_date):
        return collection_date, False, None

    shifted_date = collection_date
    shift_days = 0

    while is_holiday_or_weekend(shifted_date):
        shifted_date += timedelta(days=1)
        shift_days += 1

    if shift_days > 0:
        return shifted_date, True, f"Décalé de {shift_days} jour(s) à cause d'un jour férié"

    return collection_date, False, None


def generate_collections(start_date: date, end_date: date, cities: list[str]) -> list[schemas.CollectionCreate]:
    """Génère toutes les collectes pour la période donnée"""
    collections = []
    current_date = start_date

    while current_date <= end_date:
        week_num = get_week_number(current_date)
        is_even = is_even_week(current_date)
        weekday = current_date.weekday()

        for city in cities:
            # Ordures ménagères: Lundi (0) semaine paire
            if weekday == 0 and is_even:
                final_date, is_shifted, note = apply_holiday_shift(current_date)
                collections.append(schemas.CollectionCreate(
                    date=final_date,
                    waste_type=schemas.WasteType.ORDURES_MENAGERES,
                    city=city,
                    day_of_week=get_day_name(final_date),
                    week_number=week_num,
                    is_holiday_shift=is_shifted,
                    notes=note
                ))

            # Déchets recyclables: Jeudi (3) semaine impaire
            if weekday == 3 and not is_even:
                final_date, is_shifted, note = apply_holiday_shift(current_date)
                collections.append(schemas.CollectionCreate(
                    date=final_date,
                    waste_type=schemas.WasteType.DECHETS_RECYCLABLES,
                    city=city,
                    day_of_week=get_day_name(final_date),
                    week_number=week_num,
                    is_holiday_shift=is_shifted,
                    notes=note
                ))

        current_date += timedelta(days=1)

    return collections


@app.command()
def parse(
    pdf_path: str = typer.Option("data/calendar.pdf", "--pdf", "-p", help="Chemin vers le PDF calendrier"),
    cities: str = typer.Option("Nouvoitou,Saint-Armel", "--cities", "-c", help="Villes séparées par des virgules"),
    start_date: str = typer.Option("2024-10-01", "--start", "-s", help="Date de début (YYYY-MM-DD)"),
    end_date: str = typer.Option("2026-09-30", "--end", "-e", help="Date de fin (YYYY-MM-DD)")
):
    """Parse le calendrier PDF et peuple la base de données"""

    typer.echo(f"Parsing du calendrier: {pdf_path}")

    cities_list = [c.strip() for c in cities.split(",")]
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    typer.echo(f"Villes: {', '.join(cities_list)}")
    typer.echo(f"Période: {start} à {end}")

    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        typer.echo("Suppression des anciennes données...")
        crud.delete_all_collections(db)

        typer.echo("Génération des collectes...")
        collections = generate_collections(start, end, cities_list)

        typer.echo(f"Insertion de {len(collections)} collectes...")
        for collection in collections:
            crud.create_collection(db, collection)

        typer.echo(f"Terminé! {len(collections)} collectes insérées avec succès.")

        db_collections = crud.get_collections(db, limit=5)
        typer.echo("\nPremières collectes insérées:")
        for col in db_collections:
            typer.echo(f"  - {col.date} ({col.day_of_week}): {col.waste_type} - {col.city}")

    finally:
        db.close()


if __name__ == "__main__":
    app()
