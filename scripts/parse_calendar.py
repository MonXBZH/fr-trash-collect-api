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
import re
import pdfplumber
import holidays

app = typer.Typer()


# Dynamic holiday set (populated based on detected period or start/end)
HOLIDAY_SET: set[date] = set()


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
    """Vérifie si une date est un jour férié ou un weekend.

    Utilise `HOLIDAY_SET` s'il est renseigné (préféré). Sinon, considère
    uniquement le weekend comme jour non ouvrable.
    """
    return d.weekday() >= 5 or d in HOLIDAY_SET


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


def extract_calendar_period_from_pdf(pdf_path: str) -> str | None:
    """Extract a calendar period from the PDF.

    Attempts to find explicit ranges like "2025/2026", "2025-2026", "2025–2026",
    or infers the period from the set of years present in the text. Returns a
    string like "2025/2026" when possible, else returns a single year string
    like "2025" or None if nothing found.
    """
    try:
        years_found: dict[int, int] = {}
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                # First try to find explicit ranges like 2025/2026 or 2025-2026
                m_range = re.search(r"\b(20[0-9]{2})\s*[\/-–—]\s*(20[0-9]{2})\b", text)
                if m_range:
                    y1 = int(m_range.group(1))
                    y2 = int(m_range.group(2))
                    # normalize order
                    if y1 <= y2:
                        return f"{y1}/{y2}"
                    else:
                        return f"{y2}/{y1}"

                for m in re.findall(r"\b(20[0-9]{2})\b", text):
                    y = int(m)
                    years_found[y] = years_found.get(y, 0) + 1

        if not years_found:
            return None

        distinct_years = sorted(years_found.keys())
        # If two consecutive years present, return range
        if len(distinct_years) >= 2:
            # look for pair that are consecutive and have occurrences
            for i in range(len(distinct_years) - 1):
                a = distinct_years[i]
                b = distinct_years[i + 1]
                if b == a + 1:
                    return f"{a}/{b}"
        # Fallback: return the most frequent year
        return str(max(years_found.items(), key=lambda kv: kv[1])[0])
    except Exception:
        return None


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

        # Extract calendar period from PDF and store in metadata
        period = extract_calendar_period_from_pdf(pdf_path)
        if period:
            typer.echo(f"Période détectée dans le PDF: {period}")
            crud.set_metadata(db, "calendar_period", str(period))
            # also set calendar_year for backward compatibility (first year)
            first_year = period.split("/")[0]
            crud.set_metadata(db, "calendar_year", first_year)
        else:
            typer.echo("Aucune période extraite du PDF (fallback possible)")

        # If period was detected and the user didn't override start/end (used defaults),
        # adjust start/end to match the detected period, e.g. 2025/2026 -> 2025-10-01 / 2026-09-30
        try:
            DEFAULT_START = "2024-10-01"
            DEFAULT_END = "2026-09-30"
            if period and start_date == DEFAULT_START and end_date == DEFAULT_END:
                m = re.match(r"^(20[0-9]{2})(?:/(20[0-9]{2}))$", period)
                if m:
                    y1 = int(m.group(1))
                    y2 = int(m.group(2))
                    start = date(y1, 10, 1)
                    end = date(y2, 9, 30)
                    typer.echo(f"Ajustement automatique de la période: {start} à {end}")
        except Exception:
            # don't fail the whole parse on this
            pass

        # Build HOLIDAY_SET for the target years (prefer explicit period, else infer from start/end)
        try:
            years = set()
            if period:
                m = re.match(r"^(20[0-9]{2})(?:/(20[0-9]{2}))$", period)
                if m:
                    y1 = int(m.group(1))
                    y2 = int(m.group(2))
                    years.update(range(y1, y2 + 1))
                else:
                    years.add(int(period))
            else:
                # fallback: use years spanned by start/end
                years.update(range(start.year, end.year + 1))

            # populate global HOLIDAY_SET
            global HOLIDAY_SET
            HOLIDAY_SET = set()
            try:
                ch = holidays.CountryHoliday("FR", years=list(years))
                for d in ch.keys():
                    HOLIDAY_SET.add(d)
                typer.echo(f"Jours fériés chargés pour les années: {sorted(years)}")
            except Exception as e:
                typer.echo(f"Impossible de charger les jours fériés via python-holidays: {e}")
        except Exception:
            pass

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
