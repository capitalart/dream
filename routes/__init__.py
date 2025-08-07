"""HTTP route definitions for DreamArtMachine."""

from __future__ import annotations

from flask import Blueprint
from werkzeug.utils import secure_filename

from config import (
    UNANALYSED_ARTWORK_DIR,
    FINALISED_ARTWORK_DIR,
    sanitize_slug,
    mockup_path,
)

bp = Blueprint("routes", __name__)


@bp.route("/analyze/<provider>/<filename>", methods=["POST"])
def analyze(provider: str, filename: str) -> tuple[dict, int]:
    sanitized = secure_filename(filename)
    target = UNANALYSED_ARTWORK_DIR / sanitized
    if not target.exists():
        return {"error": "file not found"}, 404
    return {"provider": provider, "filename": sanitized}, 200


@bp.route("/mockups/<slug>", methods=["POST"])
def mockups(slug: str) -> tuple[dict, int]:
    slug = sanitize_slug(slug)
    slug_dir = FINALISED_ARTWORK_DIR / slug
    slug_dir.mkdir(parents=True, exist_ok=True)
    files = [str(mockup_path(slug, i)) for i in range(1, 10)]
    return {"mockups": files}, 200
