# FULL CODE STACK (FRI-08-AUGUST-2025-02-54-PM)


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
import init.image_config  # noqa: F401
from routes import bp as routes_bp
from routes.home_routes import bp as home_bp
from routes.artwork_routes import bp as artwork_bp
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
    app.register_blueprint(artwork_bp)
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

# CORRECTED: These folders should be inside the ART_PROCESSING_DIR
PROCESSED_ARTWORK_DIR = ART_PROCESSING_DIR / "processed-artwork"
FINALISED_ARTWORK_DIR = ART_PROCESSING_DIR / "finalised-artwork"

LOG_DIR = BASE_DIR / "logs"
INPUTS_DIR = BASE_DIR / "inputs"
MOCKUPS_DIR = INPUTS_DIR / "mockups"
MASTER_ARTWORK_PATHS_FILE = BASE_DIR / "master-artwork-paths.json"

# SKU tracking
SKU_TRACKER = BASE_DIR / "sku_tracker.json"
SKU_PREFIX = "RJC"
SKU_DIGITS = 5

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
Flask-Login==0.6.3


---
## routes/__init__.py
---
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


---
## routes/admin_routes.py
---
"""Blueprint for admin pages."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("admin/dashboard.html")


@bp.route("/security")
@login_required
def security_page():
    context = {
        "login_required": True,
        "active": 1,
        "max_sessions": 1,
        "remaining": 0,
        "no_cache": False,
        "cache_remaining": 0,
    }
    return render_template("admin/security.html", **context)


@bp.route("/users")
@login_required
def manage_users():
    return render_template(
        "admin/users.html", users=[], config={"ADMIN_USERNAME": "admin"}
    )


@bp.route("/mockups")
@login_required
def mockups():
    return render_template("admin/mockups.html")


@bp.route("/coordinates")
@login_required
def coordinates():
    return render_template("admin/coordinates.html")


---
## routes/analyze_routes.py
---
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from services.artwork_analysis_service import analyze_artwork
from scripts.generate_composites import generate as generate_mockups

bp = Blueprint("analysis", __name__)

logger = logging.getLogger(__name__)


def _secure_path(name: str) -> str:
    """Return a safe relative path for a filename."""
    parts = [secure_filename(p) for p in Path(name).parts]
    return "/".join(parts)


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
@bp.route("/analyze/<aspect>/<path:filename>", methods=["POST"])
@login_required
def analyze_route(aspect: str, filename: str):
    """Analyse an uploaded artwork and return redirect info."""
    safe_name = secure_filename(filename)
    try:
        slug = analyze_artwork(safe_name)
        generate_mockups(slug)
    except FileNotFoundError:
        logger.error("File not found during analysis: %s", safe_name)
        return jsonify({"error": "file not found"}), 404

    redirect_url = url_for("finalise.edit_listing", slug=slug)
    return jsonify({"success": True, "redirect_url": redirect_url})


---
## routes/artwork_routes.py
---
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


---
## routes/exports_routes.py
---
"""Blueprint handling export-related pages."""
from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("exports", __name__, url_prefix="/exports")


@bp.route("/sellbrite")
@login_required
def sellbrite() -> str:
    """Render the Sellbrite exports management page."""
    return render_template("exports/sellbrite.html")


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
    return render_template("edit_listing.html", slug=slug)


@bp.route("/review/<slug>", methods=["GET"])
def review(slug: str):
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
        return redirect(url_for("finalise.review", slug=slug))

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
    return redirect(url_for("finalise.review", slug=slug))


---
## routes/home_routes.py
---
"""Home and gallery routes.

