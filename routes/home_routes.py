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


@bp.route("/artworks")
@login_required
def artworks() -> str:
    """Render the artworks listing page."""
    return render_template("artworks.html")


@bp.route("/finalised")
@login_required
def finalised() -> str:
    """Render the finalised artworks page."""
    return render_template("finalised.html")
