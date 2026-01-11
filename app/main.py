from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import date

from app import crud, models, schemas
from app.database import engine, get_db, SessionLocal
from fastapi.openapi.utils import get_openapi

models.Base.metadata.create_all(bind=engine)

# Default title/description; may be updated at startup with calendar year
DEFAULT_TITLE = "API Collectes de Déchets"
DEFAULT_DESCRIPTION = "API en lecture seule pour consulter les collectes de déchets"

app = FastAPI(
    title=DEFAULT_TITLE,
    description=DEFAULT_DESCRIPTION,
    version="1.0.0",
)


def custom_openapi():
    """Génère dynamiquement le schéma OpenAPI en intégrant l'année du calendrier
    depuis la table `metadata` si présente. Cela met à jour le titre affiché
    dans la page `/docs` sans nécessiter un redémarrage manuel.
    """
    # Try to read calendar_period (preferred) or calendar_year from DB
    calendar_period = None
    calendar_year = None
    try:
        db = SessionLocal()
        calendar_period = crud.get_metadata(db, "calendar_period")
        if not calendar_period:
            calendar_year = crud.get_metadata(db, "calendar_year")
    finally:
        try:
            db.close()
        except Exception:
            pass

    title = DEFAULT_TITLE
    description = DEFAULT_DESCRIPTION
    if calendar_period:
        title = f"{DEFAULT_TITLE} (calendrier {calendar_period})"
        # keep description generic — do not duplicate period to avoid repetition in /docs
        description = DEFAULT_DESCRIPTION
    elif calendar_year:
        title = f"{DEFAULT_TITLE} (calendrier {calendar_year})"
        description = DEFAULT_DESCRIPTION

    # Always regenerate schema so that changes to metadata are immediately visible
    openapi_schema = get_openapi(
        title=title,
        version=app.version,
        description=description,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
def read_root():
    """Page d'accueil de l'API"""
    # attempt to read calendar_period (preferred) or calendar_year from metadata
    calendar_period = None
    calendar_year = None
    try:
        db = SessionLocal()
        calendar_period = crud.get_metadata(db, "calendar_period")
        if not calendar_period:
            calendar_year = crud.get_metadata(db, "calendar_year")
    finally:
        try:
            db.close()
        except Exception:
            pass

    # show the period in the main message if available
    message = DEFAULT_TITLE
    if calendar_period:
        message = f"{DEFAULT_TITLE} — calendrier {calendar_period}"
    elif calendar_year:
        message = f"{DEFAULT_TITLE} — calendrier {calendar_year}"

    return {
        "message": message,
        "calendar_period": calendar_period,
        "calendar_year": calendar_year,
        "documentation": "/docs",
        "version": "1.0.0",
        "endpoints": {
            "collections": "/collections/",
            "next_collection": "/collections/next",
            "stats": "/collections/stats"
        }
    }






@app.on_event("startup")
def startup_read_metadata():
    """On startup, read metadata (calendar_year) and update the app title/description for docs display."""
    try:
        db = SessionLocal()
        year = crud.get_metadata(db, "calendar_year")
        if year:
            app.title = f"{DEFAULT_TITLE} (calendrier {year})"
            app.description = f"{DEFAULT_DESCRIPTION} — calendrier {year}"
    finally:
        try:
            db.close()
        except Exception:
            pass


@app.get("/collections/", response_model=list[schemas.CollectionResponse], tags=["Collections"])
def list_collections(
    skip: int = 0,
    limit: int = 100,
    waste_type: str | None = None,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    upcoming: bool = False,
    db: Session = Depends(get_db)
):
    """
    Lister les collectes avec filtres optionnels.

    - **skip**: Nombre d'éléments à ignorer (pagination)
    - **limit**: Nombre maximum d'éléments à retourner (max 100)
    - **waste_type**: Filtrer par type de déchet (ordures_menageres, dechets_recyclables, dechets_alimentaires)
    - **city**: Filtrer par ville (Nouvoitou, Saint-Armel)
    - **start_date**: Date de début (format YYYY-MM-DD)
    - **end_date**: Date de fin (format YYYY-MM-DD)
    - **upcoming**: Si True, ne retourne que les collectes futures
    """
    collections = crud.get_collections(
        db=db,
        skip=skip,
        limit=min(limit, 100),
        waste_type=waste_type,
        city=city,
        start_date=start_date,
        end_date=end_date,
        upcoming=upcoming
    )
    return collections


@app.get("/collections/next", response_model=schemas.CollectionResponse | None, tags=["Collections"])
def get_next_collection(
    waste_type: str | None = None,
    city: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Récupérer la prochaine collecte planifiée.

    - **waste_type**: Filtrer par type de déchet (optionnel)
    - **city**: Filtrer par ville (optionnel)
    """
    collection = crud.get_next_collection(db=db, waste_type=waste_type, city=city)
    return collection


@app.get("/collections/stats", response_model=schemas.CollectionStats, tags=["Collections"])
def get_stats(db: Session = Depends(get_db)):
    """
    Récupérer les statistiques sur les collectes.

    Retourne le nombre total de collectes, le nombre par type,
    et les prochaines collectes pour chaque type.
    """
    stats = crud.get_collections_stats(db=db)
    return stats


@app.get("/collections/{collection_id}", response_model=schemas.CollectionResponse, tags=["Collections"])
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    """
    Récupérer une collecte spécifique par son ID.

    - **collection_id**: ID de la collecte
    """
    collection = crud.get_collection(db=db, collection_id=collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collecte non trouvée")
    return collection
