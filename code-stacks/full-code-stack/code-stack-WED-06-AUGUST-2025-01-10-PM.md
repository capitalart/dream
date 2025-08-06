# FULL CODE STACK (WED-06-AUGUST-2025-01-10-PM)


---
## app.py
---
"""Flask application for DreamArtMachine."""
from __future__ import annotations

from flask import Flask

from config import configure_logging
from routes import bp as routes_bp


def create_app() -> Flask:
    """Application factory."""
    configure_logging()
    app = Flask(__name__)
    app.register_blueprint(routes_bp)
    return app


app = create_app()


---
## config.py
---
"""Configuration for DreamArtMachine application."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import re
from pathlib import Path

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()  # type: ignore
except Exception:  # pragma: no cover
    pass

# Base directory for all operations
BASE_DIR = Path(os.getenv("DREAM_HOME", "/home/dream")).resolve()

# Core folder structure
ART_PROCESSING_DIR = BASE_DIR / "art-processing"
UNANALYSED_ARTWORK_DIR = ART_PROCESSING_DIR / "unanalysed-artwork"
PROCESSED_ARTWORK_DIR = BASE_DIR / "processed-artwork"
FINALISED_ARTWORK_DIR = BASE_DIR / "finalised-artwork"
LOG_DIR = BASE_DIR / "logs"
INPUTS_DIR = BASE_DIR / "inputs"
MOCKUPS_DIR = INPUTS_DIR / "mockups"
MASTER_ARTWORK_PATHS_FILE = BASE_DIR / "master-artwork-paths.json"

# Ensure required directories exist
for directory in [
    UNANALYSED_ARTWORK_DIR,
    PROCESSED_ARTWORK_DIR,
    FINALISED_ARTWORK_DIR,
    LOG_DIR,
    MOCKUPS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# Logging configuration
LOG_FILE = LOG_DIR / "app.log"


def configure_logging() -> None:
    """Set up application-wide logging."""
    logger = logging.getLogger()
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


_slug_re = re.compile(r"[^a-zA-Z0-9-]+")


def sanitize_slug(text: str) -> str:
    """Return a filesystem-safe slug."""
    slug = _slug_re.sub("-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def finalised_artwork_path(slug: str) -> Path:
    return FINALISED_ARTWORK_DIR / slug / f"{slug}.jpg"


def mockup_path(slug: str, index: int) -> Path:
    return FINALISED_ARTWORK_DIR / slug / f"{slug}-MU-{index:02d}.jpg"


def thumb_path(slug: str) -> Path:
    return FINALISED_ARTWORK_DIR / slug / f"{slug}-thumb.jpg"


def preview_path(slug: str) -> Path:
    return FINALISED_ARTWORK_DIR / slug / f"{slug}-thumb.jpg"


def openai_path(slug: str) -> Path:
    return FINALISED_ARTWORK_DIR / slug / f"{slug}-openai.jpg"


def processed_artwork_path(slug: str) -> Path:
    return PROCESSED_ARTWORK_DIR / slug / f"{slug}.jpg"


def processed_analysis_path(slug: str) -> Path:
    return PROCESSED_ARTWORK_DIR / slug / f"{slug}-analysis.json"


def processed_openai_path(slug: str) -> Path:
    return PROCESSED_ARTWORK_DIR / slug / f"{slug}-openai.jpg"


---
## requirements.txt
---
blinker==1.9.0
click==8.2.1
Flask==3.1.1
git-filter-repo==2.47.0
gunicorn==23.0.0
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.2
packaging==25.0
pillow==11.3.0
python-dotenv==1.1.1
Werkzeug==3.1.3
openai>=1.0.0


---
## routes/__init__.py
---
"""HTTP route definitions for DreamArtMachine."""
from __future__ import annotations

from flask import Blueprint, request
from werkzeug.utils import secure_filename

from config import UNANALYSED_ARTWORK_DIR, FINALISED_ARTWORK_DIR, sanitize_slug, mockup_path

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


from .analyze_routes import bp as analyze_bp
from .finalise_routes import bp as finalise_bp

bp.register_blueprint(analyze_bp)
bp.register_blueprint(finalise_bp)


---
## routes/analyze_routes.py
---
"""Blueprint for artwork analysis routes."""
from __future__ import annotations

import logging

from flask import Blueprint, request
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
        # Automatically generate mockup composites once analysis has
        # completed successfully.
        generate_mockups(slug)
    except FileNotFoundError:
        logger.error("File not found during analysis: %s", filename)
        return {"error": "file not found"}, 404

    return {"slug": slug, "status": "complete"}, 200



---
## routes/finalise_routes.py
---
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
        return redirect(url_for("finalise.edit_listing", slug=slug))

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
    return redirect(url_for("finalise.edit_listing", slug=slug))


---
## scripts/generate_composites.py
---
"""Generate mockup composites for an artwork slug."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import (
    MOCKUPS_DIR,
    FINALISED_ARTWORK_DIR,
    configure_logging,
    mockup_path,
    sanitize_slug,
    processed_artwork_path,
)

