from __future__ import annotations

"""Database setup for DreamArtMachine."""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

from config import DB_PATH

engine = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))
Base = declarative_base()


def init_db() -> None:
    """Create database tables."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Return a new database session."""
    return SessionLocal()