Provides landing pages and the unanalysed artwork gallery.
"""

from __future__ import annotations

import logging
import os
import json
import shutil
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

import config
from routes import utils as routes_utils

bp = Blueprint("home", __name__)

logger = logging.getLogger(__name__)


@bp.route("/")
@login_required
def root() -> "Response":
    """Redirect the base URL to /home."""
    return redirect(url_for("home.home"))


@bp.route("/home")
@login_required
def home() -> str:
    """Render the application homepage."""
    return render_template(
        "home.html",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
    )


@bp.route("/artworks")
@login_required
def artworks() -> str:
    """List all unanalysed artworks ready for processing."""
    try:
        artworks = routes_utils.get_all_unanalysed_artworks()
    except Exception as exc:  # pragma: no cover - defensive coding
        logger.error("Failed to collect unanalysed artworks: %s", exc)
        artworks = []

    for art in artworks:
        art["upload_date"] = datetime.fromtimestamp(art["timestamp"]).strftime(
            "%Y-%m-%d"
        )

    return render_template(
        "artworks.html",
        artworks=artworks,
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
        get_artwork_image_url=routes_utils.get_artwork_image_url,
    )


@bp.post("/artworks/delete-unanalysed/<slug>")
@login_required
def delete_unanalysed_artwork(slug: str):
    slug = config.sanitize_slug(slug)
    folder = config.UNANALYSED_ARTWORK_DIR / slug
    removed = False
    try:
        if folder.exists():
            shutil.rmtree(folder)
            removed = True

        registry_path = getattr(
            config, "OUTPUT_JSON", getattr(config, "MASTER_ARTWORK_PATHS_FILE", None)
        )
        reg = {}
        if registry_path and registry_path.exists():
            try:
                reg = json.loads(registry_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                reg = {}

        to_delete = []
        for key, rec in reg.items():
            cur = "|".join(
                [rec.get("image", ""), rec.get("analysis", ""), rec.get("openai", "")]
            )
            if f"/{slug}/" in cur or key == slug:
                to_delete.append(key)
        for k in to_delete:
            reg.pop(k, None)

        if registry_path:
            tmp = registry_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(reg, indent=2), encoding="utf-8")
            os.replace(tmp, registry_path)

        flash(("Deleted" if removed else "Nothing to delete") + f" for {slug}", "success")
    except Exception as exc:  # pragma: no cover - defensive
        flash(f"Delete failed for {slug}: {exc}", "danger")
    return redirect(url_for("home.artworks"))


@bp.route("/finalised")
@login_required
def finalised() -> str:
    """Render the finalised artworks page."""
    return render_template(
        "finalised.html",
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        google_configured=bool(os.getenv("GOOGLE_API_KEY")),
    )


---
## routes/utils.py
---
from __future__ import annotations

"""Utility functions for artwork routes."""

# ==========================================================================
# 1. Imports
# ==========================================================================
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from flask import url_for
from PIL import Image

import config

logger = logging.getLogger(__name__)

# Allowed image extensions for artwork files
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}


# ==========================================================================
# 2. Artwork Discovery & Registry
# ==========================================================================
def _aspect_from_image(path: Path) -> str:
    """Return a simple aspect label for the given image path."""
    try:
        with Image.open(path) as img:
            width, height = img.size
    except Exception as exc:  # pragma: no cover - unexpected image errors
        logger.warning("Failed to read image %s: %s", path, exc)
        return "unknown"

    if height == 0:
        return "unknown"

    ratio = width / height
    aspect_map = {
        "square": 1.0,
        "4x5": 0.8,
        "5x4": 1.25,
        "3x4": 0.75,
        "4x3": 1.3333333333,
        "16x9": 16 / 9,
        "9x16": 9 / 16,
    }
    # Choose the aspect with minimal difference
    label = min(aspect_map, key=lambda k: abs(ratio - aspect_map[k]))
    return label


def get_all_unanalysed_artworks() -> List[Dict[str, Any]]:
    """Return metadata for artworks awaiting analysis.

    The function scans every sub-folder in ``UNANALYSED_ARTWORK_DIR`` and
    collects information about the original upload, generated thumbnail and
    analyse image.  Artworks that already have a matching SKU inside the
    processed folder are skipped.
    """

    directory = config.UNANALYSED_ARTWORK_DIR
    processed_dir = config.PROCESSED_ARTWORK_DIR
    if not directory.exists():
        logger.debug("Unanalysed directory missing: %s", directory)
        return []

    def _find_with_marker(folder: Path, marker: str) -> Path | None:
        """Return the first file in ``folder`` containing ``marker``."""
        for path in folder.glob(f"*{marker}*"):
            if path.suffix.lower() in _ALLOWED_EXTS:
                return path
        return None

    artworks: List[Dict[str, Any]] = []
    for folder in sorted(directory.iterdir()):
        if not folder.is_dir():
            continue
        logger.debug("Scanning %s", folder)

        original = next(
            (
                f
                for f in folder.iterdir()
                if f.is_file()
                and f.suffix.lower() in _ALLOWED_EXTS
                and "-THUMB" not in f.stem
                and "-ANALYSE" not in f.stem
            ),
            None,
        )
        if not original:
            logger.debug("Original missing for %s", folder)
            continue

        thumb = _find_with_marker(folder, "-THUMB")
        if not thumb:
            logger.warning("Missing thumbnail for %s", folder)

        analyse = _find_with_marker(folder, "-ANALYSE")
        if not analyse:
            logger.warning("Missing analyse image for %s", folder)

        sku = thumb.stem.split("-")[0] if thumb else None
        if sku and any(processed_dir.rglob(f"*{sku}*")):
            logger.debug("Skipping already processed artwork %s", sku)
            continue

        aspect = _aspect_from_image(analyse) if analyse else "unknown"
        ts = original.stat().st_mtime
        artworks.append(
            {
                "filename": original.name,
                "slug": folder.name,
                "sku": sku,
                "thumb_path": str(thumb.relative_to(directory)) if thumb else None,
                "analyse": str(analyse.relative_to(directory)) if analyse else None,
                "aspect": aspect,
                "timestamp": ts,
            }
        )
    return artworks


def register_artwork_in_master(slug: str, path: Path) -> None:
    """Register ``slug`` to ``path`` within master-artwork-paths.json."""
    record = {slug: {"image": str(path.resolve())}}
    master = config.MASTER_ARTWORK_PATHS_FILE
    data: Dict[str, Any] = {}
    if master.exists():
        try:
            data = json.loads(master.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Corrupted master artwork registry: %s", master)
            data = {}
    data.update(record)
    tmp = master.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(master)


# ==========================================================================
# 4. URL Helpers
# ==========================================================================
def get_artwork_image_url(artwork_status: str, filename: str) -> str:
    """Return the correct route URL for an artwork image."""
    status = artwork_status.lower()
    if status == "finalised":
        endpoint = "artwork.finalised_image"
    elif status == "processed":
        endpoint = "artwork.processed_image"
    else:  # default to unanalysed
        endpoint = "artwork.unanalysed_image"
    try:
        return url_for(endpoint, filename=filename)
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to build URL for %s: %s", filename, exc)
        return "#"


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
## static/css/404.css
---
body {
    font-family: Arial, sans-serif;
    background-color: #f8f8f8;
    color: #333;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    margin: 0;
}

/* --- Universal Content Container --- */
.container {
    max-width: 2400px;
    width: 100%;
    margin: 0 auto;
    padding: 2.5rem 2rem;
    box-sizing: border-box;
}
@media (max-width: 1800px) {
    .container { max-width: 98vw; }
}
@media (max-width: 1400px) {
    .container { max-width: 99vw; }
}
@media (max-width: 1000px) {
    .container { padding: 1.8rem 1rem; }
}
@media (max-width: 700px) {
    .container { padding: 1.2rem 0.5rem; }
}
h1 {
    font-size: 3em;
    color: #FF6347;
}
p {
    font-size: 1.2em;
    color: #555;
}
a {
    font-size: 1.1em;
    color: #4682B4;
    text-decoration: none;
    margin-top: 20px;
}
a:hover {
    text-decoration: underline;
}


---
## static/css/GDWS-style.css
---
/* --- Page Layout --- */
  .gdws-container {
    display: flex;
    flex-wrap: wrap;
    gap: 2rem;
    align-items: flex-start;
  }
  .gdws-main-content {
    flex: 1;
    min-width: 60%;
  }
  .gdws-sidebar {
    width: 280px;
    position: sticky;
    top: 100px; /* Adjust if your header height changes */
    padding: 1.5rem;
    background-color: var(--color-card-bg);
    border: 1px solid var(--card-border);
  }
  .gdws-sidebar h3 {
    margin-top: 0;
    text-align: center;
    margin-bottom: 1.5rem;
  }
  .gdws-sidebar button {
    width: 100%;
    margin-bottom: 1rem;
  }

  /* --- Block Styles --- */
  .paragraph-block { background-color: var(--color-card-bg); border: 1px solid var(--card-border); padding: 1.5rem; margin-bottom: 1.5rem; cursor: grab; }
  .paragraph-block:active { cursor: grabbing; }
  .paragraph-block h3, .paragraph-block .block-title { margin-top: 0; font-size: 1.2em; }
  .paragraph-block .block-title { width: 100%; padding: 0.5rem; border: 1px solid transparent; background-color: transparent; font-family: inherit; font-weight: bold; }
  .paragraph-block .block-title:focus { border-color: var(--card-border); background-color: var(--color-background); }
  .paragraph-block textarea { width: 100%; min-height: 150px; background-color: var(--color-background); color: var(--color-text); border: 1px solid var(--card-border); padding: 0.5rem; }
  .block-actions { margin-top: 1rem; display: flex; gap: 1rem; justify-content: space-between; align-items: center; flex-wrap: wrap; }
  .title-actions { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
  .btn-regenerate-title { font-size: 0.8em; padding: 0.3em 0.6em; min-width: auto; }
  .sortable-ghost { opacity: 0.4; background: #888; border: 2px dashed var(--color-accent); } /* Style for drag placeholder */
  .pinned { background-color: #f0f0f0; border-left: 4px solid #007bff; cursor: not-allowed; }
  .theme-dark .pinned { background-color: #2a2a2a; border-left-color: #4e9fef; }
  .instructions-modal { display: none; }

---
## static/css/art-cards.css
---
/* ========================================================
   art-cards.css – Art Cards, Galleries, Thumbnails, Previews
   Updated 2025-07-24: responsive edit listing thumbnails
   ======================================================== */

/* === Cards & Art Galleries === */
.artwork-info-card { background: var(--color-background); border: 0.09375rem solid #e0e0e0; box-shadow: 0 0.125rem 0.5rem #0001; padding: 1.5em 2em; margin: 0 auto 1.7em auto; max-width: 35.625rem;}
.artwork-info-card h2 { font-size: 1.21em; font-weight: bold; margin-bottom: 0.6em; }
.gallery-section { margin: 2.5em auto 3.5em auto; max-width: 78.125rem; padding: 0 1em;}

/* Artworks grid */
.artwork-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.25rem; margin-bottom: 2em;}

.gallery-card { position: relative; background: var(--card-bg); border: 0.0625rem solid var(--card-border, #000); box-shadow: var(--shadow); display: flex; flex-direction: column; align-items: center; transition: box-shadow 0.18s, transform 0.12s; min-height: 22.8125rem; padding: 0.625rem; overflow: hidden;}
.gallery-card:hover { box-shadow: 0 0.25rem 1rem #0002; transform: translateY(-0.25rem) scale(1.013);}
.card-thumb { width: 100%; background: none; text-align: center; padding: 1.375rem 0 0.4375rem 0; }
.card-img-top { width: 100%; aspect-ratio: 4 / 5; object-fit: cover; box-shadow: 0 0.0625rem 0.4375rem #0001; background: var(--color-background); }
.card-img-top.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 4 / 5;
  background: var(--color-card-bg);
  color: var(--color-text);
}

.card-details { flex: 1 1 auto; width: 100%; text-align: center; padding: 0.75rem 0.8125rem 1.25rem 0.8125rem; display: flex; flex-direction: column; gap: 0.625rem;}
.card-title { font-size: 0.9em; font-weight: 400; line-height: 1.2; color: var(--main-txt); min-height: 3em; margin-bottom: 0.4375rem;}
.card-details .btn { margin-top: 0.4375rem; width: 90%; min-width: 5.625rem;}
.finalised-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: 1.6em; margin-top: 1.5em; justify-content: center;}
.final-card { background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow); padding: 0.625rem; display: flex; flex-direction: column; max-width: 21.875rem; margin: 0 auto;}
.final-actions, .edit-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-top: auto;}
.edit-actions { margin-top: 1em;}
.final-actions .btn, .edit-actions .btn { flex: 1 1 auto; min-width: 6.25rem; width: auto; margin-top: 0; }
.desc-snippet { font-size: 0.92em; line-height: 1.3; margin: 4px 0 8px 0; }
.finalised-badge { font-size: 0.9em; color: #d40000; align-self: center; padding: 4px 8px; }
.locked-badge { font-size: 0.9em; color: #0066aa; padding: 2px 6px; border: 1px solid #0066aa; margin-left: 6px;}
.main-artwork-thumb {
  max-width: 100%;
  max-height: 31.25rem;
  object-fit: contain;
  display: block;
  margin: 0 auto 0.6em auto;
  border-radius: 0.375rem;
  box-shadow: 0 0.125rem 0.75rem #0002;
}

.mockup-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 1rem;
  padding: 1rem;
}
.mockup-card {
  background: var(--color-card-bg);
  padding: 0.6875rem 0.4375rem;
  text-align: center;
  border: none;
  border-radius: 0.25rem;
  transition: box-shadow 0.15s;
}
.mockup-card:hover {
  box-shadow: 0 0.25rem 0.875rem #0002;
}

.mockup-thumb-img {
  width: 100%;
  height: 14.0625rem;
  object-fit: contain;
  border: none;
  box-shadow: 0 0.0625rem 0.375rem rgba(0,0,0,0.09);
  background: var(--color-card-bg);
  cursor: pointer;
  transition: box-shadow 0.15s;
}
.mockup-thumb-img:focus { outline: 2.5px solid var(--accent);}
.mockup-number { font-size: 0.96em; margin-bottom: 6px;}
.missing-img { width: 100%; padding: 20px 0; background: var(--color-background); color: #777; font-size: 0.9em;}
.mini-mockup-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-top: 6px;}
.mini-mockup-grid img { width: 100%; max-height: 120px; object-fit: contain; border-radius: 4px; box-shadow: 0 1px 4px #0001;}
.mockup-thumb-img.selected, .card-img-top.selected, .gallery-thumb.selected { outline: 3px solid #e76a25 !important; outline-offset: 1.5px; }

/* Overlay for per-card progress */
.card-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}
.theme-dark .card-overlay { background: rgba(0, 0, 0, 0.65); color: #fff; }
.card-overlay.hidden { display: none; }
.spinner {
  width: 18px;
  height: 18px;
  border: none;
  border-top-color: #333;
  border-radius: 50%;
  margin-right: 8px;
  animation: spin 0.8s linear infinite;
}

.category-badge.uncategorised {
  color: #e10000; /* A strong red color */
  font-weight: bold;
}

.theme-dark .category-badge.uncategorised {
  color: #ff5c5c; /* A lighter red for dark mode */
}

/* --- Mockup Swapping Overlay --- */

/* Add relative positioning to the link to contain the overlay */
.mockup-img-link {
  position: relative;
  display: block;
}

.mockup-overlay {
  position: absolute;
  inset: 0; /* A shorthand for top, right, bottom, left = 0 */
  background-color: rgba(0, 0, 0, 0.5); /* 50% opaque dark background */
  display: none; /* Hide the overlay by default */
  align-items: center;
  justify-content: center;
  border-radius: 4px; /* Match the card's border radius */
}

/* Show the overlay when the card is in a swapping state */
.mockup-card.swapping .mockup-overlay {
  display: flex;
}

.mockup-overlay .spinner-icon {
  width: 48px;
  height: 48px;
  animation: spin 1.5s linear infinite;
}

/* Invert icon color for dark theme */
.mockup-overlay .spinner-icon {
  filter: invert(1);
}

@keyframes spin { to { transform: rotate(360deg); } }
.status-icon {
  position: absolute;
  top: 6px;
  right: 8px;
  font-size: 1.4em;
}

/* Gallery view toggles */
.view-toggle { margin-top: 0.5em;}
.view-toggle button { margin-right: 0.5em;}
.finalised-grid.list-view { display: block; }
.finalised-grid.list-view .final-card { flex-direction: row; max-width: none; margin-bottom: 1em;}
.finalised-grid.list-view .card-thumb { width: 150px; margin-right: 1em; }

/* Responsive Art Cards */
@media (max-width: 1023px) {
  .artwork-grid { gap: 1.25rem; }
  .card-thumb { padding: 0.75rem 0 0.25rem 0; }
  .card-title { font-size: 1em; }
  .finalised-grid { grid-template-columns: repeat(auto-fit, minmax(13.75rem, 1fr)); }
  .main-artwork-thumb { max-height: 50vh; }
  .mockup-preview-grid { grid-template-columns: repeat(auto-fit, minmax(45%, 1fr)); }
  .mockup-card { width: 100%; }
  .mini-mockup-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 767px) {
  .mockup-preview-grid { grid-template-columns: 1fr; overflow-x: auto; }
}

---
## static/css/buttons.css
---
/* ========================================================
   buttons.css – All Buttons, Workflow Buttons & Actions
   Monochrome, strong hover, square corners, theme aware
   ======================================================== */

/* ========================================================
   Theme Variables for Buttons (Place in your root CSS file)
   ======================================================== */

:root {
  --btn-primary-bg: #111111;
  --btn-primary-text: #ffffff;
  --btn-primary-hover-bg: #ffffff;
  --btn-primary-hover-text: #111111;
  --btn-primary-hover-shadow: 0 0 0 3px #1112;

  --btn-secondary-bg: #f5f5f5;
  --btn-secondary-text: #111111;
  --btn-secondary-hover-bg: #111111;
  --btn-secondary-hover-text: #ffffff;
  --btn-secondary-hover-shadow: 0 0 0 3px #3332;

  --btn-danger-bg: #444444;
  --btn-danger-text: #ffffff;
  --btn-danger-hover-bg: #ffffff;
  --btn-danger-hover-text: #c8252d;
  --btn-danger-hover-shadow: 0 0 0 3px #c8252d44;

  --btn-disabled-bg: #bbbbbb;
  --btn-disabled-text: #eeeeee;

  --btn-workflow-bg: #ededed;
  --btn-workflow-text: #1a1a1a;
  --btn-workflow-hover-bg: #222222;
  --btn-workflow-hover-text: #ffffff;
  --btn-workflow-hover-shadow: 0 0 0 3px #2222;
  --btn-workflow-border: #bbbbbb;
}

.theme-dark {
  --btn-primary-bg: #ffffff;
  --btn-primary-text: #111111;
  --btn-primary-hover-bg: #111111;
  --btn-primary-hover-text: #ffffff;
  --btn-primary-hover-shadow: 0 0 0 3px #fff2;

  --btn-secondary-bg: #222222;
  --btn-secondary-text: #ffffff;
  --btn-secondary-hover-bg: #ffffff;
  --btn-secondary-hover-text: #222222;
  --btn-secondary-hover-shadow: 0 0 0 3px #fff2;

  --btn-danger-bg: #888888;
  --btn-danger-text: #ffffff;
  --btn-danger-hover-bg: #ffffff;
  --btn-danger-hover-text: #c8252d;
  --btn-danger-hover-shadow: 0 0 0 3px #c8252d44;

  --btn-disabled-bg: #444444;
  --btn-disabled-text: #bbbbbb;

  --btn-workflow-bg: #1a1a1a;
  --btn-workflow-text: #ffffff;
  --btn-workflow-hover-bg: #ffffff;
  --btn-workflow-hover-text: #111111;
  --btn-workflow-hover-shadow: 0 0 0 3px #fff2;
  --btn-workflow-border: #444444;
}

/* ========================================================
   Base Button Styles (Square Corners, Strong Contrast)
   ======================================================== */

.btn,
.btn-primary,
.btn-secondary,
.btn-danger,
.btn-sm,
.wide-btn,
.upload-btn-large,
.art-btn {
  font-family: var(--font-primary, monospace);
  border: none;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, box-shadow 0.12s, outline 0.12s;
  display: inline-block;
  text-align: center;
  text-decoration: none;
  outline: none;
  font-size: 1em;
  border-radius: 0;
  min-width: 120px;
  box-shadow: 0 1px 5px 0 #1111;
}

.btn, .btn-primary, .btn-secondary, .btn-danger {
  width: 90%;
  margin: 10px auto;
  padding: .55em 1.3em;
  font-size: 18px;
  align-self: center;
  font-weight: 600;
}

.btn-sm { font-size: 0.96em; padding: 0.45em 1em; }
.wide-btn { width: 100%; font-size: 1.12em; font-weight: bold; padding: 1em 0; }

/* ========================================================
   Button Types
   ======================================================== */

/* -- Primary Button -- */
.btn-primary, .btn:not(.btn-secondary):not(.btn-danger) {
  background: var(--btn-primary-bg);
  color: var(--btn-primary-text);
}
.btn-primary:hover, .btn-primary:focus,
.btn:not(.btn-secondary):not(.btn-danger):hover,
.btn:not(.btn-secondary):not(.btn-danger):focus {
  background: var(--btn-primary-hover-bg);
  color: var(--btn-primary-hover-text);
  box-shadow: var(--btn-primary-hover-shadow);
  outline: 2px solid var(--btn-primary-hover-bg);
}

/* -- Secondary Button -- */
.btn-secondary {
  background: var(--btn-secondary-bg);
  color: var(--btn-secondary-text);
  border: 1.2px solid var(--btn-workflow-border, #bbbbbb);
}
.btn-secondary:hover,
.btn-secondary:focus {
  background: var(--btn-secondary-hover-bg);
  color: var(--btn-secondary-hover-text);
  border-color: #111111;
  box-shadow: var(--btn-secondary-hover-shadow);
  outline: 2px solid var(--btn-secondary-hover-bg);
}

/* -- Danger Button -- */
.btn-danger {
  background: var(--btn-danger-bg);
  color: var(--btn-danger-text);
}
.btn-danger:hover, .btn-danger:focus {
  background: var(--btn-danger-hover-bg);
  color: var(--btn-danger-hover-text);
  box-shadow: var(--btn-danger-hover-shadow);
  outline: 2px solid #c8252d;
}

/* -- Disabled State -- */
.btn:disabled,
button:disabled,
.btn.disabled,
.btn-primary:disabled,
.btn-secondary:disabled,
.btn-danger:disabled {
  background: var(--btn-disabled-bg);
  color: var(--btn-disabled-text);
  cursor: not-allowed;
  opacity: 0.62;
  filter: grayscale(35%);
  box-shadow: none;
  outline: none;
}

/* -- Active State (All) -- */
.btn:active, .btn-primary:active, .btn-secondary:active, .btn-danger:active {
  filter: brightness(0.96) saturate(110%);
}

/* ========================================================
   Workflow Buttons (Solid & Card, Square Corners)
   ======================================================== */

.workflow-btn {
  font-family: var(--font-primary, monospace);
  display: flex;
  align-items: center;
  justify-content: flex-start;
  font-size: 1.11em;
  font-weight: 600;
  padding: 18px 32px;
  background: var(--btn-workflow-bg);
  color: var(--btn-workflow-text);
  border: 1.2px solid var(--btn-workflow-border, #bbbbbb);
  border-radius: 0;
  min-width: 220px;
  margin: 0 16px 0 0;
  transition: background 0.15s, color 0.15s, box-shadow 0.12s, outline 0.12s;
}
.workflow-btn:hover:not(.disabled),
.workflow-btn:focus:not(.disabled) {
  background: var(--btn-workflow-hover-bg);
  color: var(--btn-workflow-hover-text);
  border-color: #111111;
  box-shadow: var(--btn-workflow-hover-shadow);
  outline: 2px solid var(--btn-workflow-hover-bg);
}
.workflow-btn.disabled,
.workflow-btn[disabled] {
  background: var(--btn-disabled-bg);
  color: var(--btn-disabled-text);
  pointer-events: none;
  opacity: 0.65;
  filter: grayscale(0.35);
  outline: none;
}

/* Card-style for workflow row */
.workflow-row {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  justify-content: center;
  align-items: stretch;
  margin: 2.5rem 0 3rem 0;
}
.workflow-row .workflow-btn {
  flex: 1 1 12.5rem;
  flex-direction: column;
  gap: 1.2rem;
  font-size: 1.06em;
  text-align: center;
  min-width: 11.25rem;
  max-width: 16.875rem;
  padding: 1.7em 1.2em 1.5em 1.2em;
  box-shadow: 0 0.125rem 0.625rem 0 #1111;
  margin: 0;
  border-radius: 0;
}

/* Responsive Buttons */
@media (max-width: 1439px) {
  .workflow-row { gap: 1.2rem; }
  .workflow-row .workflow-btn { font-size: 1em; min-width: 8.125rem; max-width: 13.125rem; padding: 1em 0.8em; }
}
@media (max-width: 1023px) {
  .workflow-row { gap: 0.7rem; }
  .workflow-row .workflow-btn { font-size: 0.95em; min-width: 45vw; max-width: 95vw; padding: 0.9em 0.5em 1em 0.5em; margin-bottom: 0.5em; }
}
@media (max-width: 767px) {
  .workflow-row { flex-direction: column; gap: 0.5rem; margin-top: 4rem; }
  .workflow-row .workflow-btn {
    min-width: 98vw;
    max-width: 100vw;
    padding: 0.8em 0.4em;
    font-size: 1.2rem;
    min-height: 180px;
  }
}

/* ========================================================
   Art Actions/Rows
   ======================================================== */
.button-row, .final-actions, .edit-actions {
  display: flex; justify-content: center; align-items: center;
  gap: 0.625rem; margin-top: 1.25rem; flex-wrap: wrap;
}
.button-row form, .final-actions form, .edit-actions form { margin: 0; }
.art-btn {
  font-weight: 500; height: var(--button-height, 3rem); min-width: 6.25rem;
  border-radius: 0;
  font-size: 1em; display: flex; align-items: center; justify-content: center;
  background: var(--btn-secondary-bg);
  color: var(--btn-secondary-text);
  border: 0.075rem solid var(--btn-workflow-border, #bbbbbb);
  transition: background 0.13s, color 0.13s, border 0.13s, outline 0.13s;
}
.art-btn:not(:disabled):hover,
.art-btn:not(:disabled):focus {
  background: var(--btn-secondary-hover-bg);
  color: var(--btn-secondary-hover-text);
  border-color: #111111;
  box-shadow: var(--btn-secondary-hover-shadow);
  outline: 2px solid var(--btn-secondary-hover-bg);
}
.art-btn.delete,
.art-btn.delete:not(:disabled):hover {
  background: var(--btn-danger-bg);
  color: var(--btn-danger-text) !important;
  border: none;
}
.art-btn:disabled, .art-btn.disabled {
  background: var(--btn-disabled-bg); color: var(--btn-disabled-text);
  cursor: not-allowed; border: none; outline: none;
}

/* --- End of File --- */


---
## static/css/documentation.css
---


---
## static/css/edit_listing.css
---
/* --- [ edit_listing.css] --- */
.action-form {
  width: 100%;
}
.form-col {
  flex: 1;
}
.swap-btn-container {
  position: relative;
  width: 100%; /* Make container take full width */
}
.swap-spinner {
  display: none;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  border: 2px solid rgba(0, 0, 0, 0.2);
  border-top-color: #333;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.theme-dark .swap-spinner {
  border-top-color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}
.swapping .swap-btn {
  color: transparent;
}
.swapping .swap-spinner {
  display: block;
}

/* --- NEW STYLES FOR STACKED LAYOUT --- */
.swap-controls {
  display: flex;
  flex-direction: column; /* Stack elements vertically */
  align-items: stretch;   /* Make children take full width */
  gap: 0.5rem;
  margin-top: 0.5rem;
  width: 100%;
}

.swap-controls select,
.swap-controls .swap-btn {
  width: 100%; /* Ensure both take full width of the container */
  height: 38px;
  box-sizing: border-box;
}

.swap-controls select {
  padding: 0.4em 0.6em;
  font-size: 0.9em;
  border: 1px solid var(--card-border);
  background-color: var(--color-card-bg);
  color: var(--color-text);
  border-radius: 0;
}

.thumb-note {
  font-size: 0.85em; /* Adjusted for better fit */
  color: rgba(0, 0, 0, 0.65); /* Muted dark color for light mode */
  margin-top: 0.5rem;
  text-align: center;
}

.theme-dark .thumb-note {
  color: rgba(255, 255, 255, 0.65); /* Muted light color for dark mode */
}

/* --- OpenAI Analysis Details Table --- */
.openai-details {
  margin-top: 2rem;
  background-color:#dbdbdb;
  padding: .7rem;
  border-top: 1px solid var(--card-border);
}

.openai-analysis-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85em;
  margin-bottom: 1rem;
  table-layout: fixed; /* Ensures column widths are respected */
}

.openai-analysis-table thead th {
  font-size: 1.1em;
  font-weight: 600;
  padding: 0.8em 0.5em;
  text-align: left;
  background-color: var(--color-card-bg);
  border-bottom: 2px solid var(--card-border);
}

.openai-analysis-table tbody th,
.openai-analysis-table tbody td {
  padding: 0.6em 0.5em;
  vertical-align: top;
  border-bottom: 1px solid var(--card-border);
}

.openai-analysis-table tbody th {
  font-weight: 600;
  text-align: left;
  width: 30%;
  color: var(--color-text);
  opacity: 0.8;
  word-break: break-word; /* Allow labels to wrap if needed */
}

.openai-analysis-table tbody td {
  width: 70%;
  text-align: left;
  word-break: break-all; /* Crucial for long file paths */
}

.openai-analysis-table tbody tr:nth-of-type(even) {
  background-color: rgba(0, 0, 0, 0.02);
}

.theme-dark .openai-analysis-table tbody tr:nth-of-type(even) {
  background-color: rgba(255, 255, 255, 0.04);
}

@media (max-width: 767px) {
  .openai-analysis-table thead th,
  .openai-analysis-table tbody th,
  .openai-analysis-table tbody td {
    font-size: 0.8em;
  }
}

---
## static/css/icons.css
---
/* ========================================================
   icons.css – All icon styles and theme filters
   Applies color inversion for icons in dark theme.
   ======================================================== */

.site-logo {
  font-weight: 400;
  font-size: 1.3rem;
  letter-spacing: 0.5px;
}

.logo-icon,
.narrator-icon {
  width: 2.1875rem;
  height: 2.1875rem;
  margin-right: 0.375rem;
  vertical-align: bottom;
}

.narrator-icon {
  width: 3.125rem;
  margin-bottom: 0.3125rem;
}

.logo {
  width: 2.1875rem;
  height: 2.1875rem;
  margin: 0 0.5rem 0.3125rem 0;
  vertical-align: bottom;
}

/* Workflow and hero icons */
.step-btn-icon {
  width: 2.1875rem;
  height: 2.1875rem;
  margin-right: 0.75rem;
  display: inline-block;
}

.hero-step-icon {
  width: 3.125rem;
  height: 3.125rem;
  margin-right: 0.625rem;
  display: inline-block;
  margin-bottom: 0.3125rem;
  vertical-align: bottom;
  color:var(--color-text);
}

.progress-icon {
  width: 3rem;
  color: #ffffff;
  display: block;
  margin: 0 auto 0.8em auto;
}

/* Theme toggle icons */
.sun-icon { display: block; }
.moon-icon { display: none; }
.theme-dark .sun-icon { display: none; }
.theme-dark .moon-icon { display: block; }

/* Global icon colour inversion */
.theme-dark img.icon,
.theme-dark svg.icon,
.theme-dark .logo-icon,
.theme-dark .hero-step-icon,
.theme-dark .step-btn-icon {
  filter: invert(1) grayscale(1) brightness(1.3);
}
.theme-light img.icon,
.theme-light svg.icon,
.theme-light .logo-icon,
.theme-light .hero-step-icon,
.theme-light .step-btn-icon {
  filter: none;
}

/* --- Modal Icons --- */
.coffee-icon {
  display: block;
  width: 3.125rem;
  height: 3.125rem;
  margin: 1rem auto 0 auto; /* Centers the icon and adds space above it */
}

/* Responsive icon sizing for workflow buttons */
@media (max-width: 1439px) {
  .workflow-row .step-btn-icon { width: 2em; height: 2em; }
}
@media (max-width: 1023px) {
  .workflow-row .step-btn-icon { width: 1.5em; height: 1.5em; }
}
@media (max-width: 767px) {
  .workflow-row .step-btn-icon { width: 1.2em; height: 1.2em; }
}


---
## static/css/layout.css
---
:root {
  --header-h: 80px;
}

/* ========================================================
   layout.css – Layout, Grids, Columns, Structure
   Uses --header-bg variable for theme-aware headers.
   ======================================================== */

/* Prevent sticky header overlap on anchor/first content */
html { scroll-padding-top: var(--header-height, 72px); }

/* Main container */
.container {
  max-width: 2400px;
  margin: 0 auto;
  padding: 2.5rem 2rem; /* generous top padding clears header */
  box-sizing: border-box;
}

@media (max-width: 1000px) { .container { padding: 1.6rem 1rem; } }
@media (max-width: 700px)  { .container { padding: 1.2rem .75rem; } }

/* === Layout Grids, Columns & Rows === */
.artwork-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.25rem;
}

/* Buttons rendered as links should inherit button color */
.button-row a.btn { color: var(--btn-primary-text); text-decoration: none; }
.review-artwork-grid, .row { display: flex; flex-wrap: wrap; gap: 2.5rem; align-items: flex-start; width: 100%; }
.exports-special-grid { display: grid; grid-template-columns: 1fr 1.7fr; gap: 2em; margin: 2em 0; }
.page-title-row { display: flex; align-items: center; gap: 1.25rem; margin-bottom: 2.5rem; }
.page-title-large { font-size: 2.15em; font-weight: bold; text-align: center; margin: 1.4em 0 0.7em 0; }
.mockup-col { flex: 1 1 0; min-width: 21.25rem; display: block; }
.edit-listing-col { flex: 1; } /* MODIFIED: Removed width: 100% and allowed flexbox to manage width */
.price-sku-row, .row-inline { display: flex; gap: 1em; }
.price-sku-row > div, .row-inline > div { flex: 1; }

/* === Responsive Grids === */
@media (max-width: 1023px) {
  .page-title-row { flex-direction: column; text-align: center; gap: 1em; }
  .exports-special-grid { grid-template-columns: 1fr; gap: 1.1em; }
}
@media (max-width: 767px) {
  .review-artwork-grid { flex-direction: column; gap: 1.5em; }
  .mockup-col, .edit-listing-col { width: 100%; max-width: none;}
}

/* Responsive Header */
@media (max-width: 767px) {
  .header-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    padding: 0.5rem 1rem;
  }
  .header-grid .header-left { grid-column: 1; }
  .header-grid .header-center { grid-column: 2; justify-self: center; }
  .header-grid .header-right { grid-column: 3; justify-self: end; }
  .site-footer { min-height: 20rem; }
}

/* ===== Simple Flexbox Grid System for DreamArtMachine ===== */

/* MODIFIED: This rule now correctly calculates a 50% width while accounting for the container's gap. */
.col-6 {
  flex: 1 1 calc(48% - 1.25rem); /* 1.25rem is half of the 2.5rem gap */
  max-width: calc(48% - 1.25rem);
  min-width: 340px;
  box-sizing: border-box;
}

.row, .review-artwork-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 2.5rem;
  align-items: flex-start;
  width: 100%;
}

.col {
  flex: 1 1 0;
  min-width: 0;
}

.review-main-img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto 1rem auto;
}


/* === Header === */
.site-header,
.overlay-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 1rem;
        width: 100%;
        margin: 0 auto;
        left: 0;
        right: 0;
        background-color: var(--header-bg);
}

.site-header {
	position: sticky;
	top: 0;
	z-index: 1000;
	background-color: var(--header-bg);
	transition: background-color 0.3s, color 0.3s;
	border-bottom: 1px solid var(--color-header-border);
	color: var(--color-text); /* Ensure header text/icons match theme */
}

/* FIX: Added padding-top to the main content area */
main {
    padding-top: var(--header-h);
}

.header-left, .header-right {
	flex: 1;
}
.header-center {
	flex-grow: 0;
}
.header-right {
	display: flex;
	justify-content: flex-end;
}

.menu-toggle-btn, .menu-close-btn {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	font-size: 1rem;
	font-weight: 500;
}

.menu-toggle-btn svg, .menu-close-btn svg {
	width: 16px;
	height: 16px;
}

.theme-toggle-btn {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 44px;
	height: 44px;
}

.theme-toggle-btn svg {
	width: 24px;
	height: 24px;
}

/* --- Footer --- */
.site-footer {
        background-color: var(--color-footer-bg);
        color: var(--color-footer-text);
        min-height: 25rem;
        display: flex;
        margin-top: 3rem;
        flex-direction: column;
        justify-content: center;
        border-top: 1px solid var(--color-footer-border);
        width: 100%;
        margin-left: 0;
        margin-right: 0;
        left: 0;
        right: 0;
}

.footer-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        max-width: 2400px;
        width: 100%;
        margin: 0 auto;
        padding: 0 2rem;
}

.footer-column h4 {
	font-size: 1rem;
	margin: 20px 0 1rem 0;
	text-transform: uppercase;
	letter-spacing: 1px;
	opacity: 0.7;
}

.footer-column ul {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
}

.footer-column a {
        opacity: 0.9;
        transition: opacity 0.3s;
        line-height: 1.6;
        padding-bottom: 0.5rem;
        display: inline-block;
}
.footer-column a:hover {
	opacity: 1;
	color: var(--color-hover);
}

.copyright-bar {
	padding: 1rem 2rem;
	text-align: center;
	font-size: 0.8rem;
	margin-top: auto; /* Pushes to the bottom of the flex container */
}
         
/* --- Upload Dropzone --- */
.upload-dropzone {
  border: var(--border-2);
  padding: var(--space-6);
  text-align: center;
  cursor: pointer;
  color: var(--color-semantic-text-muted);
  transition: background var(--transition-1), border-color var(--transition-1);
}
.upload-dropzone.dragover {
  border-color: var(--color-semantic-accent-primary);
  background: var(--color-semantic-bg-hover);
}
.upload-list {
  margin-top: var(--space-3);
  list-style: none;
  padding: 0;
  font-size: var(--font-size-1);
}
.upload-list li { margin: var(--space-1) 0; }
.upload-list li.success { color: var(--color-semantic-success); }
.upload-list li.error { color: var(--color-semantic-error); }
.upload-progress {
  position: relative;
  background: var(--color-semantic-bg-hover);
  height: var(--space-2);
  margin: var(--space-1) 0;
  width: 100%;
  overflow: hidden;
}
.upload-progress-bar {
  background: var(--color-semantic-accent-primary);
  height: 100%;
  width: 0;
  transition: width 0.2s;
}
.home-hero { margin: 2em auto 2.5em auto; text-align: center; }

/* ===============================
   [ Upload Dropzone ]
   =============================== */
.upload-dropzone {
  border: 2px dashed #bbb;
  max-width: 800px;;
  width: 100%;
  margin: 20px auto;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  color: #666;
  transition: background 0.2s, border-color 0.2s;
}

.upload-dropzone:hover {
  background-color: var(--color-hover);
  color:var(--dark-color-text);
}

.upload-dropzone.dragover {
  border-color: #333;
  background: #f9f9f9;
}

.upload-list {
  margin-top: 1em;
  list-style: none;
  padding: 0;
  font-size: 0.9rem;
}
.upload-list li {
  margin: 0.2em 0;
}
.upload-list li.success { color: green; }
.upload-list li.error { color: red; }

.upload-progress {
  position: relative;
  background: #eee;
  height: 8px;
  margin: 2px 0;
  width: 100%;
  overflow: hidden;
}
.upload-progress-bar {
  background: var(--accent);
  height: 100%;
  width: 0;
  transition: width 0.2s;
}
.upload-percent {
  margin-left: 4px;
  font-size: 0.8em;
}

/* ===============================
   [ Edit Artwork Listing Page ]
   =============================== */
/* --- Edit Action Buttons Area --- */
.edit-listing-col {
  width: auto; /* Corrected from 100% */
}

.long-field {
  width: 100%;
  box-sizing: border-box;
  background-color: #dbdbdb !important;
  font-size: 1.05em;
  padding: 0.6em;
  margin-bottom: 1em;
  border-radius: 0 !important;   /* FORCE SQUARE */
}

.price-sku-row,
.row-inline {
  display: flex;
  gap: 1em;
}
.price-sku-row > div,
.row-inline > div {
  flex: 1;
}

.edit-actions-col {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.7em;
  margin: 2em 0 0 0;
  width: 100%;
}

.wide-btn {
  width: 100%;
  font-size: 1.12em;
  font-weight: bold;
  padding: 1em 0;
  border-radius: 0 !important;   /* FORCE SQUARE */
}


.status-line {margin-top:0px}

/* Responsive: Stack columns on small screens */
@media (max-width: 1100px) {
  .col-6 {
    flex: 1 1 calc(50% - 0.6rem); /* Adjust for smaller gap */
    max-width: calc(50% - 0.6rem);
    min-width: 340px;
    margin-bottom: 2rem;
  }
  .review-artwork-grid {
    gap: 1.2rem;
  }
}

/* For older .row usage (legacy) */
@media (max-width: 700px) {
  .row, .review-artwork-grid {
    flex-direction: column;
    gap: 1rem;
  }
  .price-sku-row,
  .row-inline {
    flex-direction: column;
    gap: 0.5em;
  }
}

/* ===== Responsive Mockup Thumbnails ===== */
/* Moved detailed sizing rules to art-cards.css */

@media (min-width: 1400px) {
.home-content-grid {
    max-width: 1400px;
}
}

@media (min-width: 1600px) {
.home-content-grid {
    max-width: 1600px;
}
}

@media (min-width: 1800px) {
.home-content-grid {
    max-width: 1800px;
}
}

@media (min-width: 2400px) {
.home-content-grid {
    max-width: 2400px;
}
}

@keyframes spin {
0% { transform: rotate(0deg); }
100% { transform: rotate(360deg); }
}

---
## static/css/main.css
---
@import url('style.css');
@import url('icons.css');
@import url('layout.css');
@import url('buttons.css');
@import url('art-cards.css');
@import url('overlay-menu.css');
@import url('modals-popups.css');
@import url('GDWS-style.css');
@import url('documentation.css');
@import url('edit_listing.css');
@import url('404.css');

:target {
  scroll-margin-top: 5rem;
}


---
## static/css/modals-popups.css
---
/* In static/css/modals-popups.css */

/* --- Unified Modal Style --- */
.modal-bg {
  display: none;
  position: fixed;
  z-index: 100;
  left: 0;
  top: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.65);
  align-items: center;
  justify-content: center;
}

.modal-bg.active {
  display: flex;
}

.modal-box {
  background: #ffffff;
  color: #111111;
  padding: 2.5rem;
  max-width: 450px;
  width: 90%;
  border-radius: 12px;
  box-shadow: 0 5px 25px rgba(0, 0, 0, 0.2);
  font-family: var(--font-primary);
  text-align: center;
  position: relative;
}

.modal-box .modal-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  font-size: 1.5rem;
  color: #aaa;
  background: none;
  border: none;
  cursor: pointer;
  line-height: 1;
}

.modal-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 1.5rem auto;
  display: block;
}

.modal-icon.spinning {
  animation: spin 1.5s linear infinite;
}

.modal-box h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-size: 1.5rem;
  font-weight: 600;
}

.modal-status {
  margin-bottom: 1rem;
  font-size: 1rem;
  color: #666;
  word-break: break-all;
  min-height: 1.2em;
}

.modal-progress {
  background: #eee;
  border-radius: 4px;
  height: 10px;
  margin: 1.5rem 0;
  width: 100%;
  overflow: hidden;
}

.modal-progress-bar {
  background: #333;
  height: 100%;
  width: 0;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.modal-friendly-text {
  font-size: 0.9em;
  color: #888;
  margin-top: 1.5rem;
  line-height: 1.4;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* --- Carousel Specific Styles --- */
.carousel-modal .modal-box {
  background: transparent;
  box-shadow: none;
  width: auto;
  max-width: 95vw;
  padding: 0;
}

/* ADD THE NEW RULE HERE */
.modal-img img {
  display: block;
  max-width: 90vw;    /* Never wider than 90% of the viewport width */
  max-height: 90vh;   /* Never taller than 90% of the viewport height */
  width: auto;        /* Maintain aspect ratio */
  height: auto;       /* Maintain aspect ratio */
  box-shadow: 0 5px 25px rgba(0,0,0,0.3);
}

.modal-timer {
  font-size: 0.9em;
  color: #999;
  margin-bottom: 0.5rem;
}

.carousel-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 2.5em;
  cursor: pointer;
  padding: 0 0.5em;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0,0,0,0.5);
  transition: color 0.2s;
}

.carousel-nav:hover {
  color: var(--color-accent);
}
#carousel-prev { left: 0.5rem; }
#carousel-next { right: 0.5rem; }

@media (max-width: 767px) {
  .modal-box { padding: 1.5rem; max-width: 90%; }
}

/* --- Gemini Modal --- */

.gemini-modal {
position: fixed;
z-index: 1001;
left: 0;
top: 0;
width: 100%;
height: 100%;
overflow: auto;
background-color: rgba(0,0,0,0.5);
display: none;
align-items: center;
justify-content: center;
}

.gemini-modal-content {
background-color: var(--color-background);
color: var(--color-text);
margin: auto;
padding: 2rem;
border: 1px solid #888;
width: 80%;
max-width: 600px;
position: relative;
}

.gemini-modal-close {
position: absolute;
top: 1rem;
right: 1.5rem;
font-size: 1.5rem;
font-weight: bold;
cursor: pointer;
}

.gemini-modal-body textarea {
width: 100%;
min-height: 200px;
margin-top: 1rem;
background-color: var(--color-card-bg);
color: var(--color-text);
border: 1px solid var(--color-header-border);
padding: 0.5rem;
}

.gemini-modal-actions {
margin-top: 1rem;
display: flex;
gap: 1rem;
}

.loader {
border: 4px solid #f3f3f3;
border-radius: 50%;
border-top: 4px solid var(--color-hover);
width: 40px;
height: 40px;
animation: spin 2s linear infinite;
margin: 2rem auto;
}

---
## static/css/overlay-menu.css
---
/* ========================================================
   overlay-menu.css – Overlay Menu, Nav, Sidebar
   ======================================================== */

.overlay-menu {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100vh;
  background-color: var(--color-overlay-bg, rgba(248, 248, 248, 0.85));
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  z-index: 999;
  display: flex; flex-direction: column; padding: 0;
  opacity: 0; visibility: hidden; transform: translateY(20px);
  transition: opacity 0.5s var(--ease-quart), visibility 0.5s var(--ease-quart), transform 0.5s var(--ease-quart);
  overflow-y: auto; color: #111111;
}
.overlay-menu.is-active { opacity: 1; visibility: visible; transform: translateY(0);}
.overlay-header { flex-shrink: 0; position: sticky; top: 0; background-color: var(--color-overlay-bg);} 
.overlay-nav {
  display: grid; grid-template-columns: repeat(3, 1fr);
  flex-grow: 1; padding: 4rem 2rem; gap: 2rem;
  width: 100%; max-width: 75rem; margin: 0 auto 50px auto;
}
.nav-column h3 { font-size: 1rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; opacity: 0.5; margin: 0 0 1.5rem 0;}
.nav-column ul { display: flex; flex-direction: column; gap: 1rem;}
.nav-column a { font-size: 1.2em; font-weight: 500; line-height: 1.3; display: inline-block; transition: color 0.3s var(--ease-quart);}
.nav-column a:hover { color: var(--color-hover);}
@media (max-width: 1023px) {
  .overlay-nav { grid-template-columns: 1fr; justify-items: center; text-align: center; gap: 3rem; }
  .nav-column a { font-size: 1.5rem; }
}
@media (max-width: 767px) {
  .overlay-nav { padding: 2rem 1rem; }
  .nav-column a { font-size: 1.2rem; }
}


---
## static/css/style.css
---
/* ========================================================
   style.css – Globals, Variables & Universal Container
   Defines theme-aware color variables for light and dark modes.
   ======================================================== */

/* === [ 1. FONT DEFINITIONS ] === */
@font-face {
  font-family: 'Urbanist';
  src: url('/static/fonts/Urbanist-VariableFont_wght.ttf') format('truetype');
  font-weight: 100 900;
  font-style: normal;
}

@font-face {
  font-family: 'Urbanist';
  src: url('/static/fonts/Urbanist-Italic-VariableFont_wght.ttf') format('truetype');
  font-weight: 100 900;
  font-style: italic;
}

/* === [ 2. THEME & GLOBAL VARIABLES ] === */
:root {
  --font-primary: 'Urbanist', sans-serif;
  --color-background: #cccccc;
  --color-text: #111111;
  --color-card-bg: hsl(0, 0%, 81%);
  --color-header-border: #eeeeee;
  --color-footer-bg: #cccccc;
  --color-footer-text: #111111;
  --color-footer-border: #dddddd;
  --header-bg: #cccccc;
  --table-row-bg: #cccccc;
  --table-row-alt-bg: #adadad;
  --dark-color-footer-bg: #181818;
  --dark-color-footer-text: #FFFFFF;
  --color-hover: #ffa52a;
  --color-danger: #c8252d;
  --color-hover-other: #000000;
  --color-accent: #e76a25;
  --color-accent-hover: #ff9933;
  --card-border: #c8c7c7;
  --workflow-icon-size: 2.1em;
  --dark-color-background: #333333;
  --dark-color-text: #636363;
  --dark-color-card-bg: #727272;
  --dark-card-border: #727272;
  --light-card-border: #727272;
}

/* Dark theme variables applied when `.theme-dark` class is present on `html` or `body` */
.theme-dark {
  --color-background: var(--dark-color-background);
  --color-text: var(--dark-color-text);
  --color-card-bg: #cccccc;
  --card-border: var(--dark-card-border);
  --color-footer-bg: var(--dark-color-footer-bg);
  --color-footer-text: var(--dark-color-footer-text);
  --header-bg: #111111;
  --table-row-bg: #222222;
  --table-row-alt-bg: #333333;
}

/* === [ 3. UNIVERSAL BASE & RESET ] === */
*, *::before, *::after { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  font-family: var(--font-primary);
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 16px;
  line-height: 1.6;
  transition: background-color 0.3s, color 0.3s;
  display: flex;
  flex-direction: column;
}
img { max-width: 100%; height: auto; }
a, button, input, h1, h2, h3, h4, p, div { font-family: var(--font-primary); font-weight: 400; }
a { color: inherit; text-decoration: none; }
ul { list-style: none; padding: 0; margin: 0; }
button { background: none; border: none; cursor: pointer; padding: 0; color: inherit; }
main { flex-grow: 1; }

/* === [ 4. UNIVERSAL CONTENT CONTAINER ] === */
.container {
  max-width: 2400px;
  width: 100%;
  margin: 0 auto;
  padding: 0 2rem;
  box-sizing: border-box;
}

textarea, input[type="text"], input[type="email"], input[type="password"], select {
  width: 100%;
  padding: 0.5rem;
  font-size: 1em;
  font-family: var(--font-primary);
  border: 1px solid var(--card-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-card-bg);
  color: var(--color-text);
}

/* === Responsive Breakpoints === */
/* Mobile Phones */
@media (max-width: 767px) {
  body { font-size: 0.9375rem; }
  .container { padding: 1rem 0.5rem; }
}
/* Tablets */
@media (min-width: 768px) and (max-width: 1023px) {
  .container { padding: 1.5rem 1rem; }
}
@media (min-width: 2400px) {
  .container { max-width: 2400px; }
}

---
## static/js/analysis-modal.js
---
// In static/js/analysis-modal.js

document.addEventListener('DOMContentLoaded', function() {
  const modal = document.getElementById('analysis-modal');
  if (!modal) return; // Exit if the modal isn't on the page

  const bar = document.getElementById('analysis-bar');
  const statusEl = document.getElementById('analysis-status');
  const closeBtn = document.getElementById('analysis-close');
  const timerEl = document.getElementById('analysis-timer'); // Get the timer element
  const statusUrl = document.body.dataset.analysisStatusUrl;

  let pollStatus;
  let timerInterval;
  let secondsElapsed = 0;

  // --- Timer Functions ---
  function startTimer() {
    if (timerEl) {
        secondsElapsed = 0;
        timerEl.textContent = '0s';
        timerInterval = setInterval(() => {
            secondsElapsed++;
            timerEl.textContent = `${secondsElapsed}s`;
        }, 1000);
    }
  }

  function stopTimer() {
    clearInterval(timerInterval);
  }

  // --- Modal Control Functions ---
  function openModal(opts = {}) {
    modal.classList.add('active');
    statusEl.textContent = 'Starting...';
    bar.style.width = '0%';
    startTimer(); // Start the timer when the modal opens
    
    if (opts.message) {
      statusEl.textContent = opts.message;
      stopTimer(); // Stop timer if it's just a message
    } else {
      fetchStatus();
      pollStatus = setInterval(fetchStatus, 1500);
    }
  }

  function closeModal() {
    modal.classList.remove('active');
    stopTimer(); // Stop the timer when the modal closes
    clearInterval(pollStatus);
  }

  function fetchStatus() {
    if (!statusUrl) return;
    fetch(statusUrl)
      .then(r => r.json())
      .then(d => {
        const pct = d.percent || 0;
        bar.style.width = pct + '%';
        
        if (d.status === 'failed') {
          statusEl.textContent = 'FAILED: ' + (d.error || 'Unknown error');
          stopTimer();
          clearInterval(pollStatus);
        } else if (d.status === 'complete') {
          statusEl.textContent = 'Complete';
          stopTimer();
          clearInterval(pollStatus);
        } else {
          statusEl.textContent = d.step || 'Analyzing...';
        }
      });
  }
  
  function setMessage(msg) {
      if(statusEl) statusEl.textContent = msg;
      stopTimer();
      clearInterval(pollStatus);
  }

  // --- Event Listeners ---
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  modal.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { e.preventDefault(); closeModal(); }
  });

  // Make the modal functions globally accessible
  window.AnalysisModal = { open: openModal, close: closeModal, setMessage: setMessage };
});

---
## static/js/artworks.js
---
// In static/js/artworks.js

document.addEventListener('DOMContentLoaded', () => {
  // --- Event Listener for all "Analyze" buttons ---
  document.querySelectorAll('.btn-analyze').forEach(btn => {
    btn.addEventListener('click', ev => {
      ev.preventDefault();
      const card = btn.closest('.gallery-card');
      if (!card) return;
      
      const provider = btn.dataset.provider;
      const filename = card.dataset.filename;
      
      if (!filename || !provider) {
        alert('Error: Missing filename or provider information.');
        return;
      }
      
      // Call the function to run the analysis
      runAnalyze(card, provider, filename);
    });
  });

  // --- Event Listener for all "Sign Artwork" buttons ---
  document.querySelectorAll('.btn-sign').forEach(btn => {
    btn.addEventListener('click', ev => {
      ev.preventDefault();
      const card = btn.closest('.gallery-card');
      if (!card) return;
      
      const baseName = btn.dataset.base;
      if (!baseName) {
        alert('Error: Missing artwork base name.');
        return;
      }

      showOverlay(card, 'Signing…');
      
      fetch(`/sign-artwork/${baseName}`, { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
          if (data.success) {
            // Success! Reload the thumbnail to show the signed version
            const thumb = card.querySelector('.card-img-top');
            thumb.src = `${thumb.src.split('?')[0]}?t=${new Date().getTime()}`;
            btn.textContent = 'Signed ✔';
            btn.disabled = true;
          } else {
            alert(`Signing failed: ${data.error}`);
          }
        })
        .catch(error => {
          console.error('Signing error:', error);
          alert(`An error occurred: ${error.error || 'Check console for details.'}`);
        })
        .finally(() => {
          hideOverlay(card);
        });
    });
  });
});

// --- Helper function to show a loading overlay on a card ---
function showOverlay(card, text) {
  let ov = card.querySelector('.card-overlay');
  if (!ov) {
    ov = document.createElement('div');
    ov.className = 'card-overlay';
    card.appendChild(ov);
  }
  ov.innerHTML = `<span class="spinner"></span> ${text}`;
  ov.classList.remove('hidden');
}

// --- Helper function to hide a loading overlay ---
function hideOverlay(card) {
  const ov = card.querySelector('.card-overlay');
  if (ov) ov.classList.add('hidden');
}

// --- Main function to handle the analysis process ---
function runAnalyze(card, provider, filename) {
  // Check if the provider API is configured
  const isConfigured = document.body.dataset[`${provider}Ok`] === 'true';
  if (!isConfigured) {
    alert(`${provider.charAt(0).toUpperCase() + provider.slice(1)} API Key is not configured. Please contact the administrator.`);
    return;
  }

  // Show the analysis modal and the card overlay
  if (window.AnalysisModal) window.AnalysisModal.open();
  showOverlay(card, `Analyzing…`);

  // Get the aspect ratio from the card's data attribute
  const aspect = card.dataset.aspect;
  // Build the correct URL
  const encodedFilename = filename.split('/').map(encodeURIComponent).join('/');
  const actionUrl = `/analyze/${encodeURIComponent(aspect)}/${encodedFilename}`;

  const formData = new FormData();
  formData.append('provider', provider);

  fetch(actionUrl, {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    body: formData
  })
  .then(resp => {
    if (!resp.ok) {
      return resp.json().then(errData => Promise.reject(errData));
    }
    return resp.json();
  })
  .then(data => {
    if (data.success && data.redirect_url) {
      if (window.AnalysisModal) window.AnalysisModal.setMessage('Complete! Redirecting...');
      // Wait a moment before redirecting
      setTimeout(() => {
        window.location.href = data.redirect_url;
      }, 1200);
    } else {
      throw new Error(data.error || 'Analysis failed to return a valid redirect URL.');
    }
  })
  .catch(error => {
    console.error('Analysis fetch error:', error);
    if (window.AnalysisModal) window.AnalysisModal.setMessage(`Error: ${error.error || 'A server error occurred.'}`);
    hideOverlay(card);
  });
}

---
## static/js/edit_listing.js
---
// static/js/edit_listing.js

document.addEventListener('DOMContentLoaded', () => {
  // === [ 0. FALLBACK IMAGE HANDLER FOR MOCKUP THUMBS ] ===
  document.querySelectorAll('.mockup-thumb-img').forEach(img => {
    img.addEventListener('error', function handleError() {
      if (this.dataset.fallback && this.src !== this.dataset.fallback) {
        this.src = this.dataset.fallback;
      }
      this.onerror = null; // Prevent loop
    });
  });

  // === [ 1. MODAL CAROUSEL LOGIC ] ===
  const carousel = document.getElementById('mockup-carousel');
  const carouselImg = document.getElementById('carousel-img');
  const images = Array.from(document.querySelectorAll('.mockup-img-link, .main-thumb-link'));
  let currentIndex = 0;

  function showImage(index) {
    if (index >= 0 && index < images.length) {
      currentIndex = index;
      carouselImg.src = images[currentIndex].dataset.img;
      carousel.classList.add('active');
    }
  }

  function hideCarousel() {
    carousel.classList.remove('active');
  }

  images.forEach((link, index) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      showImage(index);
    });
  });

  if (carousel) {
    carousel.querySelector('#carousel-close').addEventListener('click', hideCarousel);
    carousel.querySelector('#carousel-prev').addEventListener('click', () => showImage((currentIndex - 1 + images.length) % images.length));
    carousel.querySelector('#carousel-next').addEventListener('click', () => showImage((currentIndex + 1) % images.length));
    
    carousel.addEventListener('click', (e) => {
        if (e.target === carousel) {
            hideCarousel();
        }
    });

    document.addEventListener('keydown', (e) => {
      if (carousel.classList.contains('active')) {
        if (e.key === 'ArrowLeft') showImage((currentIndex - 1 + images.length) % images.length);
        if (e.key === 'ArrowRight') showImage((currentIndex + 1) % images.length);
        if (e.key === 'Escape') hideCarousel();
      }
    });
  }

  // === [ 2. ASYNC MOCKUP SWAP LOGIC ] ===
  document.querySelectorAll('.swap-btn').forEach(button => {
    button.addEventListener('click', async (event) => {
      event.preventDefault();

      const mockupCard = button.closest('.mockup-card'); // Get the parent card
      if (mockupCard.classList.contains('swapping')) return; // Prevent double clicks

      const slotIndex = parseInt(button.dataset.index, 10);
      const controlsContainer = button.closest('.swap-controls');
      const select = controlsContainer.querySelector('select[name="new_category"]');
      const newCategory = select.value;
      
      const currentImg = document.getElementById(`mockup-img-${slotIndex}`);
      const currentSrc = currentImg ? currentImg.src : '';

      mockupCard.classList.add('swapping');

      try {
        const response = await fetch('/edit/swap-mockup-api', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            seo_folder: window.EDIT_INFO.seoFolder,
            slot_index: slotIndex,
            new_category: newCategory,
            aspect: window.EDIT_INFO.aspect,
            current_mockup_src: currentSrc.split('/').pop().split('?')[0]
          }),
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.error || 'Failed to swap mockup.');
        }

        const timestamp = new Date().getTime();
        const mockupImg = document.getElementById(`mockup-img-${slotIndex}`);
        const mockupLink = document.getElementById(`mockup-link-${slotIndex}`);

        if (mockupImg) {
          mockupImg.src = `${data.new_thumb_url}?t=${timestamp}`;
          mockupImg.dataset.fallback = `${data.new_mockup_url}?t=${timestamp}`;
        }
        if (mockupLink) {
          mockupLink.href = `${data.new_mockup_url}?t=${timestamp}`;
          mockupLink.dataset.img = `${data.new_mockup_url}?t=${timestamp}`;
        }

      } catch (error) {
        console.error('Swap failed:', error);
        alert(`Error: ${error.message}`);
      } finally {
        mockupCard.classList.remove('swapping');
      }
    });
  });

  // === [ 3. ASYNC UPDATE IMAGE URLS ] ===
  const updateLinksBtn = document.getElementById('update-links-btn');
  if (updateLinksBtn) {
    updateLinksBtn.addEventListener('click', async () => {
      const originalText = updateLinksBtn.textContent;
      updateLinksBtn.textContent = 'Updating...';
      updateLinksBtn.disabled = true;

      try {
        const url = `/update-links/${window.EDIT_INFO.aspect}/${window.EDIT_INFO.seoFolder}.jpg`;
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'Server error');
        
        const joined = data.images.join('\n');
        document.getElementById('images-input').value = joined;
        const publicBox = document.getElementById('public-image-urls');
        if (publicBox) publicBox.value = joined;
      } catch (error) {
        alert(`Error updating image links: ${error.message}`);
      } finally {
        updateLinksBtn.textContent = originalText;
        updateLinksBtn.disabled = false;
      }
    });
  }
  
  // === [ 4. ASYNC GENERIC TEXT REWORDING ] ===
  const rewordContainer = document.getElementById('generic-text-reworder');
  if (rewordContainer) {
    const descriptionTextarea = document.getElementById('description-input');
    const spinner = document.getElementById('reword-spinner');
    const genericTextInput = document.getElementById('generic-text-input');
    const buttons = rewordContainer.querySelectorAll('button');

    rewordContainer.addEventListener('click', async (event) => {
      if (!event.target.matches('#reword-openai-btn, #reword-gemini-btn')) {
        return;
      }
      const button = event.target;
      const provider = button.dataset.provider;
      const genericText = genericTextInput.value;
      const currentDescription = descriptionTextarea.value;
      
      buttons.forEach(b => b.disabled = true);
      spinner.style.display = 'block';

      try {
          const response = await fetch('/api/reword-generic-text', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  provider: provider,
                  artwork_description: currentDescription,
                  generic_text: genericText
              })
          });

          const data = await response.json();
          if (!response.ok) throw new Error(data.error || 'Failed to reword text.');
          
          genericTextInput.value = data.reworded_text;

      } catch (error) {
          console.error('Reword failed:', error);
          alert(`Error: ${error.message}`);
      } finally {
          buttons.forEach(b => b.disabled = false);
          spinner.style.display = 'none';
      }
    });
  }

  // === [ 5. RE-ANALYZE MODAL TRIGGER ] ===
  const analyzeForm = document.querySelector('.analyze-form');
  if (analyzeForm) {
    analyzeForm.addEventListener('submit', () => {
      // Open the modal from analysis-modal.js when the form is submitted
      if (window.AnalysisModal) {
        window.AnalysisModal.open();
      }
    });
  }
});

---
## static/js/gallery.js
---
document.addEventListener('DOMContentLoaded', () => {
  const modalBg = document.getElementById('final-modal-bg');
  const modalImg = document.getElementById('final-modal-img');
  const closeBtn = document.getElementById('final-modal-close');
  const grid = document.querySelector('.finalised-grid');
  const viewKey = grid ? grid.dataset.viewKey || 'view' : 'view';
  document.querySelectorAll('.final-img-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      if (modalBg && modalImg) {
        modalImg.src = link.dataset.img;
        modalBg.style.display = 'flex';
      }
    });
  });
  if (closeBtn) closeBtn.onclick = () => {
    modalBg.style.display = 'none';
    modalImg.src = '';
  };
  if (modalBg) modalBg.onclick = e => {
    if (e.target === modalBg) {
      modalBg.style.display = 'none';
      modalImg.src = '';
    }
  };
  document.querySelectorAll('.locked-delete-form').forEach(f => {
    f.addEventListener('submit', ev => {
      const val = prompt('This listing is locked and will be permanently deleted. Type DELETE to confirm');
      if (val !== 'DELETE') { ev.preventDefault(); }
      else { f.querySelector('input[name="confirm"]').value = 'DELETE'; }
    });
  });
  const gBtn = document.getElementById('grid-view-btn');
  const lBtn = document.getElementById('list-view-btn');
  function apply(v) {
    if (!grid) return;
    if (v === 'list') { grid.classList.add('list-view'); }
    else { grid.classList.remove('list-view'); }
  }
  if (gBtn) gBtn.addEventListener('click', () => { apply('grid'); localStorage.setItem(viewKey, 'grid'); });
  if (lBtn) lBtn.addEventListener('click', () => { apply('list'); localStorage.setItem(viewKey, 'list'); });
  apply(localStorage.getItem(viewKey) || 'grid');
});


---
## static/js/main.js
---
document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    const menuClose = document.getElementById('menu-close');
    const overlayMenu = document.getElementById('overlay-menu');
    const themeToggle = document.getElementById('theme-toggle');
    const rootEl = document.documentElement;

    // --- Menu Logic ---
    if (menuToggle && menuClose && overlayMenu) {
        menuToggle.addEventListener('click', () => {
            overlayMenu.classList.add('is-active');
            document.body.style.overflow = 'hidden';
        });

        menuClose.addEventListener('click', () => {
            overlayMenu.classList.remove('is-active');
            document.body.style.overflow = '';
        });
    }

    // --- Theme Logic ---
    const applyTheme = (theme) => {
        rootEl.classList.remove('theme-light', 'theme-dark');
        rootEl.classList.add('theme-' + theme);
        localStorage.setItem('theme', theme);
    };

    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initial = savedTheme || (prefersDark ? 'dark' : 'light');
    applyTheme(initial);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const next = rootEl.classList.contains('theme-dark') ? 'light' : 'dark';
            applyTheme(next);
        });
    }

    // --- Gemini Modal Logic ---
    const modal = document.getElementById('gemini-modal');
    const modalTitle = document.getElementById('gemini-modal-title');
    const modalBody = document.getElementById('gemini-modal-body');
    const closeBtn = document.querySelector('.gemini-modal-close');
    const copyBtn = document.getElementById('gemini-copy-btn');

    const defaultPrompts = {
        'generate-description': `Act as an expert art critic. Write an evocative and compelling gallery description for a piece of art titled "{ART_TITLE}". Focus on the potential materials, the mood it evokes, and the ideal setting for it. Make it about 150 words.`,
        'create-social-post': `Generate a short, engaging Instagram post to promote a piece of art titled "{ART_TITLE}". Include a catchy opening line, a brief description, and 3-5 relevant hashtags.`
    };

    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = 'none';
        };
    }
    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };

    document.querySelectorAll('.btn-gemini').forEach(button => {
        button.addEventListener('click', async (e) => {
            const action = e.target.dataset.action;
            const artPiece = e.target.closest('.art-piece');
            const artTitle = artPiece.querySelector('h2').textContent;

            let promptTemplate = '';
            let title = '';

            if (action === 'generate-description') {
                title = '✨ AI Art Description';
                promptTemplate = localStorage.getItem('geminiDescriptionPrompt') || defaultPrompts[action];
            } else if (action === 'create-social-post') {
                title = '✨ AI Social Media Post';
                promptTemplate = defaultPrompts[action];
            }

            const prompt = promptTemplate.replace('{ART_TITLE}', artTitle);

            modalTitle.textContent = title;
            modalBody.innerHTML = '<div class="loader"></div>';
            modal.style.display = 'flex';

            try {
                let chatHistory = [{ role: "user", parts: [{ text: prompt }] }];
                const payload = { contents: chatHistory };
                const apiKey = "";
                const apiUrl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + apiKey;

                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    throw new Error("API error: " + response.status + " " + response.statusText);
                }

                const result = await response.json();

                if (result.candidates && result.candidates.length > 0 &&
                    result.candidates[0].content && result.candidates[0].content.parts &&
                    result.candidates[0].content.parts.length > 0) {
                    const text = result.candidates[0].content.parts[0].text;
                    modalBody.innerHTML = '<textarea id="gemini-result">' + text + '</textarea>';
                } else {
                    throw new Error("Invalid response structure from API.");
                }

            } catch (error) {
                console.error("Gemini API call failed:", error);
                modalBody.innerHTML = '<p>Sorry, something went wrong. Please try again. (' + error.message + ')</p>';
            }
        });
    });

    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const resultTextarea = document.getElementById('gemini-result');
            if (resultTextarea) {
                resultTextarea.select();
                document.execCommand('copy');
                copyBtn.textContent = 'Copied!';
                setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
            }
        });
    }
});


---
## static/js/mockup-admin.js
---
document.addEventListener('DOMContentLoaded', () => {
    // --- Element Definitions ---
    const mockupGrid = document.getElementById('mockup-grid');
    const arSelector = document.getElementById('aspect-ratio-selector');
    const perPageSelector = document.getElementById('per-page-selector');
    const sortSelector = document.getElementById('sort-selector');
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const imageModal = document.getElementById('image-modal');
    const duplicatesModal = document.getElementById('duplicates-modal');
    const uploadModal = document.getElementById('upload-modal');
    const uploadModalContent = `
        <div class="analysis-box">
            <img src="/static/icons/svg/light/upload-light.svg" class="progress-icon" alt="">
            <h3>Uploading Mockups...</h3>
            <div id="upload-filename" class="analysis-status"></div>
            <div class="analysis-progress">
                <div id="upload-bar" class="analysis-progress-bar"></div>
            </div>
            <div id="upload-status" class="analysis-status">0%</div>
        </div>`;

    // --- Page Controls ---
    function updateUrlParams() {
        const aspect = arSelector.value;
        const perPage = perPageSelector.value;
        const sortBy = sortSelector.value;
        const urlParams = new URLSearchParams(window.location.search);
        const category = urlParams.get('category') || 'All';
        window.location.href = `/admin/mockups/${aspect}?per_page=${perPage}&category=${category}&sort=${sortBy}`;
    }

    if (arSelector) arSelector.addEventListener('change', updateUrlParams);
    if (perPageSelector) perPageSelector.addEventListener('change', updateUrlParams);
    if (sortSelector) sortSelector.addEventListener('change', updateUrlParams);

    function selectOptionByText(selectEl, textToFind) {
        const text = (textToFind || '').trim().toLowerCase();
        for (let i = 0; i < selectEl.options.length; i++) {
            const option = selectEl.options[i];
            if (option.text.trim().toLowerCase() === text) {
                selectEl.selectedIndex = i;
                return;
            }
        }
    }

    // --- Main Grid Event Delegation ---
    if (mockupGrid) {
        mockupGrid.addEventListener('click', async (e) => {
            const card = e.target.closest('.gallery-card');
            if (!card) return;

            const filename = card.dataset.filename;
            const originalCategory = card.dataset.category;
            const overlay = card.querySelector('.card-overlay');
            const button = e.target;
            const currentAspect = arSelector.value;

            if (button.classList.contains('card-img-top')) {
                const fullSizeUrl = button.dataset.fullsizeUrl;
                if (fullSizeUrl && imageModal) {
                    imageModal.querySelector('.modal-img').src = fullSizeUrl;
                    imageModal.style.display = 'flex';
                }
                return;
            }

            const actionsContainer = card.querySelector('.categorize-actions');
            if (actionsContainer) {
                if (button.classList.contains('btn-categorize')) {
                    const selectElement = actionsContainer.querySelector('select');
                    overlay.innerHTML = `<span class="spinner"></span> Asking AI...`;
                    overlay.classList.remove('hidden');
                    button.disabled = true;
                    try {
                        const response = await fetch("/admin/mockups/suggest-category", {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ filename: filename, aspect: currentAspect })
                        });
                        const result = await response.json();
                        if (result.success) {
                            selectOptionByText(selectElement, result.suggestion);
                        } else {
                            alert(`Error: ${result.error}`);
                        }
                    } catch (err) {
                        alert('A network error occurred.');
                    } finally {
                        overlay.classList.add('hidden');
                        button.disabled = false;
                    }
                }

                if (button.classList.contains('btn-save-move')) {
                    const newCategory = actionsContainer.querySelector('select').value;
                    if (!newCategory) {
                        alert('Please select a category.');
                        return;
                    }
                    overlay.innerHTML = `<span class="spinner"></span> Moving...`;
                    overlay.classList.remove('hidden');

                    const response = await fetch("/admin/mockups/move-mockup", {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ filename, aspect: currentAspect, original_category: originalCategory, new_category: newCategory })
                    });
                    const result = await response.json();
                    if (result.success) {
                        card.remove(); 
                    } else {
                        overlay.textContent = `Error: ${result.error}`;
                    }
                }
            }
            
            if (button.classList.contains('btn-delete')) {
                if (!confirm(`Are you sure you want to permanently delete "${filename}"?`)) return;
                overlay.innerHTML = `<span class="spinner"></span> Deleting...`;
                overlay.classList.remove('hidden');

                const response = await fetch("/admin/mockups/delete-mockup", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ filename, aspect: currentAspect, category: originalCategory })
                });
                const result = await response.json();
                if (result.success) {
                    card.remove();
                } else {
                    overlay.textContent = `Error: ${result.error}`;
                }
            }
        });
    }

    // --- Modal Logic ---
    [imageModal, duplicatesModal].forEach(modal => {
        if (modal) {
            const closeBtn = modal.querySelector('.modal-close');
            if(closeBtn) closeBtn.addEventListener('click', () => modal.style.display = 'none');
            modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
        }
    });

    // --- Find Duplicates Logic ---
    const findDuplicatesBtn = document.getElementById('find-duplicates-btn');
    if (findDuplicatesBtn) {
        findDuplicatesBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const btn = e.target;
            const originalText = btn.textContent;
            btn.textContent = 'Scanning...';
            btn.disabled = true;

            try {
                const response = await fetch(btn.dataset.url);
                const data = await response.json();
                const listEl = document.getElementById('duplicates-list');
                listEl.innerHTML = '';

                if (data.duplicates.length > 0) {
                    const ul = document.createElement('ul');
                    data.duplicates.forEach(pair => {
                        const li = document.createElement('li');
                        li.innerHTML = `<strong>${pair.original}</strong><br>is a duplicate of<br><em>${pair.duplicate}</em>`;
                        ul.appendChild(li);
                    });
                    listEl.appendChild(ul);
                } else {
                    listEl.innerHTML = '<p>No duplicates found. Good job!</p>';
                }
                duplicatesModal.style.display = 'flex';
            } catch (error) {
                alert('Failed to check for duplicates.');
            } finally {
                btn.textContent = originalText;
                btn.disabled = false;
            }
        });
    }

    // --- Drag & Drop Upload Logic ---
    if (dropzone && fileInput && uploadModal) {
        function uploadFile(file) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                const formData = new FormData();
                const currentAspect = arSelector.value;
                formData.append('mockup_files', file);

                xhr.upload.addEventListener('progress', e => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        const progressBar = uploadModal.querySelector('#upload-bar');
                        const statusEl = uploadModal.querySelector('#upload-status');
                        if(progressBar) progressBar.style.width = percent + '%';
                        if(statusEl) statusEl.textContent = `${percent}%`;
                    }
                });
                xhr.addEventListener('load', () => xhr.status < 400 ? resolve() : reject(new Error(`Server responded with ${xhr.status}`)));
                xhr.addEventListener('error', () => reject(new Error('Network error during upload.')));
                xhr.open('POST', `/admin/mockups/upload/${currentAspect}`, true);
                xhr.send(formData);
            });
        }

        async function uploadFiles(files) {
            if (!files || !files.length) return;
            uploadModal.innerHTML = uploadModalContent;
            uploadModal.classList.add('active');
            
            const progressBar = uploadModal.querySelector('#upload-bar');
            const statusEl = uploadModal.querySelector('#upload-status');
            const filenameEl = uploadModal.querySelector('#upload-filename');

            for (const file of Array.from(files)) {
                if(filenameEl) filenameEl.textContent = `Uploading: ${file.name}`;
                if(progressBar) progressBar.style.width = '0%';
                if(statusEl) statusEl.textContent = '0%';
                try {
                    await uploadFile(file);
                    if(statusEl) statusEl.textContent = 'Complete!';
                } catch (error) {
                    if(statusEl) statusEl.textContent = `Error uploading ${file.name}.`;
                    await new Promise(res => setTimeout(res, 2000));
                }
            }
            window.location.reload();
        }

        ['dragenter', 'dragover'].forEach(evt => dropzone.addEventListener(evt, e => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        }));
        ['dragleave', 'drop'].forEach(evt => dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover')));
        dropzone.addEventListener('drop', e => {
            e.preventDefault();
            uploadFiles(e.dataTransfer.files);
        });
        dropzone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => uploadFiles(fileInput.files));
    }
});

---
## static/js/upload.js
---
/* ================================
   DreamArtMachine Upload JS (XMLHttpRequest for Progress)
   ================================ */

document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  
  // Modal elements
  const modal = document.getElementById('upload-modal');
  const progressBar = document.getElementById('upload-bar');
  const statusEl = document.getElementById('upload-status');
  const filenameEl = document.getElementById('upload-filename');

  function uploadFile(file) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append('file', file);

      xhr.upload.addEventListener('progress', e => {
        if (e.lengthComputable) {
          const percentComplete = Math.round((e.loaded / e.total) * 100);
          progressBar.style.width = percentComplete + '%';
          statusEl.textContent = `${percentComplete}%`;
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.responseText);
        } else {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Upload failed due to a network error.')));
      xhr.addEventListener('abort', () => reject(new Error('Upload was aborted.')));

      xhr.open('POST', '/upload', true);
      xhr.setRequestHeader('Accept', 'application/json');
      xhr.send(formData);
    });
  }

  async function uploadFiles(files) {
    if (!files || !files.length) return;
    
    modal.classList.add('active');

    for (const file of Array.from(files)) {
      filenameEl.textContent = `Uploading: ${file.name}`;
      progressBar.style.width = '0%';
      statusEl.textContent = '0%';
      
      try {
        await uploadFile(file);
        statusEl.textContent = 'Complete!';
      } catch (error) {
        statusEl.textContent = `Error: ${error.message}`;
        await new Promise(res => setTimeout(res, 2000)); // Show error for 2s
      }
    }

    // Redirect after all files are processed
    modal.classList.remove('active');
    window.location.href = '/upload';
  }

  if (dropzone) {
    ['dragenter', 'dragover'].forEach(evt => {
      dropzone.addEventListener(evt, e => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
    });
    ['dragleave', 'drop'].forEach(evt => {
      dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover'));
    });
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      uploadFiles(e.dataTransfer.files);
    });
    dropzone.addEventListener('click', () => fileInput.click());
  }

  if (fileInput) {
    fileInput.addEventListener('change', () => uploadFiles(fileInput.files));
  }
});

---
## templates/404.html
---
{% extends "main.html" %}
{% block title %}Page Not Found{% endblock %}
{% block content %}
<h1>Page Not Found</h1>
<p>Looks like this page doesn’t exist. Head back <a href="{{ url_for('home.home') }}">home</a>.</p>
{% endblock %}


---
## templates/500.html
---
{% extends "main.html" %}
{% block title %}Server Error{% endblock %}
{% block content %}
<h1>Something went wrong</h1>
<p class="page-description">We've logged the error and will fix it ASAP.</p>
<div class="main-content">
  <p><a href="{{ url_for('home.home') }}">Return to home</a></p>
</div>
{% endblock %}


---
## templates/artworks.html
---
{% extends "main.html" %}
{% block title %}Artworks | DreamArtMachine{% endblock %}
{% block content %}
<h1><img src="{{ url_for('static', filename='icons/svg/light/number-circle-two-light.svg') }}" class="hero-step-icon" alt="Step 2: Artwork" />Artwork</h1>
<p class="page-description">Browse and analyze uploaded artworks.</p>

{% if artworks %}
<div class="artwork-grid">
  {% for art in artworks %}
  <article class="gallery-card" data-filename="{{ art.filename }}" data-aspect="{{ art.aspect|default('unknown') }}">
    <div class="card-thumb">
      {% if art.thumb_path %}
      <img class="card-img-top" src="{{ get_artwork_image_url('unanalysed', art.thumb_path) }}" alt="{{ art.filename }}">
      {% else %}
      <div class="card-img-top placeholder">No thumbnail</div>
      {% endif %}
    </div>

    <div class="card-body">
      <h3 class="card-title">{{ art.filename }}</h3>
      <p class="card-meta">SKU: {{ art.sku or '—' }}<br>Uploaded: {{ art.upload_date }}</p>

      <div class="button-row">
        <button class="btn btn-primary btn-analyze" data-provider="openai">Analyze</button>

        {% if art.edit_url %}
          <a class="btn btn-secondary" href="{{ art.edit_url }}">Edit</a>
        {% endif %}
        {% if art.review_url %}
          <a class="btn btn-secondary" href="{{ art.review_url }}">Review</a>
        {% endif %}

        <form method="post" action="{{ url_for('home.delete_unanalysed_artwork', slug=art.slug) }}" onsubmit="return confirm('Delete this artwork and its files? This cannot be undone.');">
          <button type="submit" class="btn btn-danger">Delete</button>
        </form>
      </div>
    </div>

    <div class="card-overlay hidden"></div>
  </article>
  {% endfor %}
</div>
{% else %}
<p>No artworks uploaded yet.</p>
{% endif %}
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/artworks.js') }}"></script>
{% endblock %}


---
## templates/edit_listing.html
---
{% extends "main.html" %}
{% block title %}Edit Listing{% endblock %}
{% block content %}
<h1>Edit Listing</h1>
<p class="page-description">Review metadata, preview mockups and finalise your artwork.</p>
<section class="main-content">
  <p>Listing editing tools are coming soon.</p>
</section>
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/edit_listing.js') }}"></script>
{% endblock %}


---
## templates/finalised.html
---
{% extends "main.html" %}
{% block title %}Finalised Artworks{% endblock %}
{% block content %}
<h1><img src="{{ url_for('static', filename='icons/svg/light/number-circle-four-light.svg') }}" class="hero-step-icon" alt="Step 4: Finalised" />Finalised Artworks</h1>
<p class="page-description">Artworks ready for export.</p>
<section class="main-content">
  <p>No finalised artworks yet.</p>
</section>
{% endblock %}


---
## templates/home.html
---
{# Use blueprint-prefixed endpoints like 'home.home' in url_for #}
{% extends "main.html" %}
{% block title %}DreamArtMachine Home{% endblock %}
{% block content %}


<!-- ========== [IN.1] Home Hero Section ========== -->
<div class="home-hero">
  <h1>Welcome to Dream Art Machine Listing Machine</h1>
  <p class="home-intro">
    G’day! Start in the Artwork section, analyze new pieces, review your AI-generated listings and mockups, and prep everything for marketplace export—all streamlined for you.
  </p>
</div>

<!-- ========== [IN.2] Home Quick Actions ========== -->
<div id="workflow-panels" class="workflow-row">
  <a href="{{ url_for('artwork.upload_artwork') }}" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-one-light.svg') }}" class="step-btn-icon" alt="Step 1" />
    Upload Artwork
  </a>
  <a href="{{ url_for('home.artworks') }}" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-two-light.svg') }}" class="step-btn-icon" alt="Step 2" />
    Artwork<br>Select to Analyze
  </a>
  {% if latest_artwork %}
    <a href="{{ url_for('finalise.review', slug=latest_artwork.slug) }}" class="workflow-btn">
      <img src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}" class="step-btn-icon" alt="Step 3" />
      Edit Review<br>and Finalise Artwork
    </a>
  {% else %}
    <span class="workflow-btn disabled">
      <img src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}" class="step-btn-icon" alt="Step 3" />
      Edit Review<br>and Finalise Artwork
    </span>
  {% endif %}
  <a href="{{ url_for('home.finalised') }}" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-four-light.svg') }}" class="step-btn-icon" alt="Step 4" />
    Finalised Gallery<br>(Select to List)
  </a>
  <span class="workflow-btn disabled">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-five-light.svg') }}" class="step-btn-icon" alt="Step 5" />
    List Artwork<br>(Export to Sellbrite)
  </span>
</div>

<!-- ========== [IN.3] How It Works Section ========== -->
<section class="how-it-works">
  <h2>How It Works</h2>
  <ol>
    <li><b>Upload:</b> Chuck your artwork into the gallery (easy drag & drop).</li>
    <li><b>Analyze:</b> Let the AI do its magic—SEO, titles, pro description, the lot.</li>
    <li><b>Edit & Finalise:</b> Quick review and tweak, fix anything you like.</li>
    <li><b>Mockups:</b> Instantly see your art in bedrooms, offices, nurseries—looks a million bucks.</li>
    <li><b>Final Gallery:</b> See all your finished work, ready for showtime.</li>
    <li><b>Export:</b> Coming soon! Blast your art onto Sellbrite and more with one click.</li>
  </ol>
</section>
{% endblock %}


---
## templates/index.html
---
{# Use blueprint-prefixed endpoints like 'home.home' in url_for #}
{% extends "main.html" %}
{% block title %}DreamArtMachine Home{% endblock %}
{% block content %}
<div class="container">

<!-- ========== [IN.1] Home Hero Section ========== -->
<div class="home-hero">
  <h1><img src="{{ url_for('static', filename='logos/logo-vector.svg') }}" alt="DreamArtMachine Logo" class="logo"/>Welcome to DreamArtMachine Art Listing Machine</h1>
  <p class="home-intro">
    G’day! Start in the Artwork section, analyze new pieces, review your AI-generated listings and mockups, and prep everything for marketplace export—all streamlined for you.
  </p>
</div>

<!-- ========== [IN.2] Home Quick Actions ========== -->
<div class="workflow-row">
  <a href="{{ url_for('artwork.upload_artwork') }}" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-one-light.svg') }}" class="step-btn-icon" alt="Step 1" />
    Upload Artwork
  </a>
  <a href="{{ url_for('home.artworks') }}" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-two-light.svg') }}" class="step-btn-icon" alt="Step 2" />
    Artwork<br>Select to Analyze
  </a>
  {% if latest_artwork %}
    <a href="{{ url_for('finalise.review', slug=latest_artwork.slug) }}" class="workflow-btn">
      <img src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}" class="step-btn-icon" alt="Step 3" />
      Edit Review<br>and Finalise Artwork
    </a>
  {% else %}
    <span class="workflow-btn disabled">
      <img src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}" class="step-btn-icon" alt="Step 3" />
      Edit Review<br>and Finalise Artwork
    </span>
  {% endif %}
  <a href="{{ url_for('home.finalised') }}" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-four-light.svg') }}" class="step-btn-icon" alt="Step 4" />
    Finalised Gallery<br>(Select to List)
  </a>
  <span class="workflow-btn disabled">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-five-light.svg') }}" class="step-btn-icon" alt="Step 5" />
    List Artwork<br>(Export to Sellbrite)
  </span>
</div>

<!-- ========== [IN.3] How It Works Section ========== -->
<section class="how-it-works">
  <h2>How It Works</h2>
  <ol>
    <li><b>Upload:</b> Chuck your artwork into the gallery (easy drag & drop).</li>
    <li><b>Analyze:</b> Let the AI do its magic—SEO, titles, pro description, the lot.</li>
    <li><b>Edit & Finalise:</b> Quick review and tweak, fix anything you like.</li>
    <li><b>Mockups:</b> Instantly see your art in bedrooms, offices, nurseries—looks a million bucks.</li>
    <li><b>Final Gallery:</b> See all your finished work, ready for showtime.</li>
    <li><b>Export:</b> Coming soon! Blast your art onto Sellbrite and more with one click.</li>
  </ol>
</section>
</div>
{% endblock %}


---
## templates/login.html
---
{% extends "main.html" %}
{% block title %}Login{% endblock %}
{% block content %}
<h1>Login</h1>
<p class="page-description">Enter your credentials to access DreamArtMachine.</p>
<div class="main-content">
  {% with msgs = get_flashed_messages(with_categories=true) %}
    {% if msgs %}
      <div class="flash">
        <img src="{{ url_for('static', filename='icons/svg/light/warning-circle-light.svg') }}" alt="Warning" style="width:20px;margin-right:6px;vertical-align:middle;">
        {% for cat, msg in msgs %}
          {{ msg }}
        {% endfor %}
      </div>
    {% endif %}
  {% endwith %}
  <form method="post" class="login-form">
    <label for="username">Username</label>
    <input id="username" name="username" type="text" required>
    <label for="password">Password</label>
    <input id="password" name="password" type="password" required>
    <button type="submit" class="btn btn-primary wide-btn">Login</button>
  </form>
</div>
{% endblock %}


---
## templates/main-design-template.html
---
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ART Narrator</title>
    <style>
        /* --- Global Styles & Variables --- */
        :root {
            --font-primary: monospace !important;
            
            /* Light Theme Colors */
            --color-background: #FFFFFF;
            --color-text: #111111;
            --color-overlay-bg: rgba(248, 248, 248, 0.85);
            --color-card-bg: #f9f9f9;
            --color-header-border: #eeeeee;
            --color-footer-bg: #FFFFFF;
            --color-footer-text: #111111;
            --color-footer-border: #dddddd;

            /* Dark Theme Colors */
            --dark-color-background: #111111;
            --dark-color-text: #FFFFFF;
            --dark-color-card-bg: #1a1a1a;
            --dark-color-header-border: #2a2a2a;

            /* Universal Colors */
            --color-hover: #ffa52a;
            --color-btn-bg: #111;
            --color-btn-text: #fff;
            --color-delete-hover: #8B0000;
            --ease-quart: cubic-bezier(0.77, 0, 0.175, 1);
        }

        body.dark-theme {
            --color-background: var(--dark-color-background);
            --color-text: var(--dark-color-text);
            /* --color-overlay-bg is intentionally not changed for dark theme */
            --color-card-bg: var(--dark-color-card-bg);
            --color-header-border: var(--dark-color-header-border);
            --color-btn-bg: #222;
        }

        /* --- Base & Reset --- */
        *, *::before, *::after {
            box-sizing: border-box;
        }

        html, body {
            height: 100%;
        }

        body {
            margin: 0;
            font-family: var(--font-primary);
            background-color: var(--color-background);
            color: var(--color-text);
            font-size: 16px;
            line-height: 1.6;
            transition: background-color 0.3s, color 0.3s;
            display: flex;
            flex-direction: column;
        }

        a, button, input, h1, h2, h3, h4, p, div {
             font-family: var(--font-primary);
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        ul {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        button {
            background: none;
            border: none;
            cursor: pointer;
            padding: 0;
            color: inherit; /* Ensure buttons inherit color */
        }
        
        main {
            flex-grow: 1;
        }

        /* --- Header --- */
        .site-header, .overlay-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1rem;
            width: 100%;
        }
        
        .site-header {
            position: sticky;
            top: 0;
            z-index: 100;
            background-color: var(--color-background);
            transition: background-color 0.3s, color 0.3s;
            border-bottom: 1px solid var(--color-header-border);
            color: var(--color-text); /* Ensure header text/icons match theme */
        }

        .header-left, .header-right {
            flex: 1;
        }
        .header-center {
            flex-grow: 0;
        }
        .header-right {
            display: flex;
            justify-content: flex-end;
        }

        .site-logo {
            font-weight: 400;
            font-size: 1.3rem;
            letter-spacing: 0.5px;
        }

        .logo-icon {
        width: 35px;
        height: 35px;
        margin-right: 6px;
        margin-bottom: none;
        vertical-align: bottom;
        }

        .menu-toggle-btn, .menu-close-btn {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 1rem;
            font-weight: 500;
        }

        .menu-toggle-btn svg, .menu-close-btn svg {
            width: 16px;
            height: 16px;
        }
        
        .theme-toggle-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 44px;
            height: 44px;
        }

        .theme-toggle-btn svg {
            width: 24px;
            height: 24px;
        }

        .sun-icon { display: block; }
        .moon-icon { display: none; }
        body.dark-theme .sun-icon { display: none; }
        body.dark-theme .moon-icon { display: block; }


        /* --- Overlay Menu --- */
        .overlay-menu {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100vh;
            background-color: var(--color-overlay-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            z-index: 999;
            display: flex;
            flex-direction: column;
            padding: 0;
            opacity: 0;
            visibility: hidden;
            transform: translateY(20px);
            transition: opacity 0.5s var(--ease-quart), visibility 0.5s var(--ease-quart), transform 0.5s var(--ease-quart);
            overflow-y: auto;
            color: #111111; /* Force dark text inside the light overlay */
        }

        .overlay-menu.is-active {
            opacity: 1;
            visibility: visible;
            transform: translateY(0);
        }

        .overlay-header {
            flex-shrink: 0;
            position: sticky;
            top: 0;
            background-color: var(--color-overlay-bg);
        }

        .overlay-nav {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            flex-grow: 1;
            padding: 4rem 2rem;
            gap: 2rem;
            width: 100%;
            max-width: 1200px;
            margin: 0 auto 50px auto; /* Center horizontally */
        }

        .nav-column h3 {
            font-size: 1rem;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            opacity: 0.5;
            margin: 0 0 1.5rem 0;
        }

        .nav-column ul {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .nav-column a {
            font-size: 1.2em;
            font-weight: 500;
            line-height: 1.3;
            display: inline-block;
            transition: color 0.3s var(--ease-quart);
        }

        .nav-column a:hover {
            color: var(--color-hover);
        }

        /* --- Home Page Content --- */
        .home-content-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 2rem;
            padding: 2rem;
            max-width: 1200px;
            margin: 2rem auto 0 auto; /* Center horizontally */
        }

        .art-piece {
            display: flex;
            flex-direction: column;
        }
        .art-piece-info {
            background-color: var(--color-card-bg);
            padding: 1rem;
            text-align: center;
            transition: background-color 0.3s;
        }
        .art-piece img {
            max-width: 100%;
            height: auto;
            display: block;
            background-color: #eee;
        }
        .art-piece h2 {
            font-size: 1.1rem;
            margin: 0 0 0.5rem 0;
        }
        .art-piece p {
            font-size: 0.9rem;
            margin: 0;
            opacity: 0.8;
        }
        
        .art-actions {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-top: 1rem;
        }

        .btn-action {
            width: 100%;
            background-color: var(--color-btn-bg);
            color: var(--color-btn-text);
            padding: 0.75rem 1rem;
            font-weight: 500;
            text-align: center;
            transition: background-color 0.3s;
        }
        
        .btn-gemini {
             background-color: var(--color-hover);
             color: var(--color-btn-text);
        }
        
        .btn-gemini:hover {
            opacity: 0.8;
        }

        .btn-action.btn-analyse:hover {
            background-color: var(--color-hover);
        }

        .btn-action.btn-delete:hover {
            background-color: var(--color-delete-hover);
        }

        /* --- Footer --- */
        .site-footer {
            background-color: var(--color-footer-bg);
            color: var(--color-footer-text);
            height: 400px;
            display: flex;
            margin-top: 3rem;
            flex-direction: column;
            justify-content: center;
            border-top: 1px solid var(--color-footer-border);
        }

        .footer-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 2rem;
            max-width: 1200px;
            width: 100%;
            margin: 0 auto;
            padding: 0 2rem;
        }

        .footer-column h4 {
            font-size: 1rem;
            margin: 20px 0 1rem 0;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.7;
        }

        .footer-column ul {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .footer-column a {
            opacity: 0.9;
            transition: opacity 0.3s;
        }
        .footer-column a:hover {
            opacity: 1;
            color: var(--color-hover);
        }

        .copyright-bar {
            padding: 1rem 2rem;
            text-align: center;
            font-size: 0.8rem;
            margin-top: auto; /* Pushes to the bottom of the flex container */
        }
        
        /* --- Gemini Modal --- */
        .gemini-modal {
            position: fixed;
            z-index: 1001;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.5);
            display: none;
            align-items: center;
            justify-content: center;
        }

        .gemini-modal-content {
            background-color: var(--color-background);
            color: var(--color-text);
            margin: auto;
            padding: 2rem;
            border: 1px solid #888;
            width: 80%;
            max-width: 600px;
            position: relative;
        }
        
        .gemini-modal-close {
            position: absolute;
            top: 1rem;
            right: 1.5rem;
            font-size: 1.5rem;
            font-weight: bold;
            cursor: pointer;
        }

        .gemini-modal-body textarea {
            width: 100%;
            min-height: 200px;
            margin-top: 1rem;
            background-color: var(--color-card-bg);
            color: var(--color-text);
            border: 1px solid var(--color-header-border);
            padding: 0.5rem;
        }
        
        .gemini-modal-actions {
            margin-top: 1rem;
            display: flex;
            gap: 1rem;
        }

        .loader {
            border: 4px solid #f3f3f3;
            border-radius: 50%;
            border-top: 4px solid var(--color-hover);
            width: 40px;
            height: 40px;
            animation: spin 2s linear infinite;
            margin: 2rem auto;
        }

        @media (min-width: 1400px) {
            .home-content-grid {
                max-width: 1400px;
            }
        }

        @media (min-width: 1600px) {
            .home-content-grid {
                max-width: 1600px;
            }
        }

        @media (min-width: 1800px) {
            .home-content-grid {
                max-width: 1800px;
            }
        }

        @media (min-width: 2400px) {
            .home-content-grid {
                max-width: 2400px;
            }
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }


        /* Responsive */
        @media (max-width: 900px) {
            .overlay-nav {
                grid-template-columns: 1fr;
                justify-items: center;
                text-align: center;
                gap: 3rem;
            }
            .nav-column a {
                font-size: 1.5rem;
            }
            .footer-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .site-logo {
            font-weight: 400;
            font-size: 1rem;
            letter-spacing: none;
            }
            .logo-icon {
                width: 30px;
                height: 30px;
                margin-right: 4px;
            }
            .nav-column a {
                font-size: .9em;
                line-height: .2em;
                display: inline-block;
            }
            .nav-column ul {
                gap: .5rem;
                margin-bottom: 30px;
            }
        }
        
        @media (max-width: 600px) {
            .site-footer {
                height: auto; /* Allow footer to grow on small screens */
            }
            .footer-grid {
                grid-template-columns: 1fr;
                text-align: center;
                gap: 2rem;
            }
            .copyright-bar {
                margin-top: 2rem;
            }
            .site-logo {
                font-weight: 400;
                font-size: 1rem;
                letter-spacing: none;
            }
            .logo-icon {
                width: 24px;
                height: 24px;
                margin-right: 2px;
            }
            .site-header {
                height:50px
            }
            .menu-toggle-btn, .menu-close-btn {
                font-size: 1em;
            }
        }

        
        @media (max-width: 400px) {
            .site-header, .overlay-header {
                flex-direction: column;
                align-items: center;
                padding: 1rem;
            }
            .header-left, .header-right {
                width: 100%;
                text-align: center;
            }
            .header-center {
                margin-top: 1rem;
            }
            .menu-toggle-btn, .menu-close-btn {
                font-size: .8em;
            }
        }
    </style>
</head>
<body>

    <!-- Site Header -->
    <header class="site-header">
        <div class="header-left">
             <a href="{{ url_for('artwork.home') }}" class="site-logo">
            <img src="{{ url_for('static', filename='icons/svg/light/palette-light.svg') }}" alt="" class="logo-icon">DreameArtMachine</a>
        </div>
        <div class="header-center">
            <button id="menu-toggle" class="menu-toggle-btn" aria-label="Open menu">
                Menu
                <!-- Arrow Down Icon -->
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" /></svg>
            </button>
        </div>
        <div class="header-right">
            <button id="theme-toggle" class="theme-toggle-btn" aria-label="Toggle theme">
                <!-- Sun Icon -->
                <svg class="sun-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.106a.75.75 0 011.06-1.06l1.591 1.59a.75.75 0 01-1.06 1.06l-1.59-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.894 17.894a.75.75 0 01-1.06 1.06l-1.59-1.591a.75.75 0 111.06-1.06l1.59 1.59zM12 18.75a.75.75 0 01-.75.75v2.25a.75.75 0 011.5 0V19.5a.75.75 0 01-.75-.75zM6.106 18.894a.75.75 0 01-1.06-1.06l1.59-1.59a.75.75 0 011.06 1.06l-1.59 1.59zM3.75 12a.75.75 0 01.75-.75h2.25a.75.75 0 010 1.5H4.5a.75.75 0 01-.75-.75zM6.106 5.046a.75.75 0 011.06 1.06l-1.59 1.591a.75.75 0 01-1.06-1.06l1.59-1.59z"></path></svg>
                <!-- Moon Icon -->
                <svg class="moon-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69a.75.75 0 01.981.981A10.503 10.503 0 0118 18a10.5 10.5 0 01-10.5-10.5c0-1.25.22-2.454.622-3.574a.75.75 0 01.806-.162z" clip-rule="evenodd"></path></svg>
            </button>
        </div>
    </header>

    <!-- Overlay Menu -->
    <div id="overlay-menu" class="overlay-menu">
    <div class="overlay-header">
        <div class="header-left">
             <a href="{{ url_for('artwork.home') }}" class="site-logo">
            <img src="{{ url_for('static', filename='icons/svg/light/palette-light.svg') }}" alt="" class="logo-icon">DreamArtMachine</a>
        </div>
        <div class="header-center">
            <button id="menu-close" class="menu-close-btn" aria-label="Close menu">
                Close
                <!-- Arrow Up Icon -->
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M14.78 11.78a.75.75 0 0 1-1.06 0L10 8.06l-3.72 3.72a.75.75 0 1 1-1.06-1.06l4.25-4.25a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06Z" clip-rule="evenodd" /></svg>
            </button>
        </div>
        <div class="header-right">
            <!-- This empty div balances the flexbox layout -->
        </div>
    </div>
    <nav class="overlay-nav">
        <div class="nav-column">
            <h3>Artwork & Gallery</h3>
            <ul>
                <li><a href="/upload.html">Upload Artwork</a></li>
                <li><a href="/artworks.html">All Artworks</a></li>
                <li><a href="/gallery.html">Gallery</a></li>
                <li><a href="/finalised.html">Finalised</a></li>
                <li><a href="/locked.html">Locked</a></li>
                <li><a href="/edit_listing.html">Edit Listing</a></li>
            </ul>
        </div>
        <div class="nav-column">
            <h3>Workflow & Tools</h3>
            <ul>
                <li><a href="/composites_preview.html">Composites Preview</a></li>
                <li><a href="/review.html">Review Listing</a></li>
                <li><a href="/mockup_selector.html">Mockup Selector</a></li>
                <li><a href="/test_description.html">Test Description</a></li>
                <li><a href="/upload_results.html">Upload Results</a></li>
                <li><a href="/main.html">Main (Home)</a></li>
            </ul>
        </div>
        <div class="nav-column">
            <h3>Exports & Admin</h3>
            <ul>
                <li><a href="/sellbrite_exports.html">Sellbrite Exports</a></li>
                <li><a href="/sellbrite_csv_preview.html">Sellbrite CSV Preview</a></li>
                <li><a href="/sellbrite_log.html">Sellbrite Log</a></li>
                <li><a href="/admin/dashboard.html">Admin Dashboard</a></li>
                <li><a href="/admin/security.html">Admin Security</a></li>
                <li><a href="/admin/users.html">Admin Users</a></li>
                <li><a href="/login.html">Login</a></li>
            </ul>
        </div>
    </nav>
</div>

    <!-- Main Content -->
    <main>
        <div class="home-content-grid">
            <!-- Placeholder art pieces -->
            <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>M_001 Travertine Chair</h2>
                    <p>by Monolith</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
            <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>Chunk Chair</h2>
                    <p>by Obscure Objects</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
            <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>M_001 Travertine Chair</h2>
                    <p>by Monolith</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
            <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>Chunk Chair</h2>
                    <p>by Obscure Objects</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
            <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>M_001 Travertine Chair</h2>
                    <p>by Monolith</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
            <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>Chunk Chair</h2>
                    <p>by Obscure Objects</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
            <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>M_001 Travertine Chair</h2>
                    <p>by Monolith</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
             <div class="art-piece">
                <div class="art-piece-info">
                    <img src="https://placehold.co/600x800/f0f0f0/ccc?text=Artwork" alt="Placeholder for an art piece" onerror="this.onerror=null;this.src='https://placehold.co/600x800/f0f0f0/ccc?text=Image+Not+Found';">
                    <h2>Mirror Lounge Chair</h2>
                    <p>by Project 213A</p>
                </div>
                <div class="art-actions">
                    <button class="btn-action btn-analyse">Analyse</button>
                    <button class="btn-action btn-delete">Delete</button>

                    <button class="btn-action btn-gemini" data-action="create-social-post">✨ Create Social Post</button>
                </div>
            </div>
        </div>
    </main>
    
    <!-- Gemini Modal -->
    <div id="gemini-modal" class="gemini-modal">
        <div class="gemini-modal-content">
            <span class="gemini-modal-close">&times;</span>
            <h3 id="gemini-modal-title">AI Generation</h3>
            <div id="gemini-modal-body" class="gemini-modal-body">
                <!-- Content will be injected here -->
            </div>
             <div class="gemini-modal-actions">
                <button id="gemini-copy-btn" class="btn-action">Copy</button>
            </div>
        </div>
    </div>


    <!-- Footer -->
    <footer class="site-footer">
    <div class="footer-grid">
        <div class="footer-column">
            <h4>Navigate</h4>
            <ul>
                <li><a href="/index.html">Home</a></li>
                <li><a href="/about.html">About</a></li>
                <li><a href="/contact.html">Contact</a></li>
                <li><a href="/login.html">Login</a></li>
            </ul>
        </div>
        <div class="footer-column">
            <h4>Artwork & Gallery</h4>
            <ul>
                <li><a href="/upload.html">Upload Artwork</a></li>
                <li><a href="/artworks.html">Artworks</a></li>
                <li><a href="/edit_listing.html">Edit Listing</a></li>
                <li><a href="/finalised.html">Finalised</a></li>
                <li><a href="/gallery.html">Gallery</a></li>
                <li><a href="/locked.html">Locked</a></li>
            </ul>
        </div>
        <div class="footer-column">
            <h4>Workflow & Tools</h4>
            <ul>
                <li><a href="/composites_preview.html">Composites Preview</a></li>
                <li><a href="/review.html">Review</a></li>
                <li><a href="/mockup_selector.html">Mockups</a></li>
                <li><a href="/test_description.html">Test Description</a></li>
                <li><a href="/upload_results.html">Upload Results</a></li>
            </ul>
        </div>
        <div class="footer-column">
            <h4>Exports & Admin</h4>
            <ul>
                <li><a href="/sellbrite_exports.html">Sellbrite Exports</a></li>
                <li><a href="/sellbrite_csv_preview.html">Sellbrite CSV Preview</a></li>
                <li><a href="/sellbrite_log.html">Sellbrite Log</a></li>
                <li><a href="/admin/dashboard.html">Admin Dashboard</a></li>
                <li><a href="/admin/security.html">Admin Security</a></li>
                <li><a href="/admin/users.html">Admin Users</a></li>
            </ul>
        </div>
    </div>
    <div class="copyright-bar">
        © Copyright 2025 ART Narrator All rights reserved | <a href="https://DreamArtMachine.com">DreamArtMachine.com</a> designed and built by Robin Custance.
    </div>
</footer>


    <!-- JavaScript -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const menuToggle = document.getElementById('menu-toggle');
            const menuClose = document.getElementById('menu-close');
            const overlayMenu = document.getElementById('overlay-menu');
            const themeToggle = document.getElementById('theme-toggle');
            const body = document.body;

            // --- Menu Logic ---
            if (menuToggle && menuClose && overlayMenu) {
                menuToggle.addEventListener('click', () => {
                    overlayMenu.classList.add('is-active');
                    body.style.overflow = 'hidden';
                });

                menuClose.addEventListener('click', () => {
                    overlayMenu.classList.remove('is-active');
                    body.style.overflow = '';
                });
            }

            // --- Theme Logic ---
            const applyTheme = (theme) => {
                if (theme === 'dark') {
                    body.classList.add('dark-theme');
                } else {
                    body.classList.remove('dark-theme');
                }
            };

            const savedTheme = localStorage.getItem('theme');
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            
            if (savedTheme) {
                applyTheme(savedTheme);
            } else {
                applyTheme(prefersDark ? 'dark' : 'light');
            }

            if (themeToggle) {
                themeToggle.addEventListener('click', () => {
                    const currentTheme = body.classList.contains('dark-theme') ? 'dark' : 'light';
                    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                    applyTheme(newTheme);
                    localStorage.setItem('theme', newTheme);
                });
            }
            
            // --- Gemini Modal Logic ---
            const modal = document.getElementById('gemini-modal');
            const modalTitle = document.getElementById('gemini-modal-title');
            const modalBody = document.getElementById('gemini-modal-body');
            const closeBtn = document.querySelector('.gemini-modal-close');
            const copyBtn = document.getElementById('gemini-copy-btn');

            const defaultPrompts = {
                'generate-description': `Act as an expert art critic. Write an evocative and compelling gallery description for a piece of art titled "{ART_TITLE}". Focus on the potential materials, the mood it evokes, and the ideal setting for it. Make it about 150 words.`,
                'create-social-post': `Generate a short, engaging Instagram post to promote a piece of art titled "{ART_TITLE}". Include a catchy opening line, a brief description, and 3-5 relevant hashtags.`
            };

            closeBtn.onclick = () => {
                modal.style.display = "none";
            }
            window.onclick = (event) => {
                if (event.target == modal) {
                    modal.style.display = "none";
                }
            }

            document.querySelectorAll('.btn-gemini').forEach(button => {
                button.addEventListener('click', async (e) => {
                    const action = e.target.dataset.action;
                    const artPiece = e.target.closest('.art-piece');
                    const artTitle = artPiece.querySelector('h2').textContent;
                    
                    let promptTemplate = '';
                    let title = '';

                    if (action === 'generate-description') {
                        title = '✨ AI Art Description';
                        promptTemplate = localStorage.getItem('geminiDescriptionPrompt') || defaultPrompts[action];
                    } else if (action === 'create-social-post') {
                        title = '✨ AI Social Media Post';
                        promptTemplate = defaultPrompts[action]; // Using default for this one
                    }

                    const prompt = promptTemplate.replace('{ART_TITLE}', artTitle);

                    modalTitle.textContent = title;
                    modalBody.innerHTML = '<div class="loader"></div>';
                    modal.style.display = 'flex';

                    try {
                        let chatHistory = [{ role: "user", parts: [{ text: prompt }] }];
                        const payload = { contents: chatHistory };
                        const apiKey = ""; 
                        const apiUrl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + apiKey;
                        
                        const response = await fetch(apiUrl, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(payload)
                        });
                        
                        if (!response.ok) {
                             throw new Error("API error: " + response.status + " " + response.statusText);
                        }

                        const result = await response.json();
                        
                        if (result.candidates && result.candidates.length > 0 &&
                            result.candidates[0].content && result.candidates[0].content.parts &&
                            result.candidates[0].content.parts.length > 0) {
                            const text = result.candidates[0].content.parts[0].text;
                            modalBody.innerHTML = '<textarea id="gemini-result">' + text + '</textarea>';
                        } else {
                            throw new Error("Invalid response structure from API.");
                        }

                    } catch (error) {
                        console.error("Gemini API call failed:", error);
                        modalBody.innerHTML = '<p>Sorry, something went wrong. Please try again. (' + error.message + ')</p>';
                    }
                });
            });
            
            copyBtn.addEventListener('click', () => {
                const resultTextarea = document.getElementById('gemini-result');
                if (resultTextarea) {
                    resultTextarea.select();
                    document.execCommand('copy');
                    copyBtn.textContent = 'Copied!';
                    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 2000);
                }
            });

        });
    </script>

</body>
</html>


---
## templates/main.html
---
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script>
        const savedTheme = localStorage.getItem('theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = savedTheme || (prefersDark ? 'dark' : 'light');
        document.documentElement.classList.add('theme-' + theme);
    </script>
    <title>{% block title %}DreamArtMachine{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
    
</head>
<body data-analysis-status-url="" data-openai-ok="{{ 'true' if openai_configured else 'false' }}" data-google-ok="{{ 'true' if google_configured else 'false' }}">
    <header class="site-header header-grid">
        <div class="header-left">
            <a href="{{ url_for('home.home') }}" class="site-logo">
                <img src="{{ url_for('static', filename='icons/svg/light/palette-light.svg') }}" alt="" class="logo-icon icon">DreamArtMachine
            </a>
        </div>
        <div class="header-center">
            <button id="menu-toggle" class="menu-toggle-btn" aria-label="Open menu">
                Menu
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd"/></svg>
            </button>
        </div>
        <div class="header-right">
            <button id="theme-toggle" class="theme-toggle-btn" aria-label="Toggle theme">
                <svg class="sun-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.106a.75.75 0 011.06-1.06l1.591 1.59a.75.75 0 01-1.06 1.06l-1.59-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.894 17.894a.75.75 0 01-1.06 1.06l-1.59-1.591a.75.75 0 111.06-1.06l1.59 1.59zM12 18.75a.75.75 0 01-.75.75v2.25a.75.75 0 011.5 0V19.5a.75.75 0 01-.75-.75zM6.106 18.894a.75.75 0 01-1.06-1.06l1.59-1.59a.75.75 0 011.06 1.06l-1.59 1.59zM3.75 12a.75.75 0 01.75-.75h2.25a.75.75 0 010 1.5H4.5a.75.75 0 01-.75-.75zM6.106 5.046a.75.75 0 011.06 1.06l-1.59 1.591a.75.75 0 01-1.06-1.06l1.59-1.59z"/></svg>
                <svg class="moon-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69a.75.75 0 001.981.981A10.503 10.503 0 0118 18a10.5 10.5 0 01-10.5-10.5c0-1.25.22-2.454.622-3.574a.75.75 0 01.806-.162z" clip-rule="evenodd"/></svg>
            </button>
        </div>
    </header>

    <div id="overlay-menu" class="overlay-menu">
        <div class="overlay-header header-grid">
            <div class="header-left">
                <a href="{{ url_for('home.home') }}" class="site-logo">
                    <img src="{{ url_for('static', filename='icons/svg/light/palette-light.svg') }}" alt="" class="logo-icon icon">DreamArtMachine
                </a>
            </div>
            <div class="header-center">
                <button id="menu-close" class="menu-close-btn" aria-label="Close menu">
                    Close
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M14.78 11.78a.75.75 0 0 1-1.06 0L10 8.06l-3.72 3.72a.75.75 0 1 1-1.06-1.06l4.25-4.25a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06Z" clip-rule="evenodd"/></svg>
                </button>
            </div>
            <div class="header-right"></div>
        </div>
        <nav class="overlay-nav" role="navigation">
            <div class="nav-column">
                <h3>Artwork &amp; Gallery</h3>
                <ul>
                    <li><a href="{{ url_for('artwork.upload_artwork') }}">Upload Artwork</a></li>
                    <li><a href="{{ url_for('home.artworks') }}">All Artworks</a></li>
                    <li><a href="{{ url_for('home.finalised') }}">Finalised</a></li>
                    <li><a href="#">Locked</a></li>
                </ul>
            </div>
            <div class="nav-column">
                <h3>Workflow &amp; Tools</h3>
                <ul>
                    <li><a href="{{ '#' }}">Composites Preview</a></li>
                    <li><a href="{{ '#' }}">Mockup Admin</a></li>
                    <li><a href="{{ '#' }}">Coordinate Generator</a></li>
                    <li><a href="{{ '#' }}">Mockup Selector</a></li>
                </ul>
            </div>
            <div class="nav-column">
                <h3>Exports &amp; Admin</h3>
                <ul>
                    <li><a href="#">Sellbrite Management</a></li>
                    <li><a href="{{ url_for('admin.dashboard') }}">Admin Dashboard</a></li>
                    <li><a href="{{ url_for('admin.security_page') }}">Admin Security</a></li>
                    <li><a href="#">Description Editor (GDWS)</a></li>
                    <li><a href="{{ url_for('login') }}">Login</a></li>
                </ul>
            </div>
        </nav>
    </div>

    <main>
        <div class="container">
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="flash">
                        {% for m in messages %}{{ m }}{% endfor %}
                    </div>
                {% endif %}
            {% endwith %}
            {% block content %}{% endblock %}
        </div>
    </main>

    <div id="gemini-modal" class="modal-bg">
        <div class="modal-box">
            <button class="modal-close">&times;</button>
            <h3 id="gemini-modal-title">AI Generation</h3>
            <div id="gemini-modal-body" class="modal-status"></div>
            <div class="modal-actions">
                <button id="gemini-copy-btn" class="btn btn-secondary">Copy</button>
            </div>
        </div>
    </div>

    <div id="analysis-modal" class="modal-bg" role="dialog" aria-modal="true">
    <div class="modal-box" tabindex="-1">
        <button id="analysis-close" class="modal-close" aria-label="Close">&times;</button>
        <img src="{{ url_for('static', filename='icons/svg/light/arrows-clockwise-light.svg') }}" class="modal-icon spinning" alt="Processing...">
        <h3>Analyzing Artwork...</h3>
        <div class="modal-timer" id="analysis-timer">0s</div>
        <div id="analysis-status" class="modal-status" aria-live="polite">Starting...</div>
        <div class="modal-progress" aria-label="Analysis progress bar container">
        <div id="analysis-bar" class="modal-progress-bar" role="progressbar" aria-valuenow="0" aria-label="Analysis progress"></div>
        </div>
        <div class="modal-friendly-text">
        Grab a coffee while AI works its magic!<br>
        It usually only takes a minute or two!
        </div>
        <img src="{{ url_for('static', filename='icons/svg/light/coffee-light.svg') }}" class="coffee-icon icon" alt="Coffee break">
    </div>
    </div>

    <footer class="site-footer">
        <div class="footer-grid">
            <div class="footer-column">
                <h4>Navigate</h4>
                <ul>
                    <li><a href="{{ url_for('home.home') }}">Home</a></li>
                    <li><a href="{{ url_for('login') }}">Login</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Artwork &amp; Gallery</h4>
                <ul>
                    <li><a href="{{ url_for('artwork.upload_artwork') }}">Upload Artwork</a></li>
                    <li><a href="{{ url_for('home.artworks') }}">Artworks</a></li>
                    <li><a href="{{ url_for('home.finalised') }}">Finalised</a></li>
                    <li><a href="#">Locked</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Workflow &amp; Tools</h4>
                <ul>
                    <li><a href="{{ '#' }}">Composites Preview</a></li>
                    <li><a href="{{ '#' }}">Mockups</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Exports &amp; Admin</h4>
                <ul>
                    <li><a href="#">Sellbrite Management</a></li>
                    <li><a href="{{ url_for('admin.dashboard') }}">Admin Dashboard</a></li>
                    <li><a href="{{ url_for('admin.security_page') }}">Admin Security</a></li>
                    <li><a href="#">Description Editor (GDWS)</a></li>
                </ul>
                {# Removed broken menu link: Admin Users (no such route exists) #}
            </div>
        </div>
        <div class="copyright-bar">
            © Copyright 2025 ART Narrator All rights reserved | <a href="https://dreamartmachine.com">DreamArtMachine.com</a> designed and built by Robin Custance.
        </div>
    </footer>

    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    <script src="{{ url_for('static', filename='js/analysis-modal.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>

---
## templates/review_artwork.html
---
{% extends "main.html" %}
{% block title %}Edit Listing: {{ slug }}{% endblock %}
{% block content %}
<h1>Edit Listing: {{ slug }}</h1>
<p class="page-description">Update artwork details and regenerate mockups before finalising.</p>
<section class="main-content">
  <img src="{{ url_for('static', filename='finalised-artwork/' ~ slug ~ '/' ~ slug ~ '.jpg') }}" alt="{{ slug }}" class="review-main-img">
  <form method="post" action="{{ url_for('finalise.finalise', slug=slug) }}">
    <label for="title-input">Title</label>
    <input type="text" id="title-input" name="title" value="{{ title }}" required>
    <label for="description-input">Description</label>
    <textarea id="description-input" name="description" rows="5" required>{{ description }}</textarea>
    <label for="primary-colour">Primary Colour</label>
    <select id="primary-colour" name="primary_colour" required>
      {% for colour in colours %}
      <option value="{{ colour }}" {% if colour == primary_colour %}selected{% endif %}>{{ colour }}</option>
      {% endfor %}
    </select>
    <label for="secondary-colour">Secondary Colour</label>
    <select id="secondary-colour" name="secondary_colour" required>
      {% for colour in colours %}
      <option value="{{ colour }}" {% if colour == secondary_colour %}selected{% endif %}>{{ colour }}</option>
      {% endfor %}
    </select>
    <div class="mockups">
      {% for i in range(1, 10) %}
      <img src="{{ url_for('static', filename='finalised-artwork/' ~ slug ~ '/' ~ slug ~ '-MU-' ~ '%02d'|format(i) ~ '.jpg') }}" alt="Mockup {{ i }}">
      {% endfor %}
    </div>
    <button type="submit" name="action" value="finalise" class="btn btn-primary">Finalise Listing</button>
    <button type="submit" name="action" value="regenerate" class="btn btn-secondary">Regenerate Mockups</button>
  </form>
</section>
{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/edit_listing.js') }}"></script>
{% endblock %}


---
## templates/upload.html
---
{% extends "main.html" %}
{% block title %}Upload Artwork{% endblock %}
{% block content %}
<h1><img src="{{ url_for('static', filename='icons/svg/light/number-circle-one-light.svg') }}" class="hero-step-icon" alt="Step 1: Upload" />Upload New Artwork</h1>
<p class="page-description">Add images to start the creative workflow.</p>
<section class="main-content">
  <form id="upload-form" method="post" enctype="multipart/form-data">
    <input id="file-input" type="file" name="file" accept="image/*" multiple hidden>
    <div id="dropzone" class="upload-dropzone">
      Drag & Drop images here or click to choose files
    </div>
    <ul id="upload-list" class="upload-list"></ul>
  </form>
</section>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    <ul class="flash-messages">
      {% for category, msg in messages %}
        <li class="flash {{ category }}">{{ msg }}</li>
      {% endfor %}
    </ul>
  {% endif %}
{% endwith %}

<div id="upload-modal" class="modal-bg" role="dialog" aria-modal="true">
  <div class="modal-box" tabindex="-1">
    <img src="{{ url_for('static', filename='icons/svg/light/arrows-clockwise-light.svg') }}" class="modal-icon spinning" alt="Uploading...">
    <h3>Uploading...</h3>
    <div id="upload-filename" class="modal-status"></div>
    <div class="modal-progress" aria-label="upload progress">
        <div id="upload-bar" class="modal-progress-bar" role="progressbar" aria-valuenow="0"></div>
    </div>
    <div id="upload-status" class="modal-friendly-text" aria-live="polite">0%</div>
  </div>
</div>

{% endblock %}
{% block scripts %}
<script src="{{ url_for('static', filename='js/upload.js') }}"></script>
{% endblock %}


---
## tests/app.py
---
import importlib.util
import pathlib
import sys

# Load the actual application module from project root
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
spec = importlib.util.spec_from_file_location("real_app", ROOT / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Re-export selected attributes for tests
create_app = module.create_app
login_manager = module.login_manager
User = module.User
USERS = module.USERS


---
## tests/test_analyze_route.py
---
import importlib.util
import shutil
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
import config

spec = importlib.util.spec_from_file_location("real_app", ROOT / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
create_app = module.create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def login(client):
    return client.post("/login", data={"username": "robbie", "password": "Kanga123!"})


def _create_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (10, 10), color="white")
    img.save(path)


def test_analyze_route_smoke(client):
    login(client)
    slug = "test-art"
    filename = f"{slug}-ANALYSE.jpg"
    rel_path = Path(slug) / filename
    _create_image(config.UNANALYSED_ARTWORK_DIR / rel_path)

    resp = client.post(
        f"/analyze/square/{rel_path}",
        data={"provider": "openai"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "redirect_url" in data

    processed_img = config.PROCESSED_ARTWORK_DIR / slug / f"{slug}.jpg"
    assert processed_img.exists()

    shutil.rmtree(config.PROCESSED_ARTWORK_DIR / slug, ignore_errors=True)
    shutil.rmtree(config.UNANALYSED_ARTWORK_DIR / slug, ignore_errors=True)


---
## tests/test_homepage.py
---
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def login(client):
    return client.post("/login", data={"username": "robbie", "password": "Kanga123!"})


def test_home_requires_login(client):
    resp = client.get("/home")
    assert resp.status_code in (302, 401)
    assert "/login" in resp.headers.get("Location", "")


def test_root_redirects_to_home(client):
    login(client)
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/home")


def test_homepage_content(client):
    login(client)
    resp = client.get("/home")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "home-hero" in html
    assert "workflow-row" in html
    assert "site-footer" in html


---
## tests/test_image_config.py
---
"""Tests for Pillow configuration used to handle large images."""

from __future__ import annotations

import logging

from PIL import Image

import init.image_config as image_config


def test_large_image_logging(tmp_path, caplog):
    """Image.open is patched and logs when threshold is exceeded."""
    assert Image.MAX_IMAGE_PIXELS is None

    image_file = tmp_path / "tiny.png"
    Image.new("RGB", (10, 10)).save(image_file)

    image_config._LARGE_IMAGE_THRESHOLD = 50
    with caplog.at_level(logging.WARNING):
        Image.open(image_file)
    assert "Large image loaded" in caplog.text


---
## tests/test_pip_outdated.py
---
import json
import subprocess


def test_pip_outdated_runs():
    result = subprocess.run(
        ["pip", "list", "--outdated", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert isinstance(data, list)


---
## tests/test_restore_integrity.py
---
from pathlib import Path
import sys

# Add project root to import path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import validate

def test_full_integrity_passes(tmp_path):
    """
    Simulates a complete and valid project structure and asserts no errors are found.
    """
    # --- Setup a valid structure ---
    root = tmp_path
    (root / ".env").write_text("TEST=1")

    # Unanalysed section
    unanalysed = root / "art-processing" / "unanalysed-artwork" / "img"
    unanalysed.mkdir(parents=True)
    sku1 = "RJC-00001"
    (unanalysed / "img.jpg").write_text("x")
    (unanalysed / f"{sku1}-THUMB.jpg").write_text("x")
    (unanalysed / f"{sku1}-ANALYSE.jpg").write_text("x")
    (unanalysed / f"{sku1}-QC.json").write_text("{}")

    # Processed section
    processed = root / "art-processing" / "processed-artwork" / "slug"
    thumbs = processed / "THUMBS"
    thumbs.mkdir(parents=True)
    sku2 = "RJC-12345"
    slug = processed.name
    (processed / f"{slug}-{sku2}.jpg").write_text("x")
    (processed / f"{slug}-{sku2}-THUMB.jpg").write_text("x")
    (processed / f"{slug}-{sku2}-ANALYSE.jpg").write_text("x")
    (processed / f"{sku2}-QC.json").write_text("{}")
    (processed / f"{sku2}-FINAL.json").write_text("{}")
    for i in range(1, 10):
        (processed / f"{slug}-{sku2}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku2}-MU-{i:02}-THUMB.jpg").write_text("mu")

    # --- Run Validation ---
    errors = validate(root)

    # --- Assert ---
    assert not errors, f"Validation failed with errors: {errors}"

---
## tests/test_security_layer.py
---
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_login_required_on_artworks(client):
    response = client.get("/artworks")
    assert response.status_code in (302, 401)


def test_login_page_accessible(client):
    assert client.get("/login").status_code == 200


---
## tests/test_validate_sku_integrity.py
---
from pathlib import Path
import sys
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import check_unanalysed, check_processed


def test_missing_thumb(tmp_path):
    root = tmp_path / "unanalysed-artwork" / "image"
    root.mkdir(parents=True)
    sku = "RJC-00001"
    (root / "image.jpg").write_text("data")
    (root / f"{sku}-ANALYSE.jpg").write_text("data")
    (root / f"{sku}-QC.json").write_text("{}")
    errors = check_unanalysed(tmp_path / "unanalysed-artwork")
    assert any("THUMB" in e for e in errors)


def test_all_files_present(tmp_path):
    root = tmp_path / "unanalysed-artwork" / "image"
    root.mkdir(parents=True)
    sku = "RJC-00002"
    (root / "image.jpg").write_text("data")
    (root / f"{sku}-ANALYSE.jpg").write_text("data")
    (root / f"{sku}-THUMB.jpg").write_text("data")
    (root / f"{sku}-QC.json").write_text("{}")
    errors = check_unanalysed(tmp_path / "unanalysed-artwork")
    assert errors == []


def test_processed_missing_final_json(tmp_path):
    base = tmp_path / "processed-artwork" / "slug"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "RJC-12345"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{sku}-QC.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert any("Final JSON" in e for e in errors)


def test_processed_complete(tmp_path):
    base = tmp_path / "processed-artwork" / "slug2"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "R-56789"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{sku}-QC.json").write_text("{}")
    (base / f"{sku}-FINAL.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert errors == []
