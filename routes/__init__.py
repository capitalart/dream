"""HTTP route definitions for DreamArtMachine."""
from __future__ import annotations

from flask import Blueprint, request
from werkzeug.utils import secure_filename

from config import (
    UNANALYSED_ARTWORK_DIR,
    FINALISED_ARTWORK_DIR,
    sanitize_slug,
    finalised_artwork_path,
    mockup_path,
)

bp = Blueprint("routes", __name__)


@bp.route("/upload", methods=["POST"])
def upload() -> tuple[dict, int]:
    file = request.files.get("file")
    if not file or not file.filename:
        return {"error": "no file provided"}, 400
    filename = secure_filename(file.filename)
    destination = UNANALYSED_ARTWORK_DIR / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    file.save(destination)
    return {"filename": filename}, 201


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


@bp.route("/finalise/<slug>", methods=["POST"])
def finalise(slug: str) -> tuple[dict, int]:
    slug = sanitize_slug(slug)
    final_path = finalised_artwork_path(slug)
    if not final_path.exists():
        return {"error": "final image missing"}, 404
    return {"final": str(final_path)}, 200