logger = logging.getLogger(__name__)


def generate(slug: str) -> None:
    slug = sanitize_slug(slug)
    source = processed_artwork_path(slug)
    if not source.exists():
        logger.error("Processed image missing: %s", source)
        return

    dest_dir = FINALISED_ARTWORK_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as art:
        templates = sorted(MOCKUPS_DIR.glob("*.jpg"))[:9]
        for idx, tmpl in enumerate(templates, 1):
            out_path = mockup_path(slug, idx)
            if out_path.exists():
                logger.info("Mockup already exists: %s", out_path)
                continue
            with Image.open(tmpl) as background:
                if background.size != art.size:
                    logger.warning(
                        "Size mismatch %s vs %s, skipping %s",
                        background.size,
                        art.size,
                        tmpl,
                    )
                    continue
                composite = background.copy()
                composite.paste(art, (0, 0))
                composite.save(out_path)
                logger.info("Saved %s", out_path)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Generate mockup composites")
    parser.add_argument("slug", help="Artwork slug")
    args = parser.parse_args()
    generate(args.slug)


if __name__ == "__main__":
    main()



---
## templates/review_artwork.html
---
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Edit {{ slug }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    form { max-width: 800px; }
    label { display: block; margin-top: 1rem; }
    .mockups { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 2rem; }
    .mockups img { width: 100%; height: auto; }
    button { margin-top: 1.5rem; padding: 0.5rem 1rem; }
  </style>
</head>
<body>
  <h1>Edit Listing: {{ slug }}</h1>
  <img src="/finalised-artwork/{{ slug }}/{{ slug }}.jpg" alt="{{ slug }}" style="max-width:400px;display:block;margin-bottom:1rem;">
  <form method="post" action="{{ url_for('finalise.finalise', slug=slug) }}">
    <label>Title
      <input type="text" name="title" value="{{ title }}" required>
    </label>
    <label>Description
      <textarea name="description" rows="5" required>{{ description }}</textarea>
    </label>
    <label>Primary Colour
      <select name="primary_colour" required>
        {% for colour in colours %}
        <option value="{{ colour }}" {% if colour == primary_colour %}selected{% endif %}>{{ colour }}</option>
        {% endfor %}
      </select>
    </label>
    <label>Secondary Colour
      <select name="secondary_colour" required>
        {% for colour in colours %}
        <option value="{{ colour }}" {% if colour == secondary_colour %}selected{% endif %}>{{ colour }}</option>
        {% endfor %}
      </select>
    </label>
    <div class="mockups">
      {% for i in range(1, 10) %}
      <img src="/finalised-artwork/{{ slug }}/{{ slug }}-MU-{{ '%02d' % i }}.jpg" alt="Mockup {{ i }}">
      {% endfor %}
    </div>
    <button type="submit" name="action" value="finalise">Finalise Listing</button>
    <button type="submit" name="action" value="regenerate">Regenerate Mockups</button>
  </form>
</body>
</html>


---
## tests/test_validate_sku_integrity.py
---
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import check_unanalysed


def test_missing_thumb(tmp_path):
    base = tmp_path / "unanalysed-artwork"
    base.mkdir()
    (base / "image-RJC-0001.jpg").write_text("data")
    (base / "image-RJC-0001-ANALYSE.jpg").write_text("data")
    (base / "image-RJC-0001.json").write_text("{}")
    errors = check_unanalysed(base)
    assert any("THUMB" in e for e in errors)


def test_all_files_present(tmp_path):
    base = tmp_path / "unanalysed-artwork"
    base.mkdir()
    (base / "image-RJC-0002.jpg").write_text("data")
    (base / "image-RJC-0002-ANALYSE.jpg").write_text("data")
    (base / "image-RJC-0002-THUMB.jpg").write_text("data")
    (base / "image-RJC-0002.json").write_text("{}")
    errors = check_unanalysed(base)
    assert errors == []
