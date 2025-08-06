"""Blueprint for artwork finalisation routes."""
from __future__ import annotations

import json
import logging
from typing import Dict

from flask import Blueprint, redirect, render_template, request, url_for

from config import MASTER_ARTWORK_PATHS_FILE, sanitize_slug
from services.finalise_service import finalise_artwork
from scripts.generate_composites import generate as regenerate_mockups

bp = Blueprint("finalise", __name__)

logger = logging.getLogger(__name__)

COLOURS = ["red", "blue", "green", "black", "white"]


def _load_metadata(slug: str) -> Dict[str, str]:
    data: Dict[str, Dict[str, str]] = {}
    if MASTER_ARTWORK_PATHS_FILE.exists():
        try:
            with MASTER_ARTWORK_PATHS_FILE.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:  # pragma: no cover
            logger.exception("Failed reading %s", MASTER_ARTWORK_PATHS_FILE)
    record = data.get(slug, {})
    return {
        "title": record.get("title", ""),
        "description": record.get("description", ""),
        "primary_colour": record.get("primary_colour", ""),
        "secondary_colour": record.get("secondary_colour", ""),
    }


@bp.route("/edit-listing/<slug>", methods=["GET"])
def edit_listing(slug: str):
    slug = sanitize_slug(slug)
    return render_template("edit_listing.html", slug=slug)


@bp.route("/review/<slug>", methods=["GET"])
def review(slug: str):
    slug = sanitize_slug(slug)
    metadata = _load_metadata(slug)
    return render_template(
        "review_artwork.html",
        slug=slug,
        colours=COLOURS,
        **metadata,
    )


@bp.route("/finalise/<slug>", methods=["POST"])
def finalise(slug: str):
    slug = sanitize_slug(slug)
    action = request.form.get("action")
    if action == "regenerate":
        regenerate_mockups(slug)
        logger.info("Regenerated mockups for %s", slug)
        return redirect(url_for("finalise.review", slug=slug))

    metadata = {
        "title": request.form.get("title", ""),
        "description": request.form.get("description", ""),
        "primary_colour": request.form.get("primary_colour", ""),
        "secondary_colour": request.form.get("secondary_colour", ""),
    }
    try:
        finalise_artwork(slug, metadata)
    except FileNotFoundError:
        logger.error("Finalisation failed for %s", slug)
        return {"error": "required files missing"}, 400
    return redirect(url_for("finalise.review", slug=slug))
