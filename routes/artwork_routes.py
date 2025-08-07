"""Routes for uploading artwork files."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

import config

bp = Blueprint("artwork", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def _unique_path(directory: Path, filename: str) -> Path:
    """Return a path that does not overwrite existing files."""
    dest = directory / filename
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


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
    return render_template("upload.html")
