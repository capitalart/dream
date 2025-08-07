from __future__ import annotations


"""Artwork upload and serving routes.

This module handles incoming uploads, derivative generation and the serving of
images at various stages of the workflow.
"""

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import login_required
from werkzeug.utils import secure_filename, safe_join

import json
import os
from typing import List

from PIL import Image

import config
from services.sku_service import get_next_sku

bp = Blueprint("artwork", __name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


# ==========================================================================
# 1. Helpers
# ==========================================================================
def _unique_slug(base: Path, slug: str) -> Path:
    """Return a unique directory path for ``slug`` within ``base``."""
    candidate = base / slug
    counter = 1
    while candidate.exists():
        candidate = base / f"{slug}-{counter}"
        counter += 1
    return candidate


def _resize_long_edge(img: Image.Image, long_edge: int) -> Image.Image:
    """Return a copy of ``img`` resized to ``long_edge`` on the longest side."""
    w, h = img.size
    if max(w, h) <= long_edge:
        return img.copy()
    if w >= h:
        new_w = long_edge
        new_h = int(long_edge * h / w)
    else:
        new_h = long_edge
        new_w = int(long_edge * w / h)
    return img.resize((new_w, new_h), Image.LANCZOS)


def _dominant_colours(img: Image.Image, count: int = 5) -> List[str]:
    """Return up to ``count`` dominant colours as hex strings."""
    small = img.convert("RGB").resize((100, 100))
    colours = small.getcolors(10000) or []
    colours.sort(reverse=True, key=lambda c: c[0])
    return ["#%02x%02x%02x" % tuple(colour[1]) for colour in colours[:count]]


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def _serve_from_base(base: Path, subpath: str):
    try:
        full = Path(safe_join(str(base), subpath))
    except Exception:
        abort(404)
    if not full.exists():
        abort(404)
    return send_file(full)


# ==========================================================================
# 2. Upload Handling
# ==========================================================================
@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_artwork():
    """Handle new artwork file uploads with derivative generation."""
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

            slug = config.sanitize_slug(Path(filename).stem)
            target_dir = _unique_slug(config.UNANALYSED_ARTWORK_DIR, slug)
            target_dir.mkdir(parents=True, exist_ok=True)

            sku = get_next_sku(config.SKU_TRACKER)
            original_path = target_dir / filename
            uploaded_file.save(original_path)

            with Image.open(original_path) as img:
                img = img.convert("RGB")
                thumb_img = _resize_long_edge(img, 2000)
                analyse_img = _resize_long_edge(img, 3800)
                thumb_path = target_dir / f"{sku}-THUMB.jpg"
                analyse_path = target_dir / f"{sku}-ANALYSE.jpg"
                thumb_img.save(thumb_path, "JPEG", quality=90)
                analyse_img.save(analyse_path, "JPEG", quality=95)
                qc = {
                    "width": analyse_img.width,
                    "height": analyse_img.height,
                    "mode": analyse_img.mode,
                    "dominant_colours": _dominant_colours(analyse_img),
                }

            meta = {
                "sku": sku,
                "original_filename": filename,
                "slug": target_dir.name,
                "thumb_path": f"{target_dir.name}/{thumb_path.name}",
                "analyse_path": f"{target_dir.name}/{analyse_path.name}",
                "qc": qc,
            }
            qc_path = target_dir / f"{sku}-QC.json"
            _write_json(qc_path, meta)
            flash(f"✅ Uploaded: {filename} as {sku}", "success")
        return redirect(url_for("home.artworks"))

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
    return _serve_from_base(config.UNANALYSED_ARTWORK_DIR, filename)


@bp.route("/processed/<path:filename>")
@login_required
def processed_image(filename: str):
    """Serve processed artwork images."""
    return _serve_from_base(config.PROCESSED_ARTWORK_DIR, filename)


@bp.route("/finalised/<path:filename>")
@login_required
def finalised_image(filename: str):
    """Serve finalised artwork images."""
    return _serve_from_base(config.FINALISED_ARTWORK_DIR, filename)
