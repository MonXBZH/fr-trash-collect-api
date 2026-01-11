from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from enum import Enum


class WasteType(str, Enum):
    """Types de déchets collectés"""
    ORDURES_MENAGERES = "ordures_menageres"
    DECHETS_RECYCLABLES = "dechets_recyclables"
    DECHETS_ALIMENTAIRES = "dechets_alimentaires"


class CollectionBase(BaseModel):
    """Schéma de base pour une collecte"""
    date: date
    waste_type: WasteType
    city: str
    day_of_week: str
    week_number: int


class CollectionCreate(CollectionBase):
    """Schéma pour créer une collecte (utilisé par le parser)"""
    is_holiday_shift: bool = False
    notes: str | None = None


class CollectionResponse(CollectionBase):
    """Schéma de réponse API pour une collecte"""
    id: int
    is_holiday_shift: bool
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionStats(BaseModel):
    """Statistiques sur les collectes"""
    total_collections: int
    collections_by_type: dict[str, int]
    next_ordures_menageres: CollectionResponse | None
    next_dechets_recyclables: CollectionResponse | None
