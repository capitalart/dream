# ROOT FILES CODE STACK (THU-07-AUGUST-2025-12-51-AM)


---
## CODEX-README.md
---
# Backup and Restore Guidelines

This document defines the standards for backup creation and restoration integrity within this project.

## Backup

- Use `project-toolkit.sh` or `cron-backup.sh` to generate backups.
- Archives are stored in `backups/` as `dream-backup-YYYY-MM-DD-HH-MM-SS.tar.gz`.
- A `manifest-*.txt` file listing every archived path is produced and included with each backup.
- Default exclusions: `.env`, `.git`, `venv`, `__pycache__`, `.DS_Store`, and anything listed in `backup_excludes.txt`.

## Restore

- Restoration recreates the project structure and virtual environment.
- `python3 -m venv venv` is run and dependencies are installed from `requirements.txt`.
- Missing `.env` files are noted; restored ones trigger a warning.
- Optionally restore `master-artwork-paths.json` when requested.

## Logging

- Every backup or restore appends a timestamped entry to `logs/backup-restore-*.md` describing the action.


---
## app.py
---
"""Flask application for DreamArtMachine with basic authentication."""

from __future__ import annotations

import os

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    url_for,
    flash,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from config import configure_logging
from routes import bp as routes_bp
from routes.home_routes import bp as home_bp
from routes.admin_routes import bp as admin_bp
from routes.finalise_routes import bp as finalise_bp
from routes.exports_routes import bp as exports_bp
from routes.analyze_routes import bp as analyze_bp


login_manager = LoginManager()
login_manager.login_view = "login"


class User(UserMixin):
    """Minimal user model for authentication."""

    def __init__(self, username: str):
        self.id = username
        self.username = username


USERS = {"robbie": {"password": "Kanga123!"}, "backup": {"password": "DreamArt@2025"}}


@login_manager.user_loader
def load_user(user_id: str) -> User | None:  # pragma: no cover - simple loader
    user = USERS.get(user_id)
    return User(user_id) if user else None


def create_app() -> Flask:
    """Application factory with security settings and login enforcement."""
    configure_logging()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=True,
        PREFERRED_URL_SCHEME="https",
    )
    login_manager.init_app(app)

    @app.before_request
    def require_login() -> None:
        """Redirect users to login page if not authenticated."""
        exempt = {"login", "static"}
        if request.endpoint in exempt or request.path == "/favicon.ico":
            return
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            user = USERS.get(username)
            if user and user["password"] == password:
                login_user(User(username))
                return redirect(url_for("home.home"))
            flash("Invalid credentials", "error")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # Artwork listing handled in home blueprint

    @app.route("/healthz")
    @login_required
    def health_check() -> tuple[str, int]:
        return "OK", 200

    @app.route("/whoami")
    @login_required
    def whoami() -> tuple[str, int]:
        return f"Logged in as: {current_user.username}", 200

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("500.html"), 500

    app.register_blueprint(home_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(finalise_bp)
    app.register_blueprint(exports_bp)
    app.register_blueprint(analyze_bp)
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
## cron-backup.sh
---
#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
./project-toolkit.sh --run-backup >> logs/backup-cron-$(date +%Y%m%d).log 2>&1


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
Flask-Login==0.6.3
