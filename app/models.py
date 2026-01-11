from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Collection(Base):
    """Modèle pour une collecte de déchets"""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    waste_type = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    day_of_week = Column(String, nullable=False)
    week_number = Column(Integer, nullable=False)
    is_holiday_shift = Column(Boolean, default=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
