from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Database URL: default to a local SQLite file, but allow override via env var
DB_URL = os.getenv("HUNTER_POSSE_DATABASE_URL", "sqlite:///hunter_posse.db")

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a database session; useful for dependency injection or quick helpers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
