"""Home and gallery routes.

Provides landing pages and the unanalysed artwork gallery.
"""

from __future__ import annotations

import logging
import os
import json
import shutil
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

import config
from routes import utils as routes_utils

bp = Blueprint("home", __name__)

logger = logging.getLogger(__name__)


@bp.route("/")
@login_required
def root() -> "Response":
    """Redirect the base URL to /home."""
    return redirect(url_for("home.home"))


@bp.route("/home")
@login_required
def home() -> str:
    """Render the application homepage."""
    return render_template(
        "home.html",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
    )


@bp.route("/artworks")
@login_required
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


@bp.post("/artworks/delete-unanalysed/<slug>")
@login_required
def delete_unanalysed_artwork(slug: str):
    slug = config.sanitize_slug(slug)
    folder = config.UNANALYSED_ARTWORK_DIR / slug
    removed = False
    try:
        if folder.exists():
            shutil.rmtree(folder)
            removed = True

        registry_path = getattr(
            config, "OUTPUT_JSON", getattr(config, "MASTER_ARTWORK_PATHS_FILE", None)
        )
        reg = {}
        if registry_path and registry_path.exists():
            try:
                reg = json.loads(registry_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                reg = {}

        to_delete = []
        for key, rec in reg.items():
            cur = "|".join(
                [rec.get("image", ""), rec.get("analysis", ""), rec.get("openai", "")]
            )
            if f"/{slug}/" in cur or key == slug:
                to_delete.append(key)
        for k in to_delete:
            reg.pop(k, None)

        if registry_path:
            tmp = registry_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(reg, indent=2), encoding="utf-8")
            os.replace(tmp, registry_path)

        flash(("Deleted" if removed else "Nothing to delete") + f" for {slug}", "success")
    except Exception as exc:  # pragma: no cover - defensive
        flash(f"Delete failed for {slug}: {exc}", "danger")
    return redirect(url_for("home.artworks"))


@bp.route("/finalised")
@login_required
def finalised() -> str:
    """Render the finalised artworks page."""
    return render_template(
        "finalised.html",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
    )
