"""Home and gallery routes.

Provides landing pages and the unanalysed artwork gallery.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from flask import Blueprint, redirect, render_template, url_for

import config
from routes import utils as routes_utils

bp = Blueprint("home", __name__)

logger = logging.getLogger(__name__)


@bp.route("/")
def root() -> "Response":
    """Redirect the base URL to /home."""
    return redirect(url_for("home.home"))


@bp.route("/home")
def home() -> str:
    """Render the application homepage."""
    return render_template(
        "home.html",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
    )


@bp.route("/artworks")
def artworks() -> str:
    """List all unanalysed artworks ready for processing."""
    try:
        artworks = routes_utils.get_all_unanalysed_artworks()
    except Exception as exc:  # pragma: no cover - defensive coding
        logger.error("Failed to collect unanalysed artworks: %s", exc)
        artworks = []

    for art in artworks:
        art["upload_date"] = datetime.fromtimestamp(art["timestamp"]).strftime(
            "%Y-%m-%d"
        )

    return render_template(
        "artworks.html",
        artworks=artworks,
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
        get_artwork_image_url=routes_utils.get_artwork_image_url,
    )


@bp.route("/finalised")
def finalised() -> str:
    """Render the finalised artworks page."""
    return render_template(
        "finalised.html",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
    )
