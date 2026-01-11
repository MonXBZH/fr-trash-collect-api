from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date
from app import models, schemas


def get_collection(db: Session, collection_id: int):
    """Récupérer une collecte par son ID"""
    return db.query(models.Collection).filter(models.Collection.id == collection_id).first()


def get_collections(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    waste_type: str | None = None,
    city: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    upcoming: bool = False,
):
    """Récupérer une liste de collectes avec filtres optionnels"""
    query = db.query(models.Collection)

    if waste_type:
        query = query.filter(models.Collection.waste_type == waste_type)

    if city:
        query = query.filter(models.Collection.city == city)

    if start_date:
        query = query.filter(models.Collection.date >= start_date)

    if end_date:
        query = query.filter(models.Collection.date <= end_date)

    if upcoming:
        today = date.today()
        query = query.filter(models.Collection.date >= today)

    return query.order_by(models.Collection.date).offset(skip).limit(limit).all()


def get_next_collection(
    db: Session,
    waste_type: str | None = None,
    city: str | None = None,
):
    """Récupérer la prochaine collecte"""
    today = date.today()
    query = db.query(models.Collection).filter(models.Collection.date >= today)

    if waste_type:
        query = query.filter(models.Collection.waste_type == waste_type)

    if city:
        query = query.filter(models.Collection.city == city)

    return query.order_by(models.Collection.date).first()


def get_collections_stats(db: Session):
    """Récupérer les statistiques des collectes"""
    total = db.query(models.Collection).count()

    collections_by_type = {}
    for waste_type in schemas.WasteType:
        count = db.query(models.Collection).filter(
            models.Collection.waste_type == waste_type.value
        ).count()
        collections_by_type[waste_type.value] = count

    today = date.today()
    next_ordures = db.query(models.Collection).filter(
        and_(
            models.Collection.date >= today,
            models.Collection.waste_type == schemas.WasteType.ORDURES_MENAGERES.value
        )
    ).order_by(models.Collection.date).first()

    next_recyclables = db.query(models.Collection).filter(
        and_(
            models.Collection.date >= today,
            models.Collection.waste_type == schemas.WasteType.DECHETS_RECYCLABLES.value
        )
    ).order_by(models.Collection.date).first()

    return {
        "total_collections": total,
        "collections_by_type": collections_by_type,
        "next_ordures_menageres": next_ordures,
        "next_dechets_recyclables": next_recyclables,
    }


def create_collection(db: Session, collection: schemas.CollectionCreate):
    """Créer une nouvelle collecte (utilisé par le parser)"""
    db_collection = models.Collection(**collection.model_dump())
    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)
    return db_collection


def delete_all_collections(db: Session):
    """Supprimer toutes les collectes (utilisé par le parser pour réinitialiser)"""
    db.query(models.Collection).delete()
    db.commit()


def get_metadata(db: Session, key: str) -> str | None:
    """Récupérer une valeur metadata par clé"""
    row = db.query(models.Metadata).filter(models.Metadata.key == key).first()
    return row.value if row else None


def set_metadata(db: Session, key: str, value: str) -> None:
    """Créer ou mettre à jour une clé metadata"""
    row = db.query(models.Metadata).filter(models.Metadata.key == key).first()
    if row:
        row.value = value
    else:
        row = models.Metadata(key=key, value=value)
        db.add(row)
    db.commit()
