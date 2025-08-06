# ROOT FILES CODE STACK (TUE-05-AUGUST-2025-11-54-PM)


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
