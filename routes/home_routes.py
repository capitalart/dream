"""Homepage routes for DreamArtMachine."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import login_required

bp = Blueprint("home", __name__)


@bp.route("/")
@login_required
def root() -> "Response":
    """Redirect the base URL to /home."""
    return redirect(url_for("home.home"))


@bp.route("/home")
@login_required
def home() -> str:
    """Render the application homepage."""
    return render_template("home.html")
