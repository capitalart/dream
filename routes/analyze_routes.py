import logging

from flask import Blueprint, jsonify, request, url_for
from werkzeug.utils import secure_filename

from services.artwork_analysis_service import analyze_artwork
from scripts.generate_composites import generate as generate_mockups

bp = Blueprint("analysis", __name__)

logger = logging.getLogger(__name__)


@bp.route("/process-analysis-vision/", methods=["POST"])
def process_analysis_vision() -> tuple[dict, int]:
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    if not filename:
        return {"error": "filename required"}, 400
    filename = secure_filename(filename)
    try:
        slug = analyze_artwork(filename)
        generate_mockups(slug)
    except FileNotFoundError:
        logger.error("File not found during analysis: %s", filename)
        return {"error": "file not found"}, 404

    return {"slug": slug, "status": "complete"}, 200


# ==========================================================================
# New Analyze Route
# ==========================================================================
@bp.route("/analyze/<aspect>/<filename>", methods=["POST"])
def analyze_route(aspect: str, filename: str):
    """Analyse an uploaded artwork and return redirect info."""
    safe_name = secure_filename(filename)
    provider = request.form.get("provider", "openai").lower()
    try:
        slug = analyze_artwork(safe_name)
        generate_mockups(slug)
    except FileNotFoundError:
        logger.error("File not found during analysis: %s", safe_name)
        return jsonify({"error": "file not found"}), 404
    redirect_url = url_for(
        "artwork.edit_listing", aspect=aspect, filename=f"{slug}.jpg"
    )
    return jsonify(
        {"success": True, "provider": provider, "redirect_url": redirect_url}
    )
