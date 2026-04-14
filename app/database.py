from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

_db_url = settings.DATABASE_URL
_is_sqlite = _db_url.startswith("sqlite")

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import package so every model registers on Base.metadata before create_all
    from app import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        # Multiple uvicorn workers can race on SQLite DDL ("table … already exists").
        orig = getattr(exc, "orig", exc)
        if "already exists" not in str(orig).lower():
            raise
