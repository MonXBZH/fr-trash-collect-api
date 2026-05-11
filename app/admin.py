"""
Routeur admin pour l'upload de PDFs de calendrier.
Protégé par clé API via le header X-Admin-Key.

Workflow en 2 étapes :
  1. POST /admin/detect  — upload le PDF, retourne les villes détectées + un token
  2. POST /admin/import  — importe les villes choisies depuis le PDF (via le token)
"""

import os
import re
import shutil
import tempfile
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

import holidays as holidays_lib
from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud

router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

# Répertoire temporaire pour stocker les PDFs en attente d'import
_PENDING_DIR = Path(tempfile.gettempdir()) / "trash_api_pending"
_PENDING_DIR.mkdir(exist_ok=True)


ADMIN_PORTAL_HTML = """
<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Portail Admin - Upload Calendrier</title>
    <style>
        :root {
            --bg: #f4f7fb;
            --surface: #ffffff;
            --text: #1f2937;
            --muted: #6b7280;
            --accent: #0b6bcb;
            --accent-2: #084b8a;
            --ok: #0f766e;
            --err: #b91c1c;
            --border: #dbe3ee;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at top right, #dff1ff 0%, rgba(223,241,255,0) 40%),
                radial-gradient(circle at bottom left, #ffeccd 0%, rgba(255,236,205,0) 30%),
                var(--bg);
            min-height: 100vh;
            padding: 24px;
        }
        .card {
            max-width: 760px;
            margin: 0 auto;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 12px 28px rgba(16, 24, 40, 0.08);
        }
        h1 { margin: 0 0 6px 0; font-size: 1.6rem; }
        .subtitle { color: var(--muted); margin: 0 0 16px 0; }
        .grid { display: grid; gap: 12px; }
        .field { display: grid; gap: 6px; }
        label { font-weight: 600; }
        input[type="password"], input[type="file"] {
            width: 100%;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px;
            background: #fff;
        }
        .row { display: flex; gap: 10px; flex-wrap: wrap; }
        button {
            border: 0;
            border-radius: 10px;
            padding: 10px 14px;
            font-weight: 600;
            cursor: pointer;
            background: var(--accent);
            color: #fff;
        }
        button.secondary { background: #475569; }
        button:hover { background: var(--accent-2); }
        .pill {
            display: inline-block;
            background: #edf4ff;
            color: #1d4f91;
            border: 1px solid #cfe2ff;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.9rem;
        }
        .cities {
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            background: #fbfdff;
            display: grid;
            gap: 8px;
            max-height: 220px;
            overflow: auto;
        }
        .city-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .log {
            white-space: pre-wrap;
            margin-top: 14px;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 12px;
            background: #f8fafc;
            color: #0f172a;
            min-height: 80px;
        }
        .ok { color: var(--ok); }
        .err { color: var(--err); }
        .hidden { display: none; }
    </style>
</head>
<body>
    <main class="card">
        <h1>Portail Admin</h1>
        <p class="subtitle">Uploader un PDF, detecter les villes, puis lancer l'import.</p>

        <div class="grid">
            <div class="field">
                <label for="apiKey">Cle admin (header x-admin-key)</label>
                <input id="apiKey" type="password" autocomplete="off" placeholder="Votre cle admin" />
            </div>

            <div class="field">
                <label for="pdfFile">PDF calendrier</label>
                <input id="pdfFile" type="file" accept="application/pdf" />
            </div>

            <div class="row">
                <button id="detectBtn">1) Detecter les villes</button>
                <button id="selectAllBtn" class="secondary" type="button">Tout selectionner</button>
            </div>

            <div>
                <span id="periodPill" class="pill hidden"></span>
            </div>

            <div id="citiesBox" class="cities hidden"></div>

            <div class="row">
                <button id="importBtn" type="button">2) Importer la selection</button>
            </div>
        </div>

        <div id="log" class="log">Pret.</div>
    </main>

    <script>
        const apiKeyEl = document.getElementById("apiKey");
        const pdfFileEl = document.getElementById("pdfFile");
        const detectBtn = document.getElementById("detectBtn");
        const selectAllBtn = document.getElementById("selectAllBtn");
        const importBtn = document.getElementById("importBtn");
        const citiesBox = document.getElementById("citiesBox");
        const periodPill = document.getElementById("periodPill");
        const logEl = document.getElementById("log");

        let currentToken = null;

        function setLog(message, isError = false) {
            logEl.textContent = message;
            logEl.classList.toggle("err", isError);
            logEl.classList.toggle("ok", !isError);
        }

        function getCheckedCities() {
            return Array.from(citiesBox.querySelectorAll("input[type='checkbox']:checked"))
                .map((el) => el.value);
        }

        function renderCities(cities) {
            citiesBox.innerHTML = "";
            if (!cities || cities.length === 0) {
                citiesBox.classList.add("hidden");
                setLog("Aucune ville detectee dans ce PDF.", true);
                return;
            }

            for (const city of cities) {
                const row = document.createElement("label");
                row.className = "city-item";

                const cb = document.createElement("input");
                cb.type = "checkbox";
                cb.value = city;
                cb.checked = true;

                const text = document.createElement("span");
                text.textContent = city;

                row.appendChild(cb);
                row.appendChild(text);
                citiesBox.appendChild(row);
            }

            citiesBox.classList.remove("hidden");
        }

        detectBtn.addEventListener("click", async (event) => {
            event.preventDefault();
            const key = apiKeyEl.value.trim();
            const file = pdfFileEl.files?.[0];

            if (!key) {
                setLog("Saisis la cle admin.", true);
                return;
            }
            if (!file) {
                setLog("Selectionne un PDF.", true);
                return;
            }

            const formData = new FormData();
            formData.append("file", file);

            setLog("Detection en cours...");
            try {
                const response = await fetch("/admin/detect", {
                    method: "POST",
                    headers: { "x-admin-key": key },
                    body: formData,
                });

                const data = await response.json();
                if (!response.ok) {
                    setLog(`Erreur detect: ${data.detail || response.status}`, true);
                    return;
                }

                currentToken = data.token;
                renderCities(data.cities_detected || []);

                if (data.period_detected) {
                    periodPill.textContent = `Periode: ${data.period_detected}`;
                    periodPill.classList.remove("hidden");
                } else {
                    periodPill.classList.add("hidden");
                }

                setLog(`Detection OK. Token: ${data.token}`);
            } catch (error) {
                setLog(`Erreur reseau detect: ${error}`, true);
            }
        });

        selectAllBtn.addEventListener("click", () => {
            for (const cb of citiesBox.querySelectorAll("input[type='checkbox']")) {
                cb.checked = true;
            }
            setLog("Toutes les villes sont selectionnees.");
        });

        importBtn.addEventListener("click", async () => {
            const key = apiKeyEl.value.trim();
            const cities = getCheckedCities();

            if (!key) {
                setLog("Saisis la cle admin.", true);
                return;
            }
            if (!currentToken) {
                setLog("Fais d'abord l'etape de detection.", true);
                return;
            }
            if (cities.length === 0) {
                setLog("Selectionne au moins une ville.", true);
                return;
            }

            setLog("Import en cours...");
            try {
                const response = await fetch("/admin/import", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "x-admin-key": key,
                    },
                    body: JSON.stringify({ token: currentToken, cities }),
                });

                const data = await response.json();
                if (!response.ok) {
                    setLog(`Erreur import: ${data.detail || response.status}`, true);
                    return;
                }

                setLog(
                    `Import termine. Villes: ${data.cities.join(", ")} | Periode: ${data.period} | Lignes traitees: ${data.collections_inserted_or_updated}`
                );
            } catch (error) {
                setLog(`Erreur reseau import: ${error}`, true);
            }
        });
    </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def verify_api_key(x_admin_key: str = Header(..., description="Clé API admin")):
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY non configurée sur le serveur")
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_parser():
    """Importe le module parse_calendar de façon tardive pour éviter les imports circulaires."""
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    import scripts.parse_calendar as pc
    return pc


def _run_import(pdf_path: str, cities: list[str], db: Session) -> dict:
    """Détecte la période, charge les jours fériés et insère les collectes via upsert."""
    pc = _load_parser()

    period = pc.extract_calendar_period_from_pdf(pdf_path)

    if period:
        crud.set_metadata(db, "calendar_period", str(period))
        first_year = period.split("/")[0]
        crud.set_metadata(db, "calendar_year", first_year)
        m = re.match(r"^(20[0-9]{2})(?:/(20[0-9]{2}))$", period)
        if m:
            y1, y2 = int(m.group(1)), int(m.group(2))
            start: date = date(y1, 10, 1)
            end: date = date(y2, 9, 30)
        else:
            y = int(period)
            start = date(y, 1, 1)
            end = date(y, 12, 31)
    else:
        today = date.today()
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)

    # Charger les jours fériés
    years = set(range(start.year, end.year + 1))
    pc.HOLIDAY_SET = set()
    try:
        ch = holidays_lib.CountryHoliday("FR", years=list(years))
        for d in ch.keys():
            pc.HOLIDAY_SET.add(d)
    except Exception:
        pass

    collections = pc.generate_collections(start, end, cities)
    for collection in collections:
        crud.create_collection(db, collection)

    return {
        "cities": cities,
        "period": period or "inconnue",
        "collections_inserted_or_updated": len(collections),
    }


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class ImportRequest(BaseModel):
    token: str
    cities: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/portal",
    include_in_schema=False,
)
def admin_portal():
    """UI web minimale pour piloter l'upload et l'import via les endpoints admin."""
    return HTMLResponse(content=ADMIN_PORTAL_HTML)

@router.post(
    "/detect",
    summary="Uploader un PDF et détecter les villes",
    description=(
        "Uploade un PDF de calendrier, détecte les villes présentes dans les en-têtes "
        "et retourne un **token** à passer à `POST /admin/import` pour lancer l'import. "
        "Le token est valide le temps de la session serveur."
    ),
)
async def detect_cities(
    file: UploadFile = File(..., description="Fichier PDF du calendrier"),
    _: None = Depends(verify_api_key),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

    token = str(uuid.uuid4())
    dest = _PENDING_DIR / f"{token}.pdf"

    with dest.open("wb") as f:
        f.write(await file.read())

    pc = _load_parser()
    cities = pc.extract_cities_from_pdf(str(dest))
    period = pc.extract_calendar_period_from_pdf(str(dest))

    return {
        "token": token,
        "filename": file.filename,
        "period_detected": period or "non détectée",
        "cities_detected": cities,
        "hint": "Passez le token et votre sélection de villes à POST /admin/import",
    }


@router.post(
    "/import",
    summary="Importer les villes sélectionnées depuis un PDF uploadé",
    description=(
        "Lance l'import des collectes pour les **villes choisies** depuis un PDF "
        "préalablement uploadé via `POST /admin/detect`. "
        "Les données des autres villes en base ne sont pas affectées (upsert)."
    ),
)
def import_cities(
    body: ImportRequest,
    _: None = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    pdf_path = _PENDING_DIR / f"{body.token}.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Token invalide ou expiré. Veuillez re-uploader le PDF via /admin/detect.",
        )

    if not body.cities:
        raise HTTPException(status_code=400, detail="Aucune ville sélectionnée")

    result = _run_import(str(pdf_path), body.cities, db)

    # Nettoyage du fichier temporaire après import réussi
    try:
        pdf_path.unlink()
    except Exception:
        pass

    return result
