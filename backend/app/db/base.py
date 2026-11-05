import datetime as dt
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

# Register date adapters for sqlite3 to prevent Python 3.12+ deprecation warnings
if hasattr(sqlite3, "register_adapter"):
    sqlite3.register_adapter(dt.date, lambda d: d.isoformat())
    sqlite3.register_adapter(dt.datetime, lambda d: d.isoformat())

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    __table_args__ = {"extend_existing": True}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401  (registers metadata)
    Base.metadata.create_all(bind=engine)
