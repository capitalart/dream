from __future__ import annotations

"""Security helpers for authentication."""

from typing import Optional

from flask import session
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a secure password hash."""
    return pwd_context.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    """Verify a provided password against the stored hash."""
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


def login_user(user_id: int) -> None:
    """Store the user in the session."""
    session["user_id"] = user_id


def logout_user() -> None:
    """Remove the user from the session."""
    session.pop("user_id", None)


def current_user_id() -> Optional[int]:
    """Return the currently logged-in user's ID, if any."""
    return session.get("user_id")


def is_authenticated() -> bool:
    """Return True if a user is logged in."""
    return current_user_id() is not None
