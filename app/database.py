from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./trash_collection.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency pour obtenir une session de base de données"""
    db = SessionLocal()
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    import os

    # Stocker la DB dans le répertoire `data/` (permet de persister via volume)
    DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
    DB_DIR = os.path.normpath(DB_DIR)
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
