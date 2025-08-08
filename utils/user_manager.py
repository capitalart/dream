from __future__ import annotations

"""User management helpers backed by SQLAlchemy."""

from typing import Optional

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session

from db import Base, get_session
from utils.security import hash_password


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


def get_user(user_id: int) -> Optional[User]:
    session: Session = get_session()
    try:
        return session.get(User, user_id)
    finally:
        session.close()


def get_user_by_username(username: str) -> Optional[User]:
    session: Session = get_session()
    try:
        return session.query(User).filter_by(username=username).first()
    finally:
        session.close()


def create_user(username: str, password: str) -> User:
    session: Session = get_session()
    user = User(username=username, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    session.close()
    return user


def ensure_default_users() -> None:
    """Create default users if they do not exist."""
    session: Session = get_session()
    try:
        existing = session.query(User).count()
        if existing == 0:
            session.add(User(username="robbie", password_hash=hash_password("Kanga123!")))
            session.add(User(username="backup", password_hash=hash_password("DreamArt@2025")))
            session.commit()
    finally:
        session.close()
