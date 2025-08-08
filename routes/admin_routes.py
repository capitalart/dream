"""Blueprint for admin pages."""

from __future__ import annotations

from flask import Blueprint, render_template

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
def dashboard():
    return render_template("admin/dashboard.html")


@bp.route("/security")
def security_page():
    context = {
        "login_required": True,
        "active": 1,
        "max_sessions": 1,
        "remaining": 0,
        "no_cache": False,
        "cache_remaining": 0,
    }
    return render_template("admin/security.html", **context)


@bp.route("/users")
def manage_users():
    return render_template(
        "admin/users.html", users=[], config={"ADMIN_USERNAME": "admin"}
    )


@bp.route("/mockups")
def mockups():
    return render_template("admin/mockups.html")


@bp.route("/coordinates")
def coordinates():
    return render_template("admin/coordinates.html")
