from __future__ import annotations

"""Authentication routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from utils.security import (
    current_user_id,
    login_user,
    logout_user,
    verify_password,
)
from utils.user_manager import get_user, get_user_by_username

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if user and verify_password(user.password_hash, password):
            login_user(user.id)
            return redirect(url_for("home.home"))
        flash("Invalid credentials", "error")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/healthz")
def health_check() -> tuple[str, int]:
    return "OK", 200


@bp.route("/whoami")
def whoami() -> tuple[str, int]:
    user_id = current_user_id()
    user = get_user(user_id) if user_id else None
    if user:
        return f"Logged in as: {user.username}", 200
    return "Unknown", 200
