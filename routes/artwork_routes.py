from __future__ import annotations


from pathlib import Path

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import login_required
from werkzeug.utils import secure_filename

import os
import config

bp = Blueprint("artwork", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


# ==========================================================================
# 1. Helpers
# ==========================================================================
def _unique_path(directory: Path, filename: str) -> Path:
    """Return a unique path in ``directory`` avoiding overwrite."""
    dest = directory / filename
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


# ==========================================================================
# 2. Upload Handling
# ==========================================================================
@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_artwork():
    """Handle new artwork file uploads."""
    if request.method == "POST":
        files = request.files.getlist("file")
        if not files:
            flash("❌ No file uploaded", "error")
            return redirect(request.url)
        for uploaded_file in files:
            filename = secure_filename(uploaded_file.filename or "")
            if not filename:
                flash("❌ Invalid file", "error")
                continue
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                flash(f"❌ Invalid file type: {filename}", "error")
                continue
            save_path = _unique_path(config.UNANALYSED_ARTWORK_DIR, filename)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            uploaded_file.save(save_path)
            flash(f"✅ Uploaded: {save_path.name}", "success")
        return redirect(url_for("artwork.upload_artwork"))
    return render_template(
        "upload.html",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
    )


# ==========================================================================
# 3. Image Serving Routes
# ==========================================================================
@bp.route("/unanalysed/<path:filename>")
@login_required
def unanalysed_image(filename: str):
    """Serve raw uploaded artwork awaiting analysis."""
    safe = secure_filename(filename)
    path = config.UNANALYSED_ARTWORK_DIR / safe
    if not path.exists():
        abort(404)
    return send_from_directory(config.UNANALYSED_ARTWORK_DIR, safe)


@bp.route("/processed/<path:filename>")
@login_required
def processed_image(filename: str):
    """Serve processed artwork images."""
    safe = secure_filename(filename)
    path = config.PROCESSED_ARTWORK_DIR / safe
    if not path.exists():
        abort(404)
    return send_from_directory(config.PROCESSED_ARTWORK_DIR, safe)


@bp.route("/finalised/<path:filename>")
@login_required
def finalised_image(filename: str):
    """Serve finalised artwork images."""
    safe = secure_filename(filename)
    path = config.FINALISED_ARTWORK_DIR / safe
    if not path.exists():
        abort(404)
    return send_from_directory(config.FINALISED_ARTWORK_DIR, safe)
