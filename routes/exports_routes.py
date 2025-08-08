"""Blueprint handling export-related pages."""
from __future__ import annotations

from flask import Blueprint, render_template

bp = Blueprint("exports", __name__, url_prefix="/exports")


@bp.route("/sellbrite")
def sellbrite() -> str:
    """Render the Sellbrite exports management page."""
    return render_template("exports/sellbrite.html")
