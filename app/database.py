from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Ensure data directory exists so SQLite can create the DB there
DB_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
os.makedirs(DB_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URL = "sqlite:///./data/trash_collection.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency pour obtenir une session de base de données"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
