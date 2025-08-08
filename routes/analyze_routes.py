# routes/analyze_routes.py
# ======================================================================
# Analyze Routes – JSON API endpoints for artwork analysis
# ======================================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, jsonify, request, current_app, url_for
from werkzeug.exceptions import BadRequest

import config
from services.artwork_analysis_service import analyze_artwork

bp = Blueprint("analysis", __name__)

# ----------------------------------------------------------------------
# POST /analyze/<aspect>/<path:filename>
# - <aspect> is a label like "square", "4x5", etc.
# - <filename> is a RELATIVE path under UNANALYSED_ARTWORK_DIR, e.g.
#       "test-art/test-art-ANALYSE.jpg"
# Returns JSON: { success: bool, redirect_url?: str, error?: str }
# ----------------------------------------------------------------------
@bp.post("/analyze/<aspect>/<path:filename>")
def analyze_route(aspect: str, filename: str):
    """
    Analyse an uploaded artwork and return redirect information as JSON.

    IMPORTANT:
    - Do NOT pass `filename` through `secure_filename` because we rely on the
      subfolder (slug) component, e.g. "slug/slug-ANALYSE.jpg".
    """
    provider = (request.form.get("provider") or "openai").strip().lower()

    # Build the real path inside UNANALYSED_ARTWORK_DIR safely
    rel = Path(filename)
    # Prevent any path escaping
    if rel.is_absolute() or ".." in rel.parts:
        raise BadRequest("Invalid filename")

    src_path = (config.UNANALYSED_ARTWORK_DIR / rel).resolve()
    root_real = config.UNANALYSED_ARTWORK_DIR.resolve()
    if not str(src_path).startswith(str(root_real)):
        raise BadRequest("Invalid path scope")

    if not src_path.exists():
        current_app.logger.error("File not found during analysis: %s", rel)
        return jsonify({"error": "file not found"}), 404

    # Derive slug and the actual filename for downstream helpers
    slug = rel.parts[0]
    fname = rel.name

    try:
        # Let the service do the heavy lifting. We pass the resolved path so it
        # never has to reconstruct using underscores etc.
        result_slug = analyze_artwork(
            rel_path=str(rel),          # keep a stable, portable relative path
            src_path=src_path,          # absolute path to the ANALYSE image
            aspect=aspect,
            provider=provider,
            slug_hint=slug,             # hint for SKU/slug logic if needed
            filename_hint=fname,        # hint for logging
        )
    except Exception as exc:  # noqa: BLE001 – we want a JSON 500 with log
        current_app.logger.exception("Analysis failed for %s", rel)
        return jsonify({"error": str(exc)}), 500

    # Where to send the user next
    to_slug = result_slug or slug
    edit_url = url_for("finalise.edit_listing", slug=to_slug)
    return jsonify({"success": True, "redirect_url": edit_url}), 200
