"""Blueprint for admin pages."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("admin/dashboard.html")


@bp.route("/security")
@login_required
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
@login_required
def manage_users():
    return render_template(
        "admin/users.html", users=[], config={"ADMIN_USERNAME": "admin"}
    )


@bp.route("/mockups")
@login_required
def mockups():
    return render_template("admin/mockups.html")


@bp.route("/coordinates")
@login_required
def coordinates():
    return render_template("admin/coordinates.html")
