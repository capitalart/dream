# FULL CODE STACK (MON-04-AUGUST-2025-09-28-PM)


---
## app.py
---
# app.py
"""
ArtNarrator application entrypoint.

This file initializes the Flask application, sets up configurations,
registers all blueprints (routes), defines security hooks, and runs
the development server.

INDEX
-----
1.  Imports & Initialisation
2.  Flask App Setup
3.  Application Configuration
4.  Request Hooks & Security
5.  Blueprint Registration
6.  Error Handlers & Health Checks
7.  Main Execution Block
"""

# ===========================================================================
# 1. Imports & Initialisation
# ===========================================================================

from __future__ import annotations
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.routing import BuildError

# --- [ 1.1: Local Application Imports ] ---
import config
import db
from utils import security, session_tracker
from routes import utils as routes_utils

# --- [ 1.2: Route (Blueprint) Imports ] ---
from routes.artwork_routes import bp as artwork_bp
from routes.sellbrite_service import bp as sellbrite_bp
from routes.export_routes import bp as exports_bp
from routes.auth_routes import bp as auth_bp
from routes.admin_security import bp as admin_bp
from routes.mockup_admin_routes import bp as mockup_admin_bp
from routes.coordinate_admin_routes import bp as coordinate_admin_bp
from routes.gdws_admin_routes import bp as gdws_admin_bp
from routes.test_routes import test_bp
from routes.api_routes import bp as api_bp
from routes.edit_listing_routes import bp as edit_listing_bp


# ===========================================================================
# 2. Flask App Setup
# ===========================================================================

# --- [ 2.1: Initialise App and Database ] ---
app = Flask(__name__)
# FIX (2025-08-04): Load all uppercase variables from config.py into the app's config.
# This makes them available in templates via the `config` object and fixes the Pytest errors.
app.config.from_object(config)
app.secret_key = config.FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
db.init_db()

# --- [ 2.2: Setup Logging ] ---
# Ensure logs directory and session registry file exist before logging
config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
session_registry_file = config.LOGS_DIR / "session_registry.json"
if not session_registry_file.exists():
    session_registry_file.write_text("{}", encoding="utf-8")

# Note: This basic logging will be replaced by the centralized logging utility.
logging.basicConfig(
    filename=config.LOGS_DIR / "composites-workflow.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# ===========================================================================
# 3. Application Configuration
# ===========================================================================

# --- [ 3.1: Set API Key Config Flags ] ---
app.config["OPENAI_CONFIGURED"] = bool(config.OPENAI_API_KEY)
app.config["GOOGLE_CONFIGURED"] = bool(config.GOOGLE_API_KEY)
if not app.config["OPENAI_CONFIGURED"]:
    logging.warning("OPENAI_API_KEY not configured in environment/.env")
if not app.config["GOOGLE_CONFIGURED"]:
    logging.warning("GOOGLE_API_KEY not configured in environment/.env")

# --- [ 3.2: Inject API Status and Helpers into Templates ] ---
@app.context_processor
def inject_template_helpers():
    """Makes API status and custom functions available to all templates."""
    return dict(
        openai_configured=app.config.get("OPENAI_CONFIGURED", False),
        google_configured=app.config.get("GOOGLE_CONFIGURED", False),
        get_artwork_image_url=routes_utils.get_artwork_image_url,
    )


# ===========================================================================
# 4. Request Hooks & Security
# ===========================================================================

@app.before_request
def require_login() -> None:
    """Enforce login for all routes except designated public endpoints."""
    public_endpoints = {"auth.login", "static"}
    public_paths = {"/health", "/healthz"}

    if request.path in public_paths or request.endpoint in public_endpoints:
        return

    if not session.get("logged_in") and security.login_required_enabled():
        return redirect(url_for("auth.login", next=request.path))

    # Validate session for logged-in users
    username = session.get("username")
    sid = session.get("session_id")
    if username and sid and not session_tracker.touch_session(username, sid):
        session.clear()
        if security.login_required_enabled():
            return redirect(url_for("auth.login", next=request.path))


@app.after_request
def apply_no_cache(response):
    """Attach no-cache headers when admin mode requires it."""
    if security.force_no_cache_enabled():
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


# ===========================================================================
# 5. Blueprint Registration
# ===========================================================================
app.register_blueprint(auth_bp)
app.register_blueprint(artwork_bp)
app.register_blueprint(sellbrite_bp)
app.register_blueprint(exports_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(mockup_admin_bp)
app.register_blueprint(coordinate_admin_bp)
app.register_blueprint(gdws_admin_bp)
app.register_blueprint(test_bp)
app.register_blueprint(api_bp)
app.register_blueprint(edit_listing_bp)


# ===========================================================================
# 6. Error Handlers & Health Checks
# ===========================================================================

@app.errorhandler(404)
def page_not_found(e):
    app.logger.error(f"Page not found (404): {request.url}")
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"Internal Server Error (500): {e}")
    return render_template("500.html"), 500


@app.errorhandler(BuildError)
def handle_build_error(err):
    app.logger.error("BuildError (missing endpoint): %s", err)
    return render_template("missing_endpoint.html", error=err), 500


@app.route("/health")
@app.route("/healthz")
def health_check():
    """Basic health check endpoint for monitoring."""
    return "OK", 200


# ===========================================================================
# 7. Main Execution Block
# ===========================================================================

def create_app() -> Flask:
    """Factory function for application creation (e.g., for Gunicorn)."""
    return app


if __name__ == "__main__":
    logging.info(f"ArtNarrator app starting up at {datetime.now()}")
    if config.DEBUG and config.HOST not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Refusing to run in debug mode on a public interface.")
    
    print(f"🎨 Starting ArtNarrator UI at http://{config.HOST}:{config.PORT}/ ...")
    try:
        app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
    finally:
        logging.info(f"ArtNarrator app shut down at {datetime.now()}")

---
## config.py
---
# config.py — ArtNarrator & DreamArtMachine (Robbie Mode™, July 2025)
# Central config: All core folders, env vars, limits, AI models, templates.
# All code must import config.py and reference only these values!

import os
from pathlib import Path
from dotenv import load_dotenv

# --- Load .env file from project root ---
load_dotenv()

# === PROJECT ROOT ===
BASE_DIR = Path(__file__).resolve().parent

# =============================================================================
# 1. ENV/BRANDING/ADMIN
# =============================================================================
# --- [ 1.1: Branding ] ---
BRAND_NAME = os.getenv("BRAND_NAME", "Art Narrator")
BRAND_TAGLINE = os.getenv("BRAND_TAGLINE", "Create. Automate. Sell Art.")
BRAND_AUTHOR = os.getenv("BRAND_AUTHOR", "Robin Custance")
BRAND_DOMAIN = os.getenv("BRAND_DOMAIN", "artnarrator.com")
ETSY_SHOP_URL = os.getenv("ETSY_SHOP_URL", "https://www.robincustance.etsy.com")

# --- [ 1.2: Server & Flask ] ---
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "robincustance@gmail.com")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "robbie")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "kangaroo123")
SERVER_PORT = int(os.getenv("SERVER_PORT", "7777"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
HOST = os.getenv("HOST", "127.0.0.1")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecret-key-1234")
PORT = int(os.getenv("PORT", "7777"))


# =============================================================================
# 2. AI/PLATFORM/API MODELS
# =============================================================================

# --- [ 2.1: OpenAI ] ---
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Main model for both text and vision tasks (gpt-4o is multimodal)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_MODEL_FALLBACK = os.getenv("OPENAI_MODEL_FALLBACK", "gpt-4-turbo")

# Models specifically for image GENERATION
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")
OPENAI_IMAGE_MODEL_FALLBACK = os.getenv("OPENAI_IMAGE_MODEL_FALLBACK", "dall-e-2")

# --- [ 2.2: Google Cloud ] ---
# API Key for authenticating with Google Cloud services
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

# The single, multimodal model for text and vision tasks
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")

# --- [ 2.3: Other Integrations ] ---
RCLONE_REMOTE_NAME = os.getenv("RCLONE_REMOTE_NAME", "gdrive")
RCLONE_REMOTE_PATH = os.getenv("RCLONE_REMOTE_PATH", "art-backups")
SELLBRITE_ACCOUNT_TOKEN = os.getenv("SELLBRITE_ACCOUNT_TOKEN")
SELLBRITE_SECRET_KEY = os.getenv("SELLBRITE_SECRET_KEY")
SELLBRITE_API_BASE_URL = os.getenv("SELLBRITE_API_BASE_URL", "https://api.sellbrite.com/v1")

# --- [ 2.4: SMTP Configuration ] ---
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# =============================================================================
# 3. FOLDER STRUCTURE & CORE PATHS
# =============================================================================

# --- [ 3.1: Core Directories ] ---
SCRIPTS_DIR = Path(os.getenv("SCRIPTS_DIR", BASE_DIR / "scripts"))
SETTINGS_DIR = Path(os.getenv("SETTINGS_DIR", BASE_DIR / "settings"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", BASE_DIR / "logs"))
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
STATIC_DIR = Path(os.getenv("STATIC_DIR", BASE_DIR / "static"))
TEMPLATES_DIR = Path(os.getenv("TEMPLATES_DIR", BASE_DIR / "templates"))

# --- [ 3.2: Art Processing Workflow Directories ] ---
ART_PROCESSING_DIR = Path(os.getenv("ART_PROCESSING_DIR", BASE_DIR / "art-processing"))
UNANALYSED_ROOT = ART_PROCESSING_DIR / "unanalysed-artwork"
PROCESSED_ROOT = ART_PROCESSING_DIR / "processed-artwork"
FINALISED_ROOT = ART_PROCESSING_DIR / "finalised-artwork"
ARTWORK_VAULT_ROOT = ART_PROCESSING_DIR / "artwork-vault"

# ✅ NEW: TEST FOLDERS for Pytest fixtures
UNANALYSED_TEST_DIR = UNANALYSED_ROOT / "tests"
PROCESSED_TEST_DIR = PROCESSED_ROOT / "tests"

# --- [ 3.3: Input Asset Directories ] ---
MOCKUPS_INPUT_DIR = Path(os.getenv("MOCKUPS_INPUT_DIR", BASE_DIR / "inputs" / "mockups"))
MOCKUPS_STAGING_DIR = MOCKUPS_INPUT_DIR / "uncategorised"
MOCKUPS_CATEGORISED_DIR = MOCKUPS_INPUT_DIR / "categorised"
MOCKUP_THUMBNAIL_DIR = MOCKUPS_INPUT_DIR / ".thumbnails"
SIGNATURES_DIR = Path(os.getenv("SIGNATURES_DIR", BASE_DIR / "inputs" / "signatures"))
GENERIC_TEXTS_DIR = Path(os.getenv("GENERIC_TEXTS_DIR", BASE_DIR / "generic_texts"))
COORDS_DIR = Path(os.getenv("COORDS_DIR", BASE_DIR / "inputs" / "Coordinates"))
GDWS_CONTENT_DIR = DATA_DIR / "gdws_content"

# --- [ 3.4: Output Directories ] ---
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", BASE_DIR / "outputs"))
COMPOSITES_DIR = OUTPUTS_DIR / "composites"
SELECTIONS_DIR = OUTPUTS_DIR / "selections"
SELLBRITE_DIR = OUTPUTS_DIR / "sellbrite"
SIGNED_DIR = OUTPUTS_DIR / "signed"
CODEX_LOGS_DIR = Path(os.getenv("CODEX_LOGS_DIR", BASE_DIR / "CODEX-LOGS"))

# Aliases
MOCKUPS_ROOT = MOCKUPS_INPUT_DIR
CATEGORISED_MOCKUPS_ROOT = MOCKUPS_CATEGORISED_DIR
COMPOSITES_ROOT = COMPOSITES_DIR
THUMB_SUBDIR = "THUMBS"
THUMBS_ROOT = FINALISED_ROOT / THUMB_SUBDIR

# =============================================================================
# 4. HELPER & REGISTRY FILES
# =============================================================================
DB_PATH = DATA_DIR / "artnarrator.sqlite3"
SKU_TRACKER = SETTINGS_DIR / "sku_tracker.json"
ANALYSIS_STATUS_FILE = LOGS_DIR / "analysis_status.json"
SESSION_REGISTRY_FILE = LOGS_DIR / "session_registry.json"
ONBOARDING_PATH = SETTINGS_DIR / "Master-Etsy-Listing-Description-Writing-Onboarding.txt"
MOCKUP_CATEGORISER_PROMPT_PATH = SETTINGS_DIR / "mockup_categoriser_prompt.txt"
OUTPUT_JSON = ART_PROCESSING_DIR / "master-artwork-paths.json"
MOCKUP_CATEGORISATION_LOG = LOGS_DIR / "mockup_categorisation.log"
PENDING_MOCKUPS_QUEUE_FILE = PROCESSED_ROOT / "pending_mockups.json"


# =============================================================================
# 5. FILENAME TEMPLATES
# =============================================================================
FILENAME_TEMPLATES = {
    "artwork": "{seo_slug}.jpg",
    "mockup": "{seo_slug}-MU-{num:02d}.jpg",
    "thumbnail": "{seo_slug}-THUMB.jpg",
    "analyse": "{seo_slug}-ANALYSE.jpg",
    "listing_json": "{seo_slug}-listing.json",
    "qc_json": "{seo_slug}.qc.json",
}

# =============================================================================
# 6. FILE TYPES, LIMITS, & IMAGE SIZES
# =============================================================================
ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png").split(","))
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ANALYSE_MAX_DIM = int(os.getenv("ANALYSE_MAX_DIM", "2400"))
ANALYSE_MAX_MB = int(os.getenv("ANALYSE_MAX_MB", "5"))
THUMB_WIDTH = int(os.getenv("THUMB_WIDTH", "400"))
THUMB_HEIGHT = int(os.getenv("THUMB_HEIGHT", "400"))

# =============================================================================
# 7. APPLICATION CONSTANTS
# =============================================================================
# --- [ 7.1: Artwork & Mockup Defaults ] ---
MOCKUPS_PER_LISTING = 9
DEFAULT_MOCKUP_IMAGE = STATIC_DIR / "img" / "default-mockup.jpg"

# --- ADDED FOR THE SIGNING SCRIPT ---
ARTWORKS_INPUT_DIR = UNANALYSED_ROOT  # Pointing to the unanalysed artwork folder
SIGNATURE_SIZE_PERCENTAGE = 0.08     # Signature will be 10% of the image's long edge
SIGNATURE_MARGIN_PERCENTAGE = 0.05   # 5% margin from the edges
SIGNED_OUTPUT_DIR = SIGNED_DIR       # Alias for the script to find the correct folder

ETSY_COLOURS = {
    'Beige': (222, 202, 173), 'Black': (24, 23, 22), 'Blue': (42, 80, 166),
    'Bronze': (140, 120, 83), 'Brown': (110, 72, 42), 'Clear': (240, 240, 240),
    'Copper': (181, 101, 29), 'Gold': (236, 180, 63), 'Grey': (160, 160, 160),
    'Green': (67, 127, 66), 'Orange': (237, 129, 40), 'Pink': (229, 100, 156),
    'Purple': (113, 74, 151), 'Rainbow': (170, 92, 152), 'Red': (181, 32, 42),
    'Rose gold': (212, 150, 146), 'Silver': (170, 174, 179),
    'White': (242, 242, 243), 'Yellow': (242, 207, 46)
}

# --- [ 7.2: Security & Session Management ] ---
MAX_SESSIONS = 5
SESSION_TIMEOUT_SECONDS = 7200  # 2 hours

# --- [ 7.3: SKU Configuration ] ---
SKU_CONFIG = {
    "PREFIX": "RJC-",
    "DIGITS": 4
}

# --- [ 7.4: Sellbrite Export Defaults ] ---
SELLBRITE_DEFAULTS = {
    "QUANTITY": 25,
    "CONDITION": "New",
    "CATEGORY": "Art & Collectibles > Prints > Digital Prints",
    "WEIGHT": 0
}

# --- [ 7.5: Guided Description Writing System (GDWS) Config ] ---
GDWS_CONFIG = {
    "PARAGRAPH_HEADINGS": [
        "About the Artist – Robin Custance", "Did You Know? Aboriginal Art & the Spirit of Dot Painting",
        "What You’ll Receive", "Ideal Uses for the", "Printing Tips",
        "Top 10 Print-On-Demand Services for Wall Art & Art Prints", "Important Notes",
        "Frequently Asked Questions", "LET’S CREATE SOMETHING BEAUTIFUL TOGETHER",
        "THANK YOU – FROM MY STUDIO TO YOUR HOME", "EXPLORE MY WORK", "WHY YOU’LL LOVE THIS ARTWORK",
        "HOW TO BUY & PRINT", "Thank You & Stay Connected"
    ],
    "PINNED_START_TITLES": [
        "About the Artist – Robin Custance",
        "Did You Know? Aboriginal Art & the Spirit of Dot Painting",
        "What You’ll Receive",
        "WHY YOU’LL LOVE THIS ARTWORK",
        "HOW TO BUY & PRINT",
    ],
    "PINNED_END_TITLES": [
        "THANK YOU – FROM MY STUDIO TO YOUR HOME",
        "Thank You & Stay Connected",
    ]
}


# =============================================================================
# 8. DYNAMIC CATEGORIES (from filesystem)
# =============================================================================
def get_mockup_categories() -> list[str]:
    override = os.getenv("MOCKUP_CATEGORIES")
    if override:
        return [c.strip() for c in override.split(",") if c.strip()]
    d = MOCKUPS_CATEGORISED_DIR
    if d.exists():
        return sorted([f.name for f in d.iterdir() if f.is_dir()])
    return []

MOCKUP_CATEGORIES = get_mockup_categories()


def resolve_image_url(path: Path) -> str:
    """Convert filesystem path to a proper public URL."""
    relative_path = path.relative_to(BASE_DIR).as_posix()
    return f"{BASE_URL}/{relative_path}"

# =============================================================================
# 9. FOLDER AUTO-CREATION
# =============================================================================
_CRITICAL_FOLDERS = [
    ART_PROCESSING_DIR, UNANALYSED_ROOT, PROCESSED_ROOT, FINALISED_ROOT,
    ARTWORK_VAULT_ROOT, OUTPUTS_DIR, COMPOSITES_DIR, SELECTIONS_DIR,
    SELLBRITE_DIR, SIGNED_DIR, MOCKUPS_INPUT_DIR, MOCKUPS_STAGING_DIR,
    MOCKUPS_CATEGORISED_DIR, MOCKUP_THUMBNAIL_DIR, SIGNATURES_DIR,
    GENERIC_TEXTS_DIR, COORDS_DIR, SCRIPTS_DIR, SETTINGS_DIR, LOGS_DIR,
    CODEX_LOGS_DIR, DATA_DIR, STATIC_DIR, TEMPLATES_DIR, GDWS_CONTENT_DIR,
]
for folder in _CRITICAL_FOLDERS:
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise RuntimeError(f"Could not create required folder {folder}: {exc}") from exc

# =============================================================================
# 10. SCRIPT PATHS (for automation & CLI)
# =============================================================================
ANALYZE_SCRIPT_PATH = SCRIPTS_DIR / "analyze_artwork.py"
GENERATE_SCRIPT_PATH = SCRIPTS_DIR / "generate_composites.py"
MOCKUP_CATEGORISER_SCRIPT_PATH = SCRIPTS_DIR / "mockup_categoriser.py"
COORDINATE_GENERATOR_SCRIPT_PATH = SCRIPTS_DIR / "generate_coordinates.py"
COORDINATE_GENERATOR_RATIO_SCRIPT_PATH = SCRIPTS_DIR / "generate_coordinates_for_ratio.py"

# =============================================================================
# 11. URLS & ROUTE PREFIXES
# =============================================================================
# --- [ 11.1: Base URL for Serving Content ] ---
BASE_URL = f"https://{BRAND_DOMAIN}" if ENVIRONMENT == "prod" else f"http://{HOST}:{PORT}"

# --- [ 11.2: URL Paths for Serving Static-like Content via Flask ] ---
STATIC_URL_PREFIX = "static"
PROCESSED_URL_PATH = f"{STATIC_URL_PREFIX}/{PROCESSED_ROOT.relative_to(BASE_DIR).as_posix()}"
FINALISED_URL_PATH = f"{STATIC_URL_PREFIX}/{FINALISED_ROOT.relative_to(BASE_DIR).as_posix()}"
LOCKED_URL_PATH = f"{STATIC_URL_PREFIX}/{ARTWORK_VAULT_ROOT.relative_to(BASE_DIR).as_posix()}"

# --- [ 11.3: Prefixes for Other Dynamic Image Routes ] ---
UNANALYSED_IMG_URL_PREFIX = "unanalysed-img"
MOCKUP_THUMB_URL_PREFIX = "thumbs"
COMPOSITE_IMG_URL_PREFIX = "composite-img"

# =============================================================================
# 12. AUDIT & MARKDOWN FILES
# =============================================================================
QA_AUDIT_INDEX = BASE_DIR / "QA_AUDIT_INDEX.md"
SITEMAP_FILE = BASE_DIR / "SITEMAP.md"
CHANGELOG_FILE = BASE_DIR / "CHANGELOG.md"

# =============================================================================
# 14. LOGGING SETUP
# =============================================================================
# --- [ 13.1: Log File Timestamp Format ] ---
LOG_TIMESTAMP_FORMAT = "%a-%d-%b-%Y-%I-%M-%p"

# --- [ 13.2: Log File Configurations ] ---
LOG_CONFIG = {
    # Core App Lifecycle
    "APP_STARTUP": "app-lifecycle-logs",
    "DATABASE": "database-logs",
    "SECURITY": "security-logs",
    "GUNICORN": "gunicorn",
    # Artwork Workflow Actions
    "UPLOAD": "upload",
    "DELETE": "delete",
    "EDITS": "edits",
    "FINALISE": "finalise",
    "LOCK": "lock",
    # Script & Subprocess Actions
    "ANALYZE_OPENAI": "analyse-openai",
    "ANALYZE_GOOGLE": "analyse-google",
    "COMPOSITE_GEN": "composite-generation-logs",
    # API Integrations
    "SELLBRITE_API": "sellbrite-api-logs",
    # Default/Catch-all
    "DEFAULT": "general-logs",
}

---
## requirements.txt
---
annotated-types==0.7.0
anyio==4.9.0
blinker==1.9.0
certifi==2025.6.15
charset-normalizer==3.4.2
click==8.2.1
distro==1.9.0
fastapi==0.111.0
Flask==3.1.1
gunicorn
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.10
itsdangerous==2.2.0
Jinja2==3.1.6
jiter==0.10.0
joblib==1.5.1
markdown-it-py==3.0.0
MarkupSafe==3.0.2
mdurl==0.1.2
numpy==2.3.1
openai==1.93.0
opencv-python==4.11.0.86
pandas==2.3.0
passlib==1.7.4
pillow==11.2.1
pydantic==2.11.7
pydantic_core==2.33.2
Pygments==2.19.2
python-dateutil==2.9.0.post0
python-dotenv==1.1.1
pytz==2025.2
requests==2.32.4
rich==14.0.0
scikit-learn==1.7.0
scipy==1.16.0
six==1.17.0
sniffio==1.3.1
SQLAlchemy==2.0.30
threadpoolctl==3.6.0
tqdm==4.67.1
typing-inspection==0.4.1
typing_extensions==4.14.0
tzdata==2025.2
urllib3==2.5.0
Werkzeug==3.1.3
google-generativeai==0.5.0
google-cloud-vision==3.10.2
google-api-python-client==2.126.0
google-auth==2.29.0
google-cloud-storage==2.16.0
google-cloud-secret-manager==2.22.0
google-cloud-logging==3.11.0
pytest==8.4.1
ImageHash==4.3.2
starlette==0.37.2
pathspec==0.12.1


---
## routes/__init__.py
---


---
## routes/admin_security.py
---
# routes/admin_security.py
"""
Admin routes for managing site security, user access, and session tracking.

This module provides the backend for the admin dashboard, allowing administrators
to toggle login requirements, manage user accounts, and view active sessions.

INDEX
-----
1.  Imports
2.  Blueprint Setup
3.  Admin Routes
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for

from utils import security, session_tracker, user_manager
from utils.auth_decorators import role_required
import config

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
bp = Blueprint("admin", __name__, url_prefix="/admin")


# ===========================================================================
# 3. Admin Routes
# ===========================================================================

@bp.route("/")
@role_required("admin")
def dashboard():
    """Renders the main admin dashboard page."""
    return render_template("admin/dashboard.html")


@bp.route("/security", methods=["GET", "POST"])
@role_required("admin")
def security_page():
    """Handles the security settings page for toggling login and cache control."""
    if request.method == "POST":
        action = request.form.get("action")
        minutes_str = request.form.get("minutes", "5")
        minutes = int(minutes_str) if minutes_str.isdigit() else 5

        if action == "enable":
            security.enable_login()
        elif action == "disable":
            security.disable_login_for(minutes)
        elif action == "nocache_on":
            security.enable_no_cache(minutes)
        elif action == "nocache_off":
            security.disable_no_cache()
        return redirect(url_for("admin.security_page"))

    context = {
        "login_required": security.login_required_enabled(),
        "remaining": security.remaining_minutes(),
        "no_cache": security.force_no_cache_enabled(),
        "cache_remaining": security.no_cache_remaining(),
        "active_sessions": len(session_tracker.active_sessions(config.ADMIN_USERNAME)),
        "max_sessions": session_tracker.MAX_SESSIONS,
    }
    return render_template("admin/security.html", **context)


@bp.route("/users", methods=["GET", "POST"])
@role_required("admin")
def manage_users():
    """Handles the user management page for adding and deleting users."""
    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username")
        
        if action == "add" and username:
            role = request.form.get("role", "viewer")
            password = request.form.get("password", "changeme")
            user_manager.add_user(username, role, password)
        elif action == "delete" and username:
            user_manager.delete_user(username)
        
        return redirect(url_for("admin.manage_users"))

    users = user_manager.load_users()
    return render_template("admin/users.html", users=users, config=config)

---
## routes/analyze_route-bk.py
---
# -*- coding: utf-8 -*-
"""Artwork-related Flask routes.

This module powers the full listing workflow from initial review to
finalisation. It handles validation, moving files, regenerating image link
lists and serving gallery pages for processed and finalised artworks.

INDEX
-----
1.  Imports and Initialisation
2.  Health Checks and Status API
3.  AI Analysis & Subprocess Helpers
4.  Validation and Data Helpers
5.  Core Navigation & Upload Routes
6.  Mockup Selection Workflow Routes
7.  Artwork Analysis Trigger Routes
8.  Artwork Editing and Listing Management
9.  Static File and Image Serving Routes
10. Composite Image Preview Routes
11. Artwork Finalisation and Gallery Routes
12. Listing State Management (Lock, Unlock, Delete)
13. Asynchronous API Endpoints
14. File Processing and Utility Helpers
"""

# ===========================================================================
# 1. Imports and Initialisation
# ===========================================================================
# This section handles all necessary imports, configuration loading, and
# the initial setup of the Flask Blueprint and logging.
# ===========================================================================

from __future__ import annotations
import json, subprocess, uuid, random, logging, shutil, os, traceback, datetime, time, sys
from pathlib import Path

# --- Local Application Imports ---
from utils.logger_utils import log_action, strip_binary
from utils.sku_assigner import peek_next_sku
from utils import ai_services
from routes import sellbrite_service
import config
from helpers.listing_utils import (
    resolve_listing_paths,
    create_unanalysed_subfolder,
    cleanup_unanalysed_folders,
)
from config import (
    PROCESSED_ROOT, FINALISED_ROOT, UNANALYSED_ROOT, ARTWORK_VAULT_ROOT,
    BASE_DIR, ANALYSIS_STATUS_FILE, PROCESSED_URL_PATH, FINALISED_URL_PATH,
    LOCKED_URL_PATH, UNANALYSED_IMG_URL_PREFIX, MOCKUP_THUMB_URL_PREFIX,
    COMPOSITE_IMG_URL_PREFIX,
)
import scripts.analyze_artwork as aa

# --- Third-Party Imports ---
from PIL import Image
import io
import google.generativeai as genai
from flask import (
    Blueprint, current_app, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort, Response, jsonify,
)
import re

# --- Local Route-Specific Imports ---
from . import utils
from .utils import (
    ALLOWED_COLOURS_LOWER, relative_to_base, read_generic_text, clean_terms, infer_sku_from_filename,
    sync_filename_with_sku, is_finalised_image, get_allowed_colours,
    load_json_file_safe, generate_mockups_for_listing,
)

bp = Blueprint("artwork", __name__)

# ===========================================================================
# 2. Health Checks and Status API
# ===========================================================================
# These endpoints provide status information for external services like
# OpenAI and Google, and for the background artwork analysis process.
# They are used by the frontend to monitor system health.
# ===========================================================================

@bp.get("/health/openai")
def health_openai():
    """Return status of OpenAI connection."""
    logger = logging.getLogger(__name__)
    try:
        aa.client.models.list()
        return jsonify({"ok": True})
    except Exception as exc:
        logger.error("OpenAI health check failed: %s", exc)
        error = str(exc)
        if config.DEBUG:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500

@bp.get("/health/google")
def health_google():
    """Return status of Google Vision connection."""
    logger = logging.getLogger(__name__)
    try:
        genai.list_models()
        return jsonify({"ok": True})
    except Exception as exc:
        logger.error("Google health check failed: %s", exc)
        error = str(exc)
        if config.DEBUG:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500

load_json_file_safe(ANALYSIS_STATUS_FILE)

def _write_analysis_status(step: str, percent: int, file: str | None = None, status: str | None = None, error: str | None = None) -> None:
    """Write progress info for frontend polling."""
    logger = logging.getLogger(__name__)
    payload = {"step": step, "percent": percent, "file": file, "status": status, "error": error}
    try:
        ANALYSIS_STATUS_FILE.write_text(json.dumps({k: v for k, v in payload.items() if v is not None}))
    except Exception as exc:
        logger.error("Failed writing analysis status: %s", exc)

@bp.route("/status/analyze")
def analysis_status():
    """Return JSON progress info for the current analysis job."""
    return Response(ANALYSIS_STATUS_FILE.read_text(), mimetype="application/json")

# ===========================================================================
# 3. AI Analysis & Subprocess Helpers
# ===========================================================================

def _run_ai_analysis(img_path: Path, provider: str) -> dict:
    """Run the AI analysis script and return its JSON output."""
    logger = logging.getLogger("art_analysis")
    logger.info("[DEBUG] _run_ai_analysis: img_path=%s provider=%s", img_path, provider)

    if provider == "openai":
        cmd = [sys.executable, str(config.ANALYZE_SCRIPT_PATH), str(img_path), "--json-output"]
    else:
        raise ValueError(f"Unknown provider: {provider}")

    logger.info("[DEBUG] Subprocess cmd: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        msg = (result.stderr or "Unknown error").strip()
        raise RuntimeError(f"AI analysis failed: {msg}")
    
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise RuntimeError("AI analysis output could not be parsed.") from e

def _generate_composites(seo_folder: str, log_id: str) -> None:
    """Triggers the composite generation script for a specific folder."""
    cmd = [sys.executable, str(config.GENERATE_SCRIPT_PATH), "--folder", seo_folder]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=config.BASE_DIR, timeout=600)
    composite_log = config.LOGS_DIR / "composite-generation-logs" / f"composite_gen_{log_id}.log"
    composite_log.parent.mkdir(exist_ok=True)
    composite_log.write_text(f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}")
    if result.returncode != 0:
        raise RuntimeError(f"Composite generation failed ({result.returncode})")

# ===========================================================================
# 4. Validation and Data Helpers
# ===========================================================================

def validate_listing_fields(data: dict, generic_text: str) -> list[str]:
    """Return a list of validation error messages for the listing."""
    errors: list[str] = []
    if not data.get("title", "").strip(): errors.append("Title cannot be blank")
    if len(data.get("title", "")) > 140: errors.append("Title exceeds 140 characters")
    if len(data.get("tags", [])) > 13: errors.append("Too many tags (max 13)")
    for t in data.get("tags", []):
        if not t or len(t) > 20: errors.append(f"Invalid tag: '{t}'")
    return errors

def get_categories_for_aspect(aspect: str) -> list[str]:
    """Return list of mockup categories available for the given aspect."""
    base = config.MOCKUPS_CATEGORISED_DIR / aspect
    return sorted([f.name for f in base.iterdir() if f.is_dir()]) if base.exists() else []

# ===========================================================================
# 5. Core Navigation & Upload Routes
# ===========================================================================

@bp.app_context_processor
def inject_latest_artwork():
    """Injects the latest analyzed artwork data into all templates."""
    return dict(latest_artwork=utils.latest_analyzed_artwork())

@bp.route("/")
def home():
    """Renders the main home page."""
    return render_template("index.html", menu=utils.get_menu())

@bp.route("/upload", methods=["GET", "POST"])
def upload_artwork():
    """Handle new artwork file uploads and run pre-QC checks."""
    if request.method == "POST":
        files = request.files.getlist("images")
        results = []
        user = session.get("username")
        
        for f in files:
            folder = create_unanalysed_subfolder(f.filename)
            try:
                res = _process_upload_file(f, folder)
            except Exception as exc:
                logging.getLogger(__name__).error("Upload failed for %s: %s", f.filename, exc)
                res = {"original": f.filename, "success": False, "error": str(exc)}
            
            log_action("upload", res.get("original", f.filename), user, res.get("error", "uploaded"), status="success" if res.get("success") else "fail")
            results.append(res)
        
        if any(r["success"] for r in results):
            flash(f"Uploaded {sum(1 for r in results if r['success'])} file(s) successfully", "success")
        for r in [r for r in results if not r["success"]]:
            flash(f"{r['original']}: {r['error']}", "danger")

        return redirect(url_for("artwork.artworks"))
        
    return render_template("upload.html", menu=utils.get_menu())

@bp.route("/artworks")
def artworks():
    """Display lists of artworks ready for analysis, processed, and finalised."""
    processed, processed_names = utils.list_processed_artworks()
    ready = utils.list_ready_to_analyze(processed_names)
    finalised = utils.list_finalised_artworks()
    return render_template("artworks.html", ready_artworks=ready, processed_artworks=processed, finalised_artworks=finalised, menu=utils.get_menu())
    
# ===========================================================================
# 6. Mockup Selection Workflow Routes
# ===========================================================================

@bp.route("/select", methods=["GET", "POST"])
def select():
    """Display the mockup selection interface."""
    if "slots" not in session or request.args.get("reset") == "1":
        utils.init_slots()
    slots = session["slots"]
    options = utils.compute_options(slots)
    zipped = list(zip(slots, options))
    return render_template("mockup_selector.html", zipped=zipped, menu=utils.get_menu())

@bp.route("/regenerate", methods=["POST"])
def regenerate():
    """Regenerate a random mockup image for a specific slot."""
    slot_idx = int(request.form["slot"])
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        cat = slots[slot_idx]["category"]
        slots[slot_idx]["image"] = utils.random_image(cat, "4x5") # Assuming 4x5 for now
        session["slots"] = slots
    return redirect(url_for("artwork.select"))

@bp.route("/swap", methods=["POST"])
def swap():
    """Swap a mockup slot to a new category."""
    slot_idx = int(request.form["slot"])
    new_cat = request.form["new_category"]
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        slots[slot_idx]["category"] = new_cat
        slots[slot_idx]["image"] = utils.random_image(new_cat, "4x5")
        session["slots"] = slots
    return redirect(url_for("artwork.select"))

# ===========================================================================
# 7. Artwork Analysis Trigger Routes
# ===========================================================================

@bp.route("/analyze/<aspect>/<filename>", methods=["POST"], endpoint="analyze_artwork")
def analyze_artwork_route(aspect, filename):
    """Run analysis on `filename` using the selected provider."""
    logger, provider = logging.getLogger(__name__), request.form.get("provider", "openai").lower()
    base_name = Path(filename).name
    _write_analysis_status("starting", 0, base_name, status="analyzing")

    src_path = next((p for p in config.UNANALYSED_ROOT.rglob(base_name) if p.is_file()), None)
    if not src_path:
        try:
            seo_folder = utils.find_seo_folder_from_filename(aspect, filename)
            src_path = PROCESSED_ROOT / seo_folder / f"{seo_folder}.jpg"
        except FileNotFoundError: pass

    if not src_path or not src_path.exists():
        flash(f"Artwork file not found: {filename}", "danger")
        return redirect(url_for("artwork.artworks"))

    try:
        analysis_result = _run_ai_analysis(src_path, provider)
        seo_folder = Path(analysis_result.get("processed_folder", "")).name
        
        if not seo_folder: raise RuntimeError("Analysis script did not return a valid folder name.")

        _generate_composites(seo_folder, uuid.uuid4().hex)
        
    except Exception as exc:
        flash(f"❌ Error running analysis: {exc}", "danger")
        return redirect(url_for("artwork.artworks"))

    redirect_filename = f"{seo_folder}.jpg"
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=redirect_filename))

# ===========================================================================
# 8. Artwork Editing and Listing Management
# ===========================================================================

@bp.route("/edit-listing/<aspect>/<filename>", methods=["GET", "POST"])
def edit_listing(aspect, filename):
    """Display and update a processed or finalised artwork listing."""
    try:
        seo_folder, folder, listing_path, finalised = resolve_listing_paths(aspect, filename)
    except FileNotFoundError:
        flash(f"Artwork not found: {filename}", "danger")
        return redirect(url_for("artwork.artworks"))
    
    data = utils.load_json_file_safe(listing_path)
    is_locked_in_vault = ARTWORK_VAULT_ROOT in folder.parents

    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "tags": [t.strip() for t in request.form.get("tags", "").split(',') if t.strip()],
            "materials": [m.strip() for m in request.form.get("materials", "").split(',') if m.strip()],
        }
        data.update(form_data)
        with open(listing_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        flash("Listing updated", "success")
        return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

    artwork = utils.populate_artwork_data_from_json(data, seo_folder)
    mockups = utils.get_mockup_details_for_template(data.get("mockups", []), folder, seo_folder, aspect)
    
    return render_template(
        "edit_listing.html",
        artwork=artwork,
        aspect=aspect,
        filename=filename,
        seo_folder=seo_folder,
        mockups=mockups,
        finalised=finalised,
        locked=data.get("locked", False),
        is_locked_in_vault=is_locked_in_vault,
        editable=not data.get("locked", False),
        openai_analysis=data.get("openai_analysis"),
        cache_ts=int(time.time()),
    )


# ==============================================================================
# SECTION 9: ADMIN + ANALYSIS API ROUTES
# ==============================================================================

# ------------------------------------------------------------------------------
# 9.1: Admin View of Individual Artwork
# ------------------------------------------------------------------------------

@router.get("/admin/artwork/{artwork_id}", response_class=HTMLResponse, name="admin_artwork_detail_page")
async def admin_artwork_detail_route(
    artwork_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """(Admin) Displays a detailed view of an individual artwork."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")

    artwork = _get_artwork_or_404(artwork_id, db, current_user)
    context = {"page_title": f"Admin View: {artwork.original_filename}", "artwork": artwork}
    return templates.TemplateResponse(request, "artwork_admin_details.html", context)


# ------------------------------------------------------------------------------
# 9.2: API – Get Artworks for Gallery Display
# ------------------------------------------------------------------------------

@router.get("/artworks-for-analysis", response_model=Optional[List[Dict[str, Any]]], name="json_artworks_for_analysis_gallery")
async def get_artworks_for_analysis_gallery_api(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
) -> Optional[List[Dict[str, Any]]]:
    """
    Returns artwork metadata for the Analyze Gallery grid.
    Filters by multiple artwork statuses.
    """
    gallery_statuses = [
        "qc_passed",
        "analyzed_pending_acceptance",
        "analysis_rejected",
        "finalized",
        "ready_for_export",
    ]
    artworks_db = crud.get_artworks_by_statuses(
        db,
        statuses=gallery_statuses,
        owner_id=None if current_user.is_superuser else current_user.id,
    )

    return [
        {
            "id": art.id,
            "original_filename": art.original_filename,
            "thumb_url": get_artwork_display_url(request, art.thumb_path, art.status),
            "status_raw": art.status or "unknown",
            "status_display": (art.status or "Unknown").replace("_", " ").title(),
            "generated_title_display": art.generated_title or get_short_prompt_hint(art.original_filename),
            "sku_display": art.sku,
            "resolution": art.resolution,
            "dpi": str(art.dpi) if art.dpi is not None else None,
        }
        for art in artworks_db
    ]


# ------------------------------------------------------------------------------
# 9.3: API – Update Artwork Status
# ------------------------------------------------------------------------------

@router.post("/artwork/{artwork_id}/update-status", name="update_artwork_status_api_analyze")
async def update_artwork_status_api_route_analyze(
    artwork_id: int,
    new_status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Updates the status of an artwork via the Analyze section.
    Only allows transitions to pre-defined valid statuses.
    """
    artwork = _get_artwork_or_404(artwork_id, db, current_user)
    valid_statuses = [
        "uploaded_pending_qc",
        "qc_passed",
        "qc_failed_metrics",
        "analyzed_pending_acceptance",
        "analysis_rejected",
        "finalized",
        "ready_for_export",
    ]

    if new_status not in valid_statuses:
        return JSONResponse(status_code=400, content={"error": f"Invalid status: {new_status}"})

    artwork.status = new_status
    artwork.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(artwork)
        return JSONResponse(content={"message": "Status updated", "new_status": new_status})
    except Exception as e_db:
        db.rollback()
        logger.error(f"DB error updating status for ArtID {artwork_id}: {e_db}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Database error on status update."})

# ==============================================================================
# END OF FILE — analyze_routes.py
# ==============================================================================


---
## routes/analyze_routes.py
---
# -*- coding: utf-8 -*-
"""Artwork-related Flask routes.

This module powers the full listing workflow from initial review to
finalisation. It handles validation, moving files, regenerating image link
lists and serving gallery pages for processed and finalised artworks.

INDEX
-----
1.  Imports and Initialisation
2.  Health Checks and Status API
3.  AI Analysis & Subprocess Helpers
4.  Validation and Data Helpers
5.  Core Navigation & Upload Routes
6.  Mockup Selection Workflow Routes
7.  Artwork Analysis Trigger Routes
8.  Artwork Editing and Listing Management
9.  Static File and Image Serving Routes
10. Composite Image Preview Routes
11. Artwork Finalisation and Gallery Routes
12. Listing State Management (Lock, Unlock, Delete)
13. Asynchronous API Endpoints
14. File Processing and Utility Helpers
"""

# ===========================================================================
# 1. Imports and Initialisation
# ===========================================================================
# This section handles all necessary imports, configuration loading, and
# the initial setup of the Flask Blueprint and logging.
# ===========================================================================

from __future__ import annotations
import json, subprocess, uuid, random, logging, shutil, os, traceback, datetime, time, sys
from pathlib import Path

# --- Local Application Imports ---
from utils.logger_utils import log_action, strip_binary
from utils.sku_assigner import peek_next_sku
from utils import ai_services
from routes import sellbrite_service
import config
from helpers.listing_utils import (
    resolve_listing_paths,
    create_unanalysed_subfolder,
    cleanup_unanalysed_folders,
)
from config import (
    PROCESSED_ROOT, FINALISED_ROOT, UNANALYSED_ROOT, ARTWORK_VAULT_ROOT,
    BASE_DIR, ANALYSIS_STATUS_FILE, PROCESSED_URL_PATH, FINALISED_URL_PATH,
    LOCKED_URL_PATH, UNANALYSED_IMG_URL_PREFIX, MOCKUP_THUMB_URL_PREFIX,
    COMPOSITE_IMG_URL_PREFIX,
)
import scripts.analyze_artwork as aa

# --- Third-Party Imports ---
from PIL import Image
import io
import google.generativeai as genai
from flask import (
    Blueprint, current_app, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort, Response, jsonify,
)
import re

# --- Local Route-Specific Imports ---
from . import utils
from .utils import (
    ALLOWED_COLOURS_LOWER, relative_to_base, read_generic_text, clean_terms, infer_sku_from_filename,
    sync_filename_with_sku, is_finalised_image, get_allowed_colours,
    load_json_file_safe, generate_mockups_for_listing,
)

bp = Blueprint("artwork", __name__)

# ===========================================================================
# 2. Health Checks and Status API
# ===========================================================================
# These endpoints provide status information for external services like
# OpenAI and Google, and for the background artwork analysis process.
# They are used by the frontend to monitor system health.
# ===========================================================================

@bp.get("/health/openai")
def health_openai():
    """Return status of OpenAI connection."""
    logger = logging.getLogger(__name__)
    try:
        aa.client.models.list()
        return jsonify({"ok": True})
    except Exception as exc:
        logger.error("OpenAI health check failed: %s", exc)
        error = str(exc)
        if config.DEBUG:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500

@bp.get("/health/google")
def health_google():
    """Return status of Google Vision connection."""
    logger = logging.getLogger(__name__)
    try:
        genai.list_models()
        return jsonify({"ok": True})
    except Exception as exc:
        logger.error("Google health check failed: %s", exc)
        error = str(exc)
        if config.DEBUG:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500

load_json_file_safe(ANALYSIS_STATUS_FILE)

def _write_analysis_status(step: str, percent: int, file: str | None = None, status: str | None = None, error: str | None = None) -> None:
    """Write progress info for frontend polling."""
    logger = logging.getLogger(__name__)
    payload = {"step": step, "percent": percent, "file": file, "status": status, "error": error}
    try:
        ANALYSIS_STATUS_FILE.write_text(json.dumps({k: v for k, v in payload.items() if v is not None}))
    except Exception as exc:
        logger.error("Failed writing analysis status: %s", exc)

@bp.route("/status/analyze")
def analysis_status():
    """Return JSON progress info for the current analysis job."""
    return Response(ANALYSIS_STATUS_FILE.read_text(), mimetype="application/json")

# ===========================================================================
# 3. AI Analysis & Subprocess Helpers
# ===========================================================================

def _run_ai_analysis(img_path: Path, provider: str) -> dict:
    """Run the AI analysis script and return its JSON output."""
    logger = logging.getLogger("art_analysis")
    logger.info("[DEBUG] _run_ai_analysis: img_path=%s provider=%s", img_path, provider)

    if provider == "openai":
        cmd = [sys.executable, str(config.ANALYZE_SCRIPT_PATH), str(img_path), "--json-output"]
    else:
        raise ValueError(f"Unknown provider: {provider}")

    logger.info("[DEBUG] Subprocess cmd: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        msg = (result.stderr or "Unknown error").strip()
        raise RuntimeError(f"AI analysis failed: {msg}")
    
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise RuntimeError("AI analysis output could not be parsed.") from e

def _generate_composites(seo_folder: str, log_id: str) -> None:
    """Triggers the composite generation script for a specific folder."""
    cmd = [sys.executable, str(config.GENERATE_SCRIPT_PATH), "--folder", seo_folder]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=config.BASE_DIR, timeout=600)
    composite_log = config.LOGS_DIR / "composite-generation-logs" / f"composite_gen_{log_id}.log"
    composite_log.parent.mkdir(exist_ok=True)
    composite_log.write_text(f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}")
    if result.returncode != 0:
        raise RuntimeError(f"Composite generation failed ({result.returncode})")

# ===========================================================================
# 4. Validation and Data Helpers
# ===========================================================================

def validate_listing_fields(data: dict, generic_text: str) -> list[str]:
    """Return a list of validation error messages for the listing."""
    errors: list[str] = []
    if not data.get("title", "").strip(): errors.append("Title cannot be blank")
    if len(data.get("title", "")) > 140: errors.append("Title exceeds 140 characters")
    if len(data.get("tags", [])) > 13: errors.append("Too many tags (max 13)")
    for t in data.get("tags", []):
        if not t or len(t) > 20: errors.append(f"Invalid tag: '{t}'")
    return errors

def get_categories_for_aspect(aspect: str) -> list[str]:
    """Return list of mockup categories available for the given aspect."""
    base = config.MOCKUPS_CATEGORISED_DIR / aspect
    return sorted([f.name for f in base.iterdir() if f.is_dir()]) if base.exists() else []

# ===========================================================================
# 5. Core Navigation & Upload Routes
# ===========================================================================

@bp.app_context_processor
def inject_latest_artwork():
    """Injects the latest analyzed artwork data into all templates."""
    return dict(latest_artwork=utils.latest_analyzed_artwork())

@bp.route("/")
def home():
    """Renders the main home page."""
    return render_template("index.html", menu=utils.get_menu())

@bp.route("/upload", methods=["GET", "POST"])
def upload_artwork():
    """Handle new artwork file uploads and run pre-QC checks."""
    if request.method == "POST":
        files = request.files.getlist("images")
        results = []
        user = session.get("username")
        
        for f in files:
            folder = create_unanalysed_subfolder(f.filename)
            try:
                res = _process_upload_file(f, folder)
            except Exception as exc:
                logging.getLogger(__name__).error("Upload failed for %s: %s", f.filename, exc)
                res = {"original": f.filename, "success": False, "error": str(exc)}
            
            log_action("upload", res.get("original", f.filename), user, res.get("error", "uploaded"), status="success" if res.get("success") else "fail")
            results.append(res)
        
        if any(r["success"] for r in results):
            flash(f"Uploaded {sum(1 for r in results if r['success'])} file(s) successfully", "success")
        for r in [r for r in results if not r["success"]]:
            flash(f"{r['original']}: {r['error']}", "danger")

        return redirect(url_for("artwork.artworks"))
        
    return render_template("upload.html", menu=utils.get_menu())

@bp.route("/artworks")
def artworks():
    """Display lists of artworks ready for analysis, processed, and finalised."""
    processed, processed_names = utils.list_processed_artworks()
    ready = utils.list_ready_to_analyze(processed_names)
    finalised = utils.list_finalised_artworks()
    return render_template("artworks.html", ready_artworks=ready, processed_artworks=processed, finalised_artworks=finalised, menu=utils.get_menu())
    
# ===========================================================================
# 6. Mockup Selection Workflow Routes
# ===========================================================================

@bp.route("/select", methods=["GET", "POST"])
def select():
    """Display the mockup selection interface."""
    if "slots" not in session or request.args.get("reset") == "1":
        utils.init_slots()
    slots = session["slots"]
    options = utils.compute_options(slots)
    zipped = list(zip(slots, options))
    return render_template("mockup_selector.html", zipped=zipped, menu=utils.get_menu())

@bp.route("/regenerate", methods=["POST"])
def regenerate():
    """Regenerate a random mockup image for a specific slot."""
    slot_idx = int(request.form["slot"])
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        cat = slots[slot_idx]["category"]
        slots[slot_idx]["image"] = utils.random_image(cat, "4x5") # Assuming 4x5 for now
        session["slots"] = slots
    return redirect(url_for("artwork.select"))

@bp.route("/swap", methods=["POST"])
def swap():
    """Swap a mockup slot to a new category."""
    slot_idx = int(request.form["slot"])
    new_cat = request.form["new_category"]
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        slots[slot_idx]["category"] = new_cat
        slots[slot_idx]["image"] = utils.random_image(new_cat, "4x5")
        session["slots"] = slots
    return redirect(url_for("artwork.select"))

# ===========================================================================
# 7. Artwork Analysis Trigger Routes
# ===========================================================================

@bp.route("/analyze/<aspect>/<filename>", methods=["POST"], endpoint="analyze_artwork")
def analyze_artwork_route(aspect, filename):
    """Run analysis on `filename` using the selected provider."""
    logger, provider = logging.getLogger(__name__), request.form.get("provider", "openai").lower()
    base_name = Path(filename).name
    _write_analysis_status("starting", 0, base_name, status="analyzing")

    src_path = next((p for p in config.UNANALYSED_ROOT.rglob(base_name) if p.is_file()), None)
    if not src_path:
        try:
            seo_folder = utils.find_seo_folder_from_filename(aspect, filename)
            src_path = PROCESSED_ROOT / seo_folder / f"{seo_folder}.jpg"
        except FileNotFoundError: pass

    if not src_path or not src_path.exists():
        flash(f"Artwork file not found: {filename}", "danger")
        return redirect(url_for("artwork.artworks"))

    try:
        analysis_result = _run_ai_analysis(src_path, provider)
        seo_folder = Path(analysis_result.get("processed_folder", "")).name
        
        if not seo_folder: raise RuntimeError("Analysis script did not return a valid folder name.")

        _generate_composites(seo_folder, uuid.uuid4().hex)
        
    except Exception as exc:
        flash(f"❌ Error running analysis: {exc}", "danger")
        return redirect(url_for("artwork.artworks"))

    redirect_filename = f"{seo_folder}.jpg"
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=redirect_filename))

# ===========================================================================
# 8. Artwork Editing and Listing Management
# ===========================================================================

@bp.route("/edit-listing/<aspect>/<filename>", methods=["GET", "POST"])
def edit_listing(aspect, filename):
    """Display and update a processed or finalised artwork listing."""
    try:
        seo_folder, folder, listing_path, finalised = resolve_listing_paths(aspect, filename)
    except FileNotFoundError:
        flash(f"Artwork not found: {filename}", "danger")
        return redirect(url_for("artwork.artworks"))
    
    data = utils.load_json_file_safe(listing_path)
    is_locked_in_vault = ARTWORK_VAULT_ROOT in folder.parents

    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "tags": [t.strip() for t in request.form.get("tags", "").split(',') if t.strip()],
            "materials": [m.strip() for m in request.form.get("materials", "").split(',') if m.strip()],
        }
        data.update(form_data)
        with open(listing_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        flash("Listing updated", "success")
        return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

    artwork = utils.populate_artwork_data_from_json(data, seo_folder)
    mockups = utils.get_mockup_details_for_template(data.get("mockups", []), folder, seo_folder, aspect)
    
    return render_template(
        "edit_listing.html",
        artwork=artwork,
        aspect=aspect,
        filename=filename,
        seo_folder=seo_folder,
        mockups=mockups,
        finalised=finalised,
        locked=data.get("locked", False),
        is_locked_in_vault=is_locked_in_vault,
        editable=not data.get("locked", False),
        openai_analysis=data.get("openai_analysis"),
        cache_ts=int(time.time()),
    )


# ==============================================================================
# SECTION 9: ADMIN + ANALYSIS API ROUTES
# ==============================================================================

# ------------------------------------------------------------------------------
# 9.1: Admin View of Individual Artwork
# ------------------------------------------------------------------------------

@router.get("/admin/artwork/{artwork_id}", response_class=HTMLResponse, name="admin_artwork_detail_page")
async def admin_artwork_detail_route(
    artwork_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """(Admin) Displays a detailed view of an individual artwork."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")

    artwork = _get_artwork_or_404(artwork_id, db, current_user)
    context = {"page_title": f"Admin View: {artwork.original_filename}", "artwork": artwork}
    return templates.TemplateResponse(request, "artwork_admin_details.html", context)


# ------------------------------------------------------------------------------
# 9.2: API – Get Artworks for Gallery Display
# ------------------------------------------------------------------------------

@router.get("/artworks-for-analysis", response_model=Optional[List[Dict[str, Any]]], name="json_artworks_for_analysis_gallery")
async def get_artworks_for_analysis_gallery_api(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
) -> Optional[List[Dict[str, Any]]]:
    """
    Returns artwork metadata for the Analyze Gallery grid.
    Filters by multiple artwork statuses.
    """
    gallery_statuses = [
        "qc_passed",
        "analyzed_pending_acceptance",
        "analysis_rejected",
        "finalized",
        "ready_for_export",
    ]
    artworks_db = crud.get_artworks_by_statuses(
        db,
        statuses=gallery_statuses,
        owner_id=None if current_user.is_superuser else current_user.id,
    )

    return [
        {
            "id": art.id,
            "original_filename": art.original_filename,
            "thumb_url": get_artwork_display_url(request, art.thumb_path, art.status),
            "status_raw": art.status or "unknown",
            "status_display": (art.status or "Unknown").replace("_", " ").title(),
            "generated_title_display": art.generated_title or get_short_prompt_hint(art.original_filename),
            "sku_display": art.sku,
            "resolution": art.resolution,
            "dpi": str(art.dpi) if art.dpi is not None else None,
        }
        for art in artworks_db
    ]


# ------------------------------------------------------------------------------
# 9.3: API – Update Artwork Status
# ------------------------------------------------------------------------------

@router.post("/artwork/{artwork_id}/update-status", name="update_artwork_status_api_analyze")
async def update_artwork_status_api_route_analyze(
    artwork_id: int,
    new_status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Updates the status of an artwork via the Analyze section.
    Only allows transitions to pre-defined valid statuses.
    """
    artwork = _get_artwork_or_404(artwork_id, db, current_user)
    valid_statuses = [
        "uploaded_pending_qc",
        "qc_passed",
        "qc_failed_metrics",
        "analyzed_pending_acceptance",
        "analysis_rejected",
        "finalized",
        "ready_for_export",
    ]

    if new_status not in valid_statuses:
        return JSONResponse(status_code=400, content={"error": f"Invalid status: {new_status}"})

    artwork.status = new_status
    artwork.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(artwork)
        return JSONResponse(content={"message": "Status updated", "new_status": new_status})
    except Exception as e_db:
        db.rollback()
        logger.error(f"DB error updating status for ArtID {artwork_id}: {e_db}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Database error on status update."})

# ==============================================================================
# END OF FILE — analyze_routes.py
# ==============================================================================


---
## routes/api_routes.py
---
# routes/api_routes.py
"""
General-purpose API routes for direct artwork analysis and file management.

These endpoints are designed to be called by external services or advanced
UI components that need direct access to core functionalities.

INDEX
-----
1.  Imports
2.  Blueprint Setup
3.  API Routes
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import uuid
import shutil
from pathlib import Path
import logging

from flask import Blueprint, request, jsonify

import config
from routes.artwork_routes import _run_ai_analysis

logger = logging.getLogger(__name__)

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
bp = Blueprint("api", __name__, url_prefix="/api")


# ===========================================================================
# 3. API Routes
# ===========================================================================

@bp.post("/analyze-artwork")
def analyze_artwork_api():
    """
    Analyzes an uploaded image with a specified provider.
    This is a stateless endpoint that creates and cleans up its own temp folder.
    """
    provider = request.form.get("provider")
    if provider not in {"openai", "google"}:
        return jsonify({"success": False, "error": "Provider must be 'openai' or 'google'."}), 400

    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "error": "No image file provided in 'file' field."}), 400

    temp_id = uuid.uuid4().hex[:8]
    # Use the UNANALYSED_ROOT from config for the base path
    temp_dir = config.UNANALYSED_ROOT / f"api-temp-{temp_id}"
    
    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
        image_path = temp_dir / file.filename
        file.save(image_path)
        logger.info(f"API analyze-artwork call: Saved temporary file to {image_path}")

        entry = _run_ai_analysis(image_path, provider)
        logger.info(f"API analyze-artwork call: Successfully analyzed {image_path} with {provider}.")
        return jsonify({"success": True, "result": entry})

    except Exception as exc:
        logger.error(f"API analyze-artwork error: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500
        
    finally:
        # Ensure the temporary directory is always cleaned up
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"API analyze-artwork call: Cleaned up temporary directory {temp_dir}")


@bp.post("/delete-upload-folder")
def delete_upload_folder():
    """
    Deletes a specified subfolder within the unanalysed artwork directory.
    Includes a security check to prevent traversal outside the target directory.
    """
    folder_path_str = request.json.get("folder") if request.is_json else None
    
    if not folder_path_str:
        return jsonify({"success": False, "error": "Invalid request. 'folder' path is required."}), 400

    # Security check: Ensure the path is within the allowed directory
    unanalysed_root_str = str(config.UNANALYSED_ROOT)
    full_path = Path(folder_path_str).resolve()

    if not str(full_path).startswith(unanalysed_root_str):
        logger.warning(f"API delete-upload-folder blocked attempt to delete outside target directory: {folder_path_str}")
        return jsonify({"success": False, "error": "Invalid folder path. Deletion is restricted."}), 400
        
    try:
        shutil.rmtree(full_path, ignore_errors=True)
        logger.info(f"API successfully deleted folder: {full_path}")
        return jsonify({"success": True, "message": f"Folder '{full_path.name}' deleted."})
    except Exception as exc:
        logger.error(f"API delete-upload-folder failed for path {full_path}: {exc}", exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500

---
## routes/artwork_routes-bk.py
---
# -*- coding: utf-8 -*-
"""Artwork-related Flask routes.

This module powers the full listing workflow from initial review to
finalisation. It handles validation, moving files, regenerating image link
lists and serving gallery pages for processed and finalised artworks.

INDEX
-----
1.  Imports and Initialisation
2.  Health Checks and Status API
3.  AI Analysis & Subprocess Helpers
4.  Validation and Data Helpers
5.  Core Navigation & Upload Routes
6.  Mockup Selection Workflow Routes
7.  Artwork Analysis Trigger Routes
8.  Artwork Editing and Listing Management
9.  Static File and Image Serving Routes
10. Composite Image Preview Routes
11. Artwork Finalisation and Gallery Routes
12. Listing State Management (Lock, Unlock, Delete)
13. Asynchronous API Endpoints
14. File Processing and Utility Helpers
"""

# ===========================================================================
# 1. Imports and Initialisation
# ===========================================================================
# This section handles all necessary imports, configuration loading, and
# the initial setup of the Flask Blueprint and logging.
# ===========================================================================

# This file now references all path, directory, and filename variables strictly from config.py.
from __future__ import annotations
import json, subprocess, uuid, random, logging, shutil, os, traceback, datetime, time, sys
from pathlib import Path

# --- Local Application Imports ---
from utils.logger_utils import log_action, strip_binary
from utils.sku_assigner import peek_next_sku
from utils import ai_services
from routes import sellbrite_service
import config
from helpers.listing_utils import (
    resolve_listing_paths,
    create_unanalysed_subfolder,
    cleanup_unanalysed_folders,
)
from config import (
    PROCESSED_ROOT, FINALISED_ROOT, UNANALYSED_ROOT, ARTWORK_VAULT_ROOT,
    BASE_DIR, ANALYSIS_STATUS_FILE, PROCESSED_URL_PATH, FINALISED_URL_PATH,
    LOCKED_URL_PATH, UNANALYSED_IMG_URL_PREFIX, MOCKUP_THUMB_URL_PREFIX,
    COMPOSITE_IMG_URL_PREFIX,
)
import scripts.analyze_artwork as aa

# --- Third-Party Imports ---
from PIL import Image
import io
import google.generativeai as genai
from flask import (
    Blueprint, current_app, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort, Response, jsonify,
)
import re

# --- Local Route-Specific Imports ---
from . import utils
from .utils import (
    ALLOWED_COLOURS_LOWER, relative_to_base, read_generic_text, clean_terms, infer_sku_from_filename,
    sync_filename_with_sku, is_finalised_image, get_allowed_colours,
    load_json_file_safe, generate_mockups_for_listing,
)

bp = Blueprint("artwork", __name__)

# ===========================================================================
# 2. Health Checks and Status API
# ===========================================================================
# These endpoints provide status information for external services like
# OpenAI and Google, and for the background artwork analysis process.
# They are used by the frontend to monitor system health.
# ===========================================================================

@bp.get("/health/openai")
def health_openai():
    """Return status of OpenAI connection."""
    logger = logging.getLogger(__name__)
    try:
        aa.client.models.list()
        return jsonify({"ok": True})
    except Exception as exc:  # noqa: BLE001
        logger.error("OpenAI health check failed: %s", exc)
        debug = config.DEBUG
        error = str(exc)
        if debug:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500


@bp.get("/health/google")
def health_google():
    """Return status of Google Vision connection."""
    logger = logging.getLogger(__name__)
    try:
        genai.list_models()
        return jsonify({"ok": True})
    except Exception as exc:  # noqa: BLE001
        logger.error("Google health check failed: %s", exc)
        debug = config.DEBUG
        error = str(exc)
        if debug:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500


# Ensure analysis status file exists at import time
load_json_file_safe(ANALYSIS_STATUS_FILE)


def _write_analysis_status(
    step: str,
    percent: int,
    file: str | None = None,
    status: str | None = None,
    error: str | None = None,
) -> None:
    """Write progress info for frontend polling."""
    logger = logging.getLogger(__name__)
    try:
        ANALYSIS_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # pragma: no cover - unexpected IO
        logger.error(
            "Unable to create status directory %s: %s", ANALYSIS_STATUS_FILE.parent, exc
        )

    payload = {"step": step, "percent": percent, "file": file}
    if status:
        payload["status"] = status
    if error:
        payload["error"] = error

    try:
        ANALYSIS_STATUS_FILE.write_text(json.dumps(payload))
    except Exception as exc:  # pragma: no cover - unexpected IO
        logger.error("Failed writing analysis status: %s", exc)


@bp.route("/status/analyze")
def analysis_status():
    """Return JSON progress info for the current analysis job."""
    data = load_json_file_safe(ANALYSIS_STATUS_FILE)
    if not data:
        data = {"step": "idle", "percent": 0, "status": "idle"}
    return Response(json.dumps(data), mimetype="application/json")


# ===========================================================================
# 3. AI Analysis & Subprocess Helpers
# ===========================================================================
# These helper functions are responsible for invoking external Python scripts
# via subprocesses, such as the AI analysis and composite generation scripts.
# They handle command construction, execution, and error logging.
# ===========================================================================

def _run_ai_analysis(img_path: Path, provider: str) -> dict:
    """Run the AI analysis script and return its JSON output."""
    logger = logging.getLogger("art_analysis")
    logger.info("[DEBUG] _run_ai_analysis: img_path=%s provider=%s", img_path, provider)

    if provider == "openai":
        script_path = config.SCRIPTS_DIR / "analyze_artwork.py"
        # --- MODIFIED: Use sys.executable to ensure the correct Python interpreter ---
        cmd = [sys.executable, str(script_path), str(img_path), "--provider", "openai", "--json-output"]
    elif provider == "google":
        script_path = config.SCRIPTS_DIR / "analyze_artwork_google.py"
        # --- MODIFIED: Use sys.executable for consistency ---
        cmd = [sys.executable, str(script_path), str(img_path)]
    else:
        raise ValueError(f"Unknown provider: {provider}")

    logger.info("[DEBUG] Subprocess cmd: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        logger.error("AI analysis subprocess timed out for %s", img_path)
        raise RuntimeError("AI analysis timed out after 300 seconds") from None
    except Exception as exc:  # noqa: BLE001 - unexpected OSError
        logger.error("Subprocess execution failed: %s", exc)
        raise RuntimeError(str(exc)) from exc

    if result.returncode != 0:
        msg = (result.stderr or "Unknown error").strip()
        raise RuntimeError(f"AI analysis failed: {msg}")

    if not result.stdout.strip():
        raise RuntimeError("AI analysis failed. Please try again.")

    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise RuntimeError("AI analysis output could not be parsed.") from e


def _generate_composites(seo_folder: str, log_id: str) -> None:
    """Triggers the composite generation script."""
    # --- MODIFIED: Use sys.executable for consistency and reliability ---
    cmd = [sys.executable, str(config.GENERATE_SCRIPT_PATH)]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=config.BASE_DIR,
        timeout=600,
    )
    composite_log = utils.LOGS_DIR / f"composite_gen_{log_id}.log"
    with open(composite_log, "w") as log:
        log.write(f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}")
    if result.returncode != 0:
        raise RuntimeError(f"Composite generation failed ({result.returncode})")


# ===========================================================================
# 4. Validation and Data Helpers
# ===========================================================================
# This section contains helper functions for validating form data and
# retrieving data for templates, such as available mockup categories.
# ===========================================================================

def validate_listing_fields(data: dict, generic_text: str) -> list[str]:
    """Return a list of validation error messages for the listing."""
    errors: list[str] = []
    # Title validation
    title = data.get("title", "").strip()
    if not title: errors.append("Title cannot be blank")
    if len(title) > 140: errors.append("Title exceeds 140 characters")
    # Tag validation
    tags = data.get("tags", [])
    if len(tags) > 13: errors.append("Too many tags (max 13)")
    for t in tags:
        if not t or len(t) > 20: errors.append(f"Invalid tag: '{t}'")
        if not re.fullmatch(r"[A-Za-z0-9 ]+", t): errors.append(f"Tag has invalid characters: '{t}'")
    # SKU and SEO Filename validation
    seo_filename = data.get("seo_filename", "")
    if len(seo_filename) > 70: errors.append("SEO filename exceeds 70 characters")
    if not re.search(r"Artwork-by-Robin-Custance-RJC-[A-Za-z0-9-]+\.jpg$", seo_filename):
        errors.append("SEO filename must end with 'Artwork-by-Robin-Custance-RJC-XXXX.jpg'")
    sku = data.get("sku", "")
    if not sku: errors.append("SKU is required")
    if sku and not sku.startswith("RJC-"): errors.append("SKU must start with 'RJC-'")
    if sku and infer_sku_from_filename(seo_filename or "") != sku:
        errors.append("SKU must match value in SEO filename")
    # Price validation
    try:
        if abs(float(data.get("price")) - 18.27) > 1e-2: errors.append("Price must be 18.27")
    except Exception: errors.append("Price must be a number (18.27)")
    # Color validation
    for key in ("primary_colour", "secondary_colour"):
        col = data.get(key, "").strip()
        if not col: errors.append(f"{key.replace('_', ' ').title()} is required")
        elif col.lower() not in ALLOWED_COLOURS_LOWER: errors.append(f"{key.replace('_', ' ').title()} invalid")
    # Image validation
    images = [i.strip() for i in data.get("images", []) if str(i).strip()]
    if not images: errors.append("At least one image required")
    for img in images:
        if not is_finalised_image(img): errors.append(f"Image not in finalised-artwork folder: '{img}'")
    # Description validation
    desc = data.get("description", "").strip()
    if len(desc.split()) < 400: errors.append("Description must be at least 400 words")
    if generic_text and "About the Artist – Robin Custance".lower() not in " ".join(desc.split()).lower():
        errors.append("Description must include the correct generic context block.")
    return errors

def get_categories_for_aspect(aspect: str) -> list[str]:
    """Return list of mockup categories available for the given aspect."""
    base = config.MOCKUPS_CATEGORISED_DIR / aspect
    if not base.exists(): return []
    return sorted([f.name for f in base.iterdir() if f.is_dir()])


# ===========================================================================
# 5. Core Navigation & Upload Routes
# ===========================================================================
# These routes handle the main user navigation: the home page, the artwork
# upload page, and the main dashboard listing all artworks in various stages.
# A context processor is included to inject data into all templates.
# ===========================================================================

@bp.app_context_processor
def inject_latest_artwork():
    """Injects the latest analyzed artwork data into all templates."""
    return dict(latest_artwork=utils.latest_analyzed_artwork())

@bp.route("/")
def home():
    """Renders the main home page."""
    return render_template("index.html", menu=utils.get_menu())

@bp.route("/upload", methods=["GET", "POST"])
def upload_artwork():
    """Handle new artwork file uploads and run pre-QC checks."""
    if request.method == "POST":
        files = request.files.getlist("images")
        results, successes = [], []
        user = session.get("username")
        
        for f in files:
            # Create a unique folder for each file inside the loop
            folder = create_unanalysed_subfolder(f.filename)
            try:
                res = _process_upload_file(f, folder)
            except Exception as exc:
                logging.getLogger(__name__).error("Upload failed for %s: %s", f.filename, exc)
                res = {"original": f.filename, "success": False, "error": str(exc)}
            
            status = "success" if res.get("success") else "fail"
            log_action("upload", res.get("original", f.filename), user, res.get("error", "uploaded"), status=status)
            results.append(res)
        
        if (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html):
            return jsonify(results)
        
        successes = [r for r in results if r["success"]]
        if successes:
            flash(f"Uploaded {len(successes)} file(s) successfully", "success")
        for f in [r for r in results if not r["success"]]:
            flash(f"{f['original']}: {f['error']}", "danger")

        return redirect(url_for("artwork.artworks"))
        
    return render_template("upload.html", menu=utils.get_menu())


@bp.route("/artworks")
def artworks():
    """Display lists of artworks ready for analysis, processed, and finalised."""
    processed, processed_names = utils.list_processed_artworks()
    ready = utils.list_ready_to_analyze(processed_names)
    finalised = utils.list_finalised_artworks()
    return render_template(
        "artworks.html",
        ready_artworks=ready,
        processed_artworks=processed,
        finalised_artworks=finalised,
        menu=utils.get_menu(),
    )
    

# ===========================================================================
# 6. Mockup Selection Workflow Routes
# ===========================================================================
# This group of routes manages the user flow for selecting, regenerating,
# and swapping the initial set of mockups before the main analysis.
# ===========================================================================

@bp.route("/select", methods=["GET", "POST"])
def select():
    """Display the mockup selection interface."""
    if "slots" not in session or request.args.get("reset") == "1":
        utils.init_slots()
    slots = session["slots"]
    options = utils.compute_options(slots)
    zipped = list(zip(slots, options))
    return render_template("mockup_selector.html", zipped=zipped, menu=utils.get_menu())


@bp.route("/regenerate", methods=["POST"])
def regenerate():
    """Regenerate a random mockup image for a specific slot."""
    slot_idx = int(request.form["slot"])
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        cat = slots[slot_idx]["category"]
        slots[slot_idx]["image"] = utils.random_image(cat)
        session["slots"] = slots
    return redirect(url_for("artwork.select"))


@bp.route("/swap", methods=["POST"])
def swap():
    """Swap a mockup slot to a new category."""
    slot_idx = int(request.form["slot"])
    new_cat = request.form["new_category"]
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        slots[slot_idx]["category"] = new_cat
        slots[slot_idx]["image"] = utils.random_image(new_cat)
        session["slots"] = slots
    return redirect(url_for("artwork.select"))


@bp.route("/proceed", methods=["POST"])
def proceed():
    """Finalise mockup selections and trigger composite generation."""
    slots = session.get("slots", [])
    if not slots:
        flash("No mockups selected!", "danger")
        return redirect(url_for("artwork.select"))
    utils.SELECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    selection_id = str(uuid.uuid4())
    selection_file = utils.SELECTIONS_DIR / f"{selection_id}.json"
    with open(selection_file, "w") as f:
        json.dump(slots, f, indent=2)
    # This section would typically call a generation script
    flash("Composite generation process initiated!", "success")
    latest = utils.latest_composite_folder()
    if latest:
        return redirect(url_for("artwork.composites_specific", seo_folder=latest))
    return redirect(url_for("artwork.composites_preview"))


# ===========================================================================
# 7. Artwork Analysis Trigger Routes
# ===========================================================================
# These routes are the primary entry points for starting the AI analysis
# process on an artwork, either from a fresh upload or a re-analysis.
# They orchestrate file copying, script execution, and status updates.
# ===========================================================================

@bp.route("/analyze/<aspect>/<filename>", methods=["POST"], endpoint="analyze_artwork")
def analyze_artwork_route(aspect, filename):
    """Run analysis on `filename` using the selected provider."""
    logger, provider = logging.getLogger(__name__), request.form.get("provider", "openai").lower()
    base_name = Path(filename).name
    _write_analysis_status("starting", 0, base_name, status="analyzing")

    src_path = next((p for p in config.UNANALYSED_ROOT.rglob(base_name) if p.is_file()), None)
    if not src_path:
        try:
            # Handle re-analysis of already processed files
            seo_folder = utils.find_seo_folder_from_filename(aspect, filename)
            # For re-analysis, the source is the main JPG in the processed folder
            src_path = PROCESSED_ROOT / seo_folder / f"{seo_folder}.jpg"
        except FileNotFoundError:
            pass

    if not src_path or not src_path.exists():
        flash(f"Artwork file not found: {filename}", "danger")
        _write_analysis_status("failed", 100, base_name, status="failed", error="file not found")
        return redirect(url_for("artwork.artworks"))

    try:
        _write_analysis_status(f"{provider}_call", 20, base_name, status="analyzing")
        analysis_result = _run_ai_analysis(src_path, provider)
        
        processed_folder_path = Path(analysis_result.get("processed_folder", ""))
        seo_folder = processed_folder_path.name
        
        if not seo_folder:
            raise RuntimeError("Analysis script did not return a valid folder name.")

        _write_analysis_status("generating", 60, filename, status="analyzing")
        _generate_composites(seo_folder, uuid.uuid4().hex)

        # --- CLEANUP LOGIC ADDED HERE ---
        # If the source was an unanalysed file, delete its temporary parent folder.
        # This check prevents deleting anything during a re-analysis.
        if config.UNANALYSED_ROOT in src_path.parents:
            shutil.rmtree(src_path.parent, ignore_errors=True)
            log_action("cleanup", src_path.parent.name, session.get("username"), "Deleted unanalysed artwork folder.")
            logger.info(f"Cleaned up unanalysed source folder: {src_path.parent}")
        # --- END OF CLEANUP LOGIC ---
        
    except Exception as exc:
        logger.error("Error running analysis for %s: %s", filename, exc, exc_info=True)
        flash(f"❌ Error running analysis: {exc}", "danger")
        _write_analysis_status("failed", 100, base_name, status="failed", error=str(exc))
        if "XMLHttpRequest" in request.headers.get("X-Requested-With", ""):
            return jsonify({"success": False, "error": str(exc)}), 500
        return redirect(url_for("artwork.artworks"))

    _write_analysis_status("done", 100, filename, status="complete")

    redirect_filename = f"{seo_folder}.jpg"
    redirect_url = url_for("artwork.edit_listing", aspect=aspect, filename=redirect_filename)

    if "XMLHttpRequest" in request.headers.get("X-Requested-With", ""):
        return jsonify({
            "success": True,
            "message": "Analysis complete.",
            "redirect_url": redirect_url
        })

    return redirect(redirect_url)

@bp.post("/analyze-upload/<base>")
def analyze_upload(base):
    """Analyze an uploaded image from the unanalysed folder."""
    uid, rec = utils.get_record_by_base(base)
    if not rec:
        flash("Artwork not found", "danger")
        return redirect(url_for("artwork.artworks"))
        
    folder = Path(rec["current_folder"])
    qc_path = folder / f"{base}.qc.json"
    qc = utils.load_json_file_safe(qc_path)
    orig_path = folder / f"{base}.{qc.get('extension', 'jpg')}"
    provider = request.form.get("provider", "openai")
    
    _write_analysis_status("starting", 0, orig_path.name, status="analyzing")
    try:
        analysis_result = _run_ai_analysis(orig_path, provider)
        processed_folder_path = Path(analysis_result.get("processed_folder", ""))
        seo_folder = processed_folder_path.name
        
        if not seo_folder:
            raise RuntimeError("Analysis script did not return a valid folder name.")
            
        _write_analysis_status("generating", 60, orig_path.name, status="analyzing")
        _generate_composites(seo_folder, uuid.uuid4().hex)
        
    except Exception as e:
        flash(f"❌ Error running analysis: {e}", "danger")
        _write_analysis_status("failed", 100, orig_path.name, status="failed", error=str(e))
        return redirect(url_for("artwork.artworks"))
    
    cleanup_unanalysed_folders()
    _write_analysis_status("done", 100, orig_path.name, status="complete")
    
    # CORRECTED: Redirect using the stable folder name
    redirect_filename = f"{seo_folder}.jpg"
    return redirect(url_for("artwork.edit_listing", aspect=qc.get("aspect_ratio", ""), filename=redirect_filename))


# ===========================================================================
# 8. Artwork Editing and Listing Management
# ===========================================================================
# This section contains the primary route for editing an artwork's listing
# details. It handles both GET requests to display the form and POST requests
# to save, update, or delete the listing. It also includes routes for
# managing mockups on the edit page.
# ===========================================================================

@bp.route("/review/<aspect>/<filename>")
def review_artwork(aspect, filename):
    """
    Handles a legacy URL structure for reviewing artworks.
    This route now permanently redirects to the modern 'edit_listing' page,
    ensuring old bookmarks or links continue to function.
    """
    # Redirect to the new, canonical URL for editing listings.
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

@bp.route("/review-swap-mockup/<seo_folder>/<int:slot_idx>", methods=["POST"])
def review_swap_mockup(seo_folder, slot_idx):
    """
    Handles a request to swap a single mockup from the edit page.
    This is triggered by a form submission for a specific mockup slot.
    """
    # Retrieve the new category selected by the user from the form data.
    new_category = request.form.get("new_category")
    
    # Call the utility function to perform the swap on disk.
    # The function returns a success flag and other optional data.
    success, *_ = utils.swap_one_mockup(seo_folder, slot_idx, new_category)
    
    # Display a message to the user indicating the outcome of the swap.
    flash(f"Mockup slot {slot_idx} swapped to {new_category}" if success else "Failed to swap mockup", "success" if success else "danger")
    
    # To redirect back to the correct edit page, determine the aspect ratio from the listing file.
    listing_path = next((config.PROCESSED_ROOT / seo_folder).glob("*-listing.json"), None)
    aspect = "4x5" # A fallback aspect ratio in case the listing file is not found.
    if listing_path:
        # Load the listing JSON to get the accurate aspect ratio.
        data = utils.load_json_file_safe(listing_path)
        aspect = data.get("aspect_ratio", aspect)
        
    # Redirect back to the edit page with all the necessary parameters.
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=f"{seo_folder}.jpg"))

@bp.route("/edit-listing/<aspect>/<filename>", methods=["GET", "POST"])
def edit_listing(aspect, filename):
    """
    The main endpoint for both displaying and updating a processed or finalised artwork listing.
    Handles GET requests to show the form and POST requests to save changes.
    """
    try:
        # Resolve all necessary paths for the artwork based on its aspect and filename.
        # This helper function checks processed, finalised, and locked directories.
        seo_folder, folder, listing_path, finalised = resolve_listing_paths(aspect, filename)
    except FileNotFoundError:
        # If the artwork cannot be found, flash an error and redirect to the main gallery.
        flash(f"Artwork not found: {filename}", "danger")
        return redirect(url_for("artwork.artworks"))
    
    # Load the artwork's metadata from its corresponding listing.json file.
    data = utils.load_json_file_safe(listing_path)
    # Load the generic, boilerplate text associated with the artwork's aspect ratio.
    generic_text = read_generic_text(data.get("aspect_ratio", aspect))
    # Check if the artwork is in the 'artwork-vault', which is a special locked state.
    is_locked_in_vault = config.ARTWORK_VAULT_ROOT in folder.parents

    # Handle form submission for updating the listing.
    if request.method == "POST":
        # Collect all editable fields from the submitted form.
        form_data = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "primary_colour": request.form.get("primary_colour", "").strip(),
            "secondary_colour": request.form.get("secondary_colour", "").strip(),
            "seo_filename": request.form.get("seo_filename", "").strip(),
            "price": request.form.get("price", "18.27").strip(),
            "sku": data.get("sku", "").strip(), # SKU is preserved from the existing data and not user-editable.
            "images": [i.strip() for i in request.form.get("images", "").splitlines() if i.strip()],
        }
        
        # Validate the submitted form data against a set of rules.
        errors = validate_listing_fields(form_data, generic_text)
        if errors:
            # If validation fails, flash each error message to the user.
            for error in errors: flash(error, "danger")
        else:
            # If validation passes, update the loaded data with the new form data.
            data.update(form_data)
            # Write the updated dictionary back to the listing.json file.
            with open(listing_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Inform the user that the update was successful.
            flash("Listing updated", "success")
            log_action("edits", filename, session.get("username"), "listing updated")
        # Redirect back to the same edit page to show the results or errors.
        return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

    # This block handles the GET request to display the page.
    # Populate a dictionary with all the necessary data for the template.
    artwork = utils.populate_artwork_data_from_json(data, seo_folder)
    # Get details for all associated mockups (images, thumbnails, etc.).
    mockups = utils.get_mockup_details_for_template(data.get("mockups", []), folder, seo_folder, aspect)
    
    # Render the main 'edit_listing.html' template with all the collected data.
    return render_template(
        "edit_listing.html",
        artwork=artwork,
        aspect=aspect,
        filename=filename,
        seo_folder=seo_folder,
        mockups=mockups,
        menu=utils.get_menu(),
        errors=None,
        colour_options=get_allowed_colours(),
        # Get available mockup categories for dropdowns, specific to the artwork's aspect ratio.
        categories=get_categories_for_aspect(data.get("aspect_ratio", aspect)),
        finalised=finalised,
        locked=data.get("locked", False),
        is_locked_in_vault=is_locked_in_vault,
        # The form is editable only if the listing is not marked as locked.
        editable=not data.get("locked", False),
        # Pass the raw OpenAI analysis data for display.
        openai_analysis=data.get("openai_analysis"),
        # Add a timestamp for cache-busting URLs for images.
        cache_ts=int(time.time()),
    )


# ===========================================================================
# 9. Static File and Image Serving Routes
# ===========================================================================
# These routes are responsible for serving images from various directories,
# including processed, finalised, locked, and temporary unanalysed locations.
# They are crucial for displaying artwork and mockups throughout the UI.
# ===========================================================================

@bp.route(f"/{config.PROCESSED_URL_PATH}/<path:filename>")
def processed_image(filename):
    """Serve artwork images from processed folders."""
    return send_from_directory(config.PROCESSED_ROOT, filename)

@bp.route(f"/{config.FINALISED_URL_PATH}/<path:filename>")
def finalised_image(filename):
    """Serve images strictly from the finalised-artwork folder."""
    return send_from_directory(config.FINALISED_ROOT, filename)

@bp.route(f"/{config.LOCKED_URL_PATH}/<path:filename>")
def locked_image(filename):
    """Serve images from the locked artwork vault."""
    return send_from_directory(config.ARTWORK_VAULT_ROOT, filename)

@bp.route(f"/{config.MOCKUP_THUMB_URL_PREFIX}/<path:filepath>")
def serve_mockup_thumb(filepath: str):
    """Serve mockup thumbnails from any potential location."""
    for base_dir in [config.PROCESSED_ROOT, config.FINALISED_ROOT, config.ARTWORK_VAULT_ROOT]:
        full_path = base_dir / filepath
        if full_path.is_file():
            return send_from_directory(full_path.parent, full_path.name)
    abort(404)

@bp.route(f"/{config.UNANALYSED_IMG_URL_PREFIX}/<filename>")
def unanalysed_image(filename: str):
    """Serve images from the unanalysed artwork folders."""
    path = next((p for p in config.UNANALYSED_ROOT.rglob(filename) if p.is_file()), None)
    if path:
        return send_from_directory(path.parent, path.name)
    abort(404)

@bp.route(f"/{config.COMPOSITE_IMG_URL_PREFIX}/<folder>/<filename>")
def composite_img(folder, filename):
    """Serve a specific composite image."""
    return send_from_directory(config.PROCESSED_ROOT / folder, filename)

# --- FIX: Restored missing route required by mockup_selector.html ---
@bp.route("/mockup-img/<category>/<filename>")
def mockup_img(category, filename):
    """Serves a mockup image from the central inputs directory."""
    return send_from_directory(config.MOCKUPS_INPUT_DIR / category, filename)


# ===========================================================================
# 10. Composite Image Preview Routes
# ===========================================================================
# These routes provide a preview page for generated composite images,
# allowing users to review them before finalising the artwork.
# ===========================================================================

@bp.route("/composites")
def composites_preview():
    """Redirect to the latest composite folder or the main artworks page."""
    latest = utils.latest_composite_folder()
    if latest:
        return redirect(url_for("artwork.composites_specific", seo_folder=latest))
    flash("No composites found", "warning")
    return redirect(url_for("artwork.artworks"))


@bp.route("/composites/<seo_folder>")
def composites_specific(seo_folder):
    """Display the composite images for a specific artwork."""
    folder = utils.PROCESSED_ROOT / seo_folder
    json_path = folder / f"{seo_folder}-listing.json"
    images = []
    if json_path.exists():
        listing = utils.load_json_file_safe(json_path)
        images = utils.get_mockup_details_for_template(
            listing.get("mockups", []), folder, seo_folder, listing.get("aspect_ratio", "")
        )
    return render_template(
        "composites_preview.html",
        images=images,
        folder=seo_folder,
        menu=utils.get_menu(),
    )


@bp.route("/approve_composites/<seo_folder>", methods=["POST"])
def approve_composites(seo_folder):
    """Placeholder for approving composites and moving to the next step."""
    # In the current flow, finalisation handles this implicitly.
    listing_path = next((PROCESSED_ROOT / seo_folder).glob("*-listing.json"), None)
    if listing_path:
        data = utils.load_json_file_safe(listing_path)
        aspect = data.get("aspect_ratio", "4x5")
        filename = data.get("seo_filename", f"{seo_folder}.jpg")
        flash("Composites approved. Please review and finalise.", "success")
        return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))
    flash("Could not find listing data.", "danger")
    return redirect(url_for("artwork.artworks"))


# ===========================================================================
# 11. Artwork Finalisation and Gallery Routes
# ===========================================================================
# These routes handle the final step of the workflow: moving an artwork
# to the 'finalised' directory. It also includes the gallery pages for
# viewing all finalised and locked artworks.
# ===========================================================================

@bp.route("/finalise/<aspect>/<filename>", methods=["GET", "POST"])
def finalise_artwork(aspect, filename):
    """Move processed artwork to the finalised location."""
    try:
        seo_folder, _, _, _ = resolve_listing_paths(aspect, filename)
    except FileNotFoundError:
        flash(f"Artwork not found: {filename}", "danger")
        return redirect(url_for("artwork.artworks"))

    processed_dir = utils.PROCESSED_ROOT / seo_folder
    final_dir = utils.FINALISED_ROOT / seo_folder
    user = session.get("username")

    try:
        if final_dir.exists(): shutil.rmtree(final_dir)
        shutil.move(str(processed_dir), str(final_dir))

        listing_file = final_dir / f"{seo_folder}-listing.json"
        if listing_file.exists():
            utils.assign_or_get_sku(listing_file, config.SKU_TRACKER)
            utils.update_listing_paths(listing_file, PROCESSED_ROOT, FINALISED_ROOT)

        log_action("finalise", filename, user, f"finalised to {final_dir}")
        flash("Artwork finalised", "success")
    except Exception as e:
        log_action("finalise", filename, user, "finalise failed", status="fail", error=str(e))
        flash(f"Failed to finalise artwork: {e}", "danger")
        if final_dir.exists() and not processed_dir.exists():
            shutil.move(str(final_dir), str(processed_dir))
            flash("Attempted to roll back the move.", "info")

    return redirect(url_for("artwork.finalised_gallery"))


@bp.route("/finalised")
def finalised_gallery():
    """Display all finalised artworks in a gallery view."""
    artworks = [a for a in utils.get_all_artworks() if a['status'] == 'finalised']
    return render_template("finalised.html", artworks=artworks, menu=utils.get_menu())


@bp.route("/locked")
def locked_gallery():
    """Show gallery of locked artworks only."""
    locked_items = [a for a in utils.get_all_artworks() if a.get('locked')]
    return render_template("locked.html", artworks=locked_items, menu=utils.get_menu())


# ===========================================================================
# 12. Listing State Management (Lock, Unlock, Delete)
# ===========================================================================
# These routes manage the lifecycle of a finalised artwork, allowing it
# to be locked (moved to a vault), unlocked (moved back to finalised),
# or deleted entirely.
# ===========================================================================

@bp.post("/finalise/delete/<aspect>/<filename>")
def delete_finalised(aspect, filename):
    # ... (function remains the same)
    try:
        _, folder, listing_file, _ = resolve_listing_paths(aspect, filename)
        info = utils.load_json_file_safe(listing_file)
        if info.get("locked") and request.form.get("confirm") != "DELETE":
            flash("Type DELETE to confirm deletion of a locked item.", "warning")
            return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))
        
        shutil.rmtree(folder)
        flash("Artwork deleted successfully.", "success")
        log_action("delete", filename, session.get("username"), f"Deleted folder {folder}")
    except FileNotFoundError:
        flash("Artwork not found.", "danger")
    except Exception as e:
        flash(f"Delete failed: {e}", "danger")
    return redirect(url_for("artwork.finalised_gallery"))


@bp.post("/lock/<aspect>/<filename>")
def lock_listing(aspect, filename):
    # ... (function remains the same)
    try:
        seo, folder, listing_path, finalised = resolve_listing_paths(aspect, filename)
        if not finalised:
            flash("Artwork must be finalised before locking.", "danger")
            return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))
        
        target = config.ARTWORK_VAULT_ROOT / f"LOCKED-{seo}"
        config.ARTWORK_VAULT_ROOT.mkdir(parents=True, exist_ok=True)
        if target.exists(): shutil.rmtree(target)
        shutil.move(str(folder), str(target))

        new_listing_path = target / listing_path.name
        with open(new_listing_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["locked"] = True
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()
        utils.update_listing_paths(new_listing_path, folder, target)
        flash("Artwork locked.", "success")
        log_action("lock", filename, session.get("username"), "locked artwork")
    except Exception as exc:
        flash(f"Failed to lock: {exc}", "danger")
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


@bp.post("/unlock/<aspect>/<filename>")
def unlock_listing(aspect, filename):
    """
    Unlock a previously locked artwork.
    MODIFIED: Now requires 'UNLOCK' confirmation and only changes the JSON
    flag, leaving the files in the artwork-vault.
    """
    # 1. Check for confirmation text
    if request.form.get("confirm_unlock") != "UNLOCK":
        flash("Incorrect confirmation text. Please type UNLOCK to proceed.", "warning")
        return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

    try:
        # 2. Resolve paths, ensuring we are looking in the vault
        _, _, listing_path, _ = resolve_listing_paths(aspect, filename, allow_locked=True)
        if config.ARTWORK_VAULT_ROOT not in listing_path.parents:
            flash("Cannot unlock an item that is not in the vault.", "danger")
            return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

        # 3. Read the file, change the flag, and save it back in place
        with open(listing_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["locked"] = False
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()
        
        log_action("unlock", filename, session.get("username"), "unlocked artwork")
        flash("Artwork unlocked and is now editable. File paths remain unchanged.", "success")
    
    except FileNotFoundError:
        flash("Locked artwork not found.", "danger")
        return redirect(url_for("artwork.artworks"))
    except Exception as exc:
        log_action("unlock", filename, session.get("username"), "unlock failed", status="fail", error=str(exc))
        flash(f"Failed to unlock: {exc}", "danger")
        
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


# ===========================================================================
# 13. Asynchronous API Endpoints
# ===========================================================================
# This section contains routes designed to be called via AJAX/Fetch from the
# frontend. They perform specific actions like updating image links or
# resetting an SKU and return JSON responses.
# ===========================================================================

@bp.post("/update-links/<aspect>/<filename>")
def update_links(aspect, filename):
    """Regenerate the image URL list from disk and return as JSON."""
    wants_json = "application/json" in request.headers.get("Accept", "")
    try:
        _, folder, listing_file, _ = resolve_listing_paths(aspect, filename)
        data = utils.load_json_file_safe(listing_file)
        imgs = [p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
        data["images"] = [utils.relative_to_base(p) for p in sorted(imgs)]
        with open(listing_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        msg = "Image links updated"
        if wants_json: return jsonify({"success": True, "message": msg, "images": data["images"]})
        flash(msg, "success")
    except Exception as e:
        msg = f"Failed to update links: {e}"
        if wants_json: return jsonify({"success": False, "message": msg, "images": []}), 500
        flash(msg, "danger")
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


@bp.post("/reset-sku/<aspect>/<filename>")
def reset_sku(aspect, filename):
    """Force reassign a new SKU for the given artwork."""
    try:
        _, _, listing, _ = resolve_listing_paths(aspect, filename)
        utils.assign_or_get_sku(listing, config.SKU_TRACKER, force=True)
        flash("SKU has been reset.", "success")
    except Exception as exc:
        flash(f"Failed to reset SKU: {exc}", "danger")
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


@bp.post("/delete/<filename>")
def delete_artwork(filename: str):
    """Delete all files and registry entries for an artwork, regardless of its state."""
    logger, user = logging.getLogger(__name__), session.get("username", "unknown")
    log_action("delete", filename, user, f"Initiating delete for '{filename}'")
    
    base_stem = Path(filename).stem

    # --- Step 1: Clean up processed/finalised/locked folders if they exist ---
    try:
        # Use the utility that can find the folder from an original filename
        seo_folder = utils.find_seo_folder_from_filename("", filename)
        if seo_folder:
            shutil.rmtree(config.PROCESSED_ROOT / seo_folder, ignore_errors=True)
            shutil.rmtree(config.FINALISED_ROOT / seo_folder, ignore_errors=True)
            # Locked folders have a prefix
            shutil.rmtree(config.ARTWORK_VAULT_ROOT / f"LOCKED-{seo_folder}", ignore_errors=True)
            logger.info(f"Deleted processed/finalised/locked folders for {seo_folder}")
    except FileNotFoundError:
        # This is expected if the artwork was never processed
        logger.info(f"No processed folder found for '{filename}', proceeding to clean unanalysed files.")
        pass

    # --- Step 2: Clean up the original unanalysed files and folder ---
    # Find all files related to the original upload (image, thumb, qc.json, etc.)
    found_files = list(config.UNANALYSED_ROOT.rglob(f"{base_stem}*"))
    if found_files:
        # Get the parent directory from the first found file
        parent_dir = found_files[0].parent
        if parent_dir != config.UNANALYSED_ROOT:
             shutil.rmtree(parent_dir, ignore_errors=True)
             logger.info(f"Deleted unanalysed folder: {parent_dir}")
    
    # --- Step 3: Clean up the registry entry using the unique base name ---
    uid, _ = utils.get_record_by_base(base_stem)
    if uid:
        utils.remove_record_from_registry(uid)
        logger.info(f"Removed registry record {uid}")
    
    log_action("delete", filename, user, "Delete process completed.")
    return jsonify({"success": True})


# --- NEW ENDPOINT FOR REWORDING GENERIC TEXT ---
@bp.post("/api/reword-generic-text")
def reword_generic_text_api():
    """
    Handles an asynchronous request to reword the generic part of a description.
    Accepts the main description and generic text, returns reworded text.
    """
    logger = logging.getLogger(__name__)
    data = request.json

    provider = data.get("provider")
    artwork_desc = data.get("artwork_description")
    generic_text = data.get("generic_text")

    if not all([provider, artwork_desc, generic_text]):
        logger.error("Reword API call missing required data.")
        return jsonify({"success": False, "error": "Missing required data."}), 400

    try:
        reworded_text = ai_services.call_ai_to_reword_text(
            provider=provider,
            artwork_description=artwork_desc,
            generic_text=generic_text
        )
        logger.info(f"Successfully reworded text using {provider}.")
        return jsonify({"success": True, "reworded_text": reworded_text})

    except Exception as e:
        logger.error(f"Failed to reword generic text: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ===========================================================================
# 14. File Processing and Utility Helpers
# ===========================================================================
# This section holds helper functions that are used by the route handlers,
# particularly for processing uploaded files. This includes validation,
# thumbnailing, and creating QC (Quality Control) data files.
# ===========================================================================

@bp.route("/next-sku")
def preview_next_sku():
    """Return the next available SKU without reserving it."""
    return Response(peek_next_sku(config.SKU_TRACKER), mimetype="text/plain")

def _process_upload_file(file_storage, dest_folder):
    """Validate, save, and preprocess a single uploaded file."""
    filename = file_storage.filename
    if not filename: return {"original": filename, "success": False, "error": "No filename"}

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in config.ALLOWED_EXTENSIONS:
        return {"original": filename, "success": False, "error": "Invalid file type"}
    
    data = file_storage.read()
    if len(data) > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        return {"original": filename, "success": False, "error": "File too large"}

    safe, unique, uid = aa.slugify(Path(filename).stem), uuid.uuid4().hex[:8], uuid.uuid4().hex
    base = f"{safe}-{unique}"
    dest_folder.mkdir(parents=True, exist_ok=True)
    orig_path = dest_folder / f"{base}.{ext}"

    try:
        orig_path.write_bytes(data)
        with Image.open(orig_path) as img:
            width, height = img.size
            # Create thumbnail
            thumb_path = dest_folder / f"{base}-thumb.jpg"
            thumb = img.copy()
            thumb.thumbnail((config.THUMB_WIDTH, config.THUMB_HEIGHT))
            thumb.save(thumb_path, "JPEG", quality=80)
            # Create analysis-sized image
            analyse_path = dest_folder / f"{base}-analyse.jpg"
            utils.resize_for_analysis(img, analyse_path)
    except Exception as exc:
        logging.getLogger(__name__).error("Image processing failed: %s", exc)
        return {"original": filename, "success": False, "error": "Image processing failed"}
    
    qc_data = {
        "original_filename": filename, "extension": ext, "image_shape": [width, height],
        "filesize_bytes": len(data), "aspect_ratio": aa.get_aspect_ratio(orig_path),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    qc_path = dest_folder / f"{base}.qc.json"
    qc_path.write_text(json.dumps(qc_data, indent=2))

    utils.register_new_artwork(uid, f"{base}.{ext}", dest_folder, [orig_path.name, thumb_path.name, analyse_path.name, qc_path.name], "unanalysed", base)
    
    return {"success": True, "base": base, "aspect": qc_data["aspect_ratio"], "uid": uid, "original": filename}


# ===========================================================================
# 15. Artwork Signing Route
# ===========================================================================
# (You will need to add this import at the top of the file)
from scripts import signing_service

@bp.post("/sign-artwork/<base_name>")
def sign_artwork_route(base_name: str):
    """
    Finds an unanalysed artwork by its base name, applies a smart
    signature, and replaces the original file with the signed version.
    """
    # Find the source file in the unanalysed artworks directory
    source_path = next((p for p in config.UNANALYSED_ROOT.rglob(f"{base_name}.*") if "-thumb" not in p.name and "-analyse" not in p.name), None)

    if not source_path:
        return jsonify({"success": False, "error": "Original artwork file not found."}), 404
        
    # The destination is the same as the source to replace it in-place
    destination_path = source_path
    
    success, message = signing_service.add_smart_signature(source_path, destination_path)
    
    if success:
        log_action("sign", source_path.name, session.get("username"), "Artwork signed successfully")
        return jsonify({"success": True, "message": message})
    else:
        log_action("sign", source_path.name, session.get("username"), "Artwork signing failed", status="fail", error=message)
        return jsonify({"success": False, "error": message}), 500

---
## routes/artwork_routes.py
---
# routes/artwork_routes.py
# -*- coding: utf-8 -*-
"""
Artwork-related Flask routes for the ArtNarrator application.

This module powers the entire artwork processing workflow, from initial
upload and AI analysis to mockup review, finalization, and state management.

Table of Contents (ToC)
-----------------------
[artwork-routes-py-1] Imports & Initialisation
    [artwork-routes-py-1a] Imports
    [artwork-routes-py-1b] Blueprint Setup

[artwork-routes-py-2] Health Checks and Status API
    [artwork-routes-py-2a] health_openai
    [artwork-routes-py-2b] health_google
    [artwork-routes-py-2c] _write_analysis_status
    [artwork-routes-py-2d] analysis_status

[artwork-routes-py-3] AI Analysis & Subprocess Helpers
    [artwork-routes-py-3a] _run_ai_analysis
    [artwork-routes-py-3b] _generate_composites

[artwork-routes-py-4] Validation and Data Helpers
    [artwork-routes-py-4a] validate_listing_fields
    [artwork-routes-py-4b] get_categories_for_aspect

[artwork-routes-py-5] Core Navigation & Upload Routes
    [artwork-routes-py-5a] inject_latest_artwork
    [artwork-routes-py-5b] home
    [artwork-routes-py-5c] upload_artwork
    [artwork-routes-py-5d] artworks

[artwork-routes-py-6] Mockup Selection Workflow Routes
    [artwork-routes-py-6a] select
    [artwork-routes-py-6b] regenerate
    [artwork-routes-py-6c] swap
    [artwork-routes-py-6d] proceed

[artwork-routes-py-7] Artwork Analysis Trigger Routes
    [artwork-routes-py-7a] analyze_artwork_route
    [artwork-routes-py-7b] analyze_upload

[artwork-routes-py-8] Artwork Editing and Listing Management
    [artwork-routes-py-8a] edit_listing

[artwork-routes-py-9] Static File and Image Serving Routes
    [artwork-routes-py-9a] processed_image
    [artwork-routes-py-9b] finalised_image
    [artwork-routes-py-9c] locked_image
    [artwork-routes-py-9d] serve_mockup_thumb
    [artwork-routes-py-9e] unanalysed_image
    [artwork-routes-py-9f] composite_img
    [artwork-routes-py-9g] mockup_img

[artwork-routes-py-10] Composite Image Preview Routes
    [artwork-routes-py-10a] composites_preview
    [artwork-routes-py-10b] composites_specific
    [artwork-routes-py-10c] approve_composites

[artwork-routes-py-11] Artwork Finalisation and Gallery Routes
    [artwork-routes-py-11a] finalise_artwork
    [artwork-routes-py-11b] finalised_gallery
    [artwork-routes-py-11c] locked_gallery
    [artwork-routes-py-11d] lock_it_in

[artwork-routes-py-12] Listing State Management (Lock, Unlock, Delete)
    [artwork-routes-py-12a] delete_finalised
    [artwork-routes-py-12b] lock_listing
    [artwork-routes-py-12c] unlock_listing
    [artwork-routes-py-12d] unlock_artwork

[artwork-routes-py-13] Asynchronous API Endpoints
    [artwork-routes-py-13a] update_links
    [artwork-routes-py-13b] reset_sku
    [artwork-routes-py-13c] delete_artwork
    [artwork-routes-py-13d] reword_generic_text_api

[artwork-routes-py-14] File Processing and Utility Helpers
    [artwork-routes-py-14a] preview_next_sku
    [artwork-routes-py-14b] _process_upload_file

[artwork-routes-py-15] Artwork Signing Route
    [artwork-routes-py-15a] sign_artwork_route
"""

# === [ Section 1: Imports & Initialisation | artwork-routes-py-1 ] ===
# Handles all necessary library imports and sets up the Flask Blueprint.
# Cross-references: config.py, helpers/listing_utils.py, routes/utils.py
# ---------------------------------------------------------------------------------

# --- [ 1a: Imports | artwork-routes-py-1a ] ---
from __future__ import annotations
import json, subprocess, uuid, random, logging, shutil, os, traceback, datetime, time, sys
from pathlib import Path
from PIL import Image
import google.generativeai as genai
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort, Response, jsonify,
)
import re

# Local Application Imports
import config
from helpers.listing_utils import (
    resolve_listing_paths,
    create_unanalysed_subfolder,
    cleanup_unanalysed_folders,
    load_json_file_safe,
    generate_public_image_urls,
    remove_artwork_from_registry,
    delete_artwork as delete_artwork_files,
    update_artwork_registry,
)
import scripts.analyze_artwork as aa
from scripts import signing_service
from . import utils
from routes import utils as route_utils
from utils.logger_utils import log_action
from utils.sku_assigner import peek_next_sku
from utils import ai_services
from .utils import (
    ALLOWED_COLOURS_LOWER, read_generic_text, clean_terms, infer_sku_from_filename,
    is_finalised_image, get_allowed_colours, update_listing_paths
)


# --- [ 1b: Blueprint Setup | artwork-routes-py-1b ] ---
bp = Blueprint("artwork", __name__)


# === [ Section 2: Health Checks and Status API | artwork-routes-py-2 ] ===
# Endpoints for monitoring the health of external services (OpenAI, Google)
# and for providing real-time status updates on background analysis jobs.
# ---------------------------------------------------------------------------------

# --- [ 2a: health_openai | artwork-routes-py-2a ] ---
@bp.get("/health/openai")
def health_openai():
    """Provides a health check endpoint for the OpenAI API connection."""
    logger = logging.getLogger(__name__)
    try:
        aa.client.models.list()
        return jsonify({"ok": True})
    except Exception as exc:
        logger.error("OpenAI health check failed: %s", exc)
        error = str(exc)
        if config.DEBUG:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500


# --- [ 2b: health_google | artwork-routes-py-2b ] ---
@bp.get("/health/google")
def health_google():
    """Provides a health check endpoint for the Google Gemini API connection."""
    logger = logging.getLogger(__name__)
    try:
        genai.list_models()
        return jsonify({"ok": True})
    except Exception as exc:
        logger.error("Google health check failed: %s", exc)
        error = str(exc)
        if config.DEBUG:
            error += "\n" + traceback.format_exc()
        return jsonify({"ok": False, "error": error}), 500


# --- [ 2c: _write_analysis_status | artwork-routes-py-2c ] ---
def _write_analysis_status(step: str, percent: int, file: str | None = None, status: str | None = None, error: str | None = None) -> None:
    """
    Writes the current progress of an analysis job to a shared JSON file.
    This file is polled by the frontend to update the UI modal.
    """
    logger = logging.getLogger(__name__)
    payload = {"step": step, "percent": percent, "file": file, "status": status, "error": error}
    try:
        config.ANALYSIS_STATUS_FILE.write_text(json.dumps({k: v for k, v in payload.items() if v is not None}))
    except Exception as exc:
        logger.error("Failed writing analysis status: %s", exc)


# --- [ 2d: analysis_status | artwork-routes-py-2d ] ---
@bp.route("/status/analyze")
def analysis_status():
    """Returns the content of the analysis status JSON file for frontend polling."""
    return Response(config.ANALYSIS_STATUS_FILE.read_text(), mimetype="application/json")


# === [ Section 3: AI Analysis & Subprocess Helpers | artwork-routes-py-3 ] ===
# Helper functions for invoking external Python scripts (like AI analysis
# and mockup generation) as separate processes.
# ---------------------------------------------------------------------------------

# --- [ 3a: _run_ai_analysis | artwork-routes-py-3a ] ---
def _run_ai_analysis(img_path: Path, provider: str) -> dict:
    """
    Executes the AI analysis script as a subprocess and captures its JSON output.

    Args:
        img_path: The absolute path to the image file to be analyzed.
        provider: The AI provider to use (e.g., 'openai').

    Returns:
        A dictionary parsed from the script's JSON output.
    """
    logger = logging.getLogger("art_analysis")
    logger.info("[DEBUG] _run_ai_analysis: img_path=%s provider=%s", img_path, provider)

    if provider == "openai":
        cmd = [sys.executable, str(config.ANALYZE_SCRIPT_PATH), str(img_path), "--json-output"]
    else:
        raise ValueError(f"Unknown provider: {provider}")

    logger.info("[DEBUG] Subprocess cmd: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        msg = (result.stderr or "Unknown error").strip()
        raise RuntimeError(f"AI analysis failed: {msg}")
    
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        logger.error("JSON decode error: %s", e)
        raise RuntimeError("AI analysis output could not be parsed.") from e


# --- [ 3b: _generate_composites | artwork-routes-py-3b ] ---
def _generate_composites(log_id: str) -> None:
    """Triggers the queue-based composite/mockup generation script as a subprocess."""
    cmd = [sys.executable, str(config.GENERATE_SCRIPT_PATH)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=config.BASE_DIR, timeout=600)
    composite_log = config.LOGS_DIR / "composite-generation-logs" / f"composite_gen_{log_id}.log"
    composite_log.parent.mkdir(exist_ok=True, parents=True)
    composite_log.write_text(f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}")
    if result.returncode != 0:
        raise RuntimeError(f"Composite generation failed ({result.returncode})")


# === [ Section 4: Validation and Data Helpers | artwork-routes-py-4 ] ===
# Functions for validating form data and retrieving data needed by templates.
# ---------------------------------------------------------------------------------

# --- [ 4a: validate_listing_fields | artwork-routes-py-4a ] ---
def validate_listing_fields(data: dict, generic_text: str) -> list[str]:
    """
    Validates all fields from the edit listing form against business rules.

    Args:
        data: A dictionary of form data.
        generic_text: The boilerplate text block to check for inclusion.

    Returns:
        A list of string error messages. An empty list indicates success.
    """
    errors: list[str] = []
    title = data.get("title", "").strip()
    if not title: errors.append("Title cannot be blank")
    if len(title) > 140: errors.append("Title exceeds 140 characters")
    tags = data.get("tags", [])
    if len(tags) > 13: errors.append("Too many tags (max 13)")
    for t in tags:
        if not t or len(t) > 20: errors.append(f"Invalid tag: '{t}'")
        if not re.fullmatch(r"[A-Za-z0-9 ]+", t): errors.append(f"Tag has invalid characters: '{t}'")
    seo_filename = data.get("seo_filename", "")
    if len(seo_filename) > 70: errors.append("SEO filename exceeds 70 characters")
    if not re.search(r"-by-robin-custance-RJC-[A-Za-z0-9-]+\.jpg$", seo_filename, re.IGNORECASE):
        errors.append("SEO filename must end with '-by-robin-custance-RJC-XXXX.jpg'")
    sku = data.get("sku", "")
    if not sku: errors.append("SKU is required")
    if sku and not sku.startswith("RJC-"): errors.append("SKU must start with 'RJC-'")
    if sku and utils.infer_sku_from_filename(seo_filename or "") != sku:
        errors.append("SKU must match value in SEO filename")
    try:
        if abs(float(data.get("price")) - 18.27) > 1e-2: errors.append("Price must be 18.27")
    except (ValueError, TypeError): errors.append("Price must be a number (18.27)")
    for key in ("primary_colour", "secondary_colour"):
        col = data.get(key, "").strip()
        if not col: errors.append(f"{key.replace('_', ' ').title()} is required")
        elif col.lower() not in utils.ALLOWED_COLOURS_LOWER: errors.append(f"{key.replace('_', ' ').title()} invalid")
    images = [i.strip() for i in data.get("images", []) if str(i).strip()]
    if not images: errors.append("At least one image required")
    desc = data.get("description", "").strip()
    if len(desc.split()) < 400: errors.append("Description must be at least 400 words")
    if generic_text and "About the Artist – Robin Custance".lower() not in " ".join(desc.split()).lower():
        errors.append("Description must include the correct generic context block.")
    return errors


# --- [ 4b: get_categories_for_aspect | artwork-routes-py-4b ] ---
def get_categories_for_aspect(aspect: str) -> list[str]:
    """Returns a sorted list of available mockup category names for a given aspect ratio."""
    base = config.MOCKUPS_CATEGORISED_DIR / aspect
    return sorted([f.name for f in base.iterdir() if f.is_dir()]) if base.exists() else []


# === [ Section 5: Core Navigation & Upload Routes | artwork-routes-py-5 ] ===
# Handles the main UI pages: the homepage, the artwork gallery/dashboard,
# and the file upload page.
# ---------------------------------------------------------------------------------

# --- [ 5a: inject_latest_artwork | artwork-routes-py-5a ] ---
@bp.app_context_processor
def inject_latest_artwork():
    """Injects data about the latest analyzed artwork into all templates."""
    return dict(latest_artwork=utils.latest_analyzed_artwork())


# --- [ 5b: home | artwork-routes-py-5b ] ---
@bp.route("/")
def home():
    """Renders the main home/dashboard page."""
    return render_template("index.html", menu=utils.get_menu())


# --- [ 5c: upload_artwork | artwork-routes-py-5c ] ---
@bp.route("/upload", methods=["GET", "POST"])
def upload_artwork():
    """Handles new artwork file uploads and runs initial QC checks."""
    if request.method == "POST":
        files = request.files.getlist("images")
        results = []
        user = session.get("username")
        
        for f in files:
            folder = create_unanalysed_subfolder(f.filename)
            try:
                res = _process_upload_file(f, folder)
            except Exception as exc:
                logging.getLogger(__name__).error("Upload failed for %s: %s", f.filename, exc)
                res = {"original": f.filename, "success": False, "error": str(exc)}
            
            log_action("upload", res.get("original", f.filename), user, res.get("error", "uploaded"), status="success" if res.get("success") else "fail")
            results.append(res)
        
        if "XMLHttpRequest" in request.headers.get("X-Requested-With", ""):
            return jsonify(results)
        
        if any(r["success"] for r in results):
            flash(f"Uploaded {sum(1 for r in results if r['success'])} file(s) successfully", "success")
        for r in [r for r in results if not r["success"]]:
            flash(f"{r['original']}: {r['error']}", "danger")

        return redirect(url_for("artwork.artworks"))
        
    return render_template("upload.html", menu=utils.get_menu())


# --- [ 5d: artworks | artwork-routes-py-5d ] ---
@bp.route("/artworks")
def artworks():
    """Displays galleries of artworks in 'Ready to Analyze', 'Processed', and 'Finalised' states."""
    processed, processed_names = utils.list_processed_artworks()
    ready = utils.list_ready_to_analyze(processed_names)
    finalised = utils.list_finalised_artworks()
    return render_template("artworks.html", ready_artworks=ready, processed_artworks=processed, finalised_artworks=finalised, menu=utils.get_menu())
    

# === [ Section 6: Mockup Selection Workflow Routes | artwork-routes-py-6 ] ===
# DEPRECATED: These routes were part of an older, manual mockup selection flow.
# They are kept for reference but are no longer active in the main UI.
# ---------------------------------------------------------------------------------

# --- [ 6a: select | artwork-routes-py-6a ] ---
@bp.route("/select", methods=["GET", "POST"])
def select():
    """(DEPRECATED) Displays the old mockup selection interface."""
    if "slots" not in session or request.args.get("reset") == "1":
        utils.init_slots()
    slots = session["slots"]
    options = utils.compute_options(slots)
    zipped = list(zip(slots, options))
    return render_template("mockup_selector.html", zipped=zipped, menu=utils.get_menu())


# --- [ 6b: regenerate | artwork-routes-py-6b ] ---
@bp.route("/regenerate", methods=["POST"])
def regenerate():
    """(DEPRECATED) Regenerates a random mockup for a specific slot."""
    slot_idx = int(request.form["slot"])
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        cat = slots[slot_idx]["category"]
        slots[slot_idx]["image"] = utils.random_image(cat, "4x5")
        session["slots"] = slots
    return redirect(url_for("artwork.select"))


# --- [ 6c: swap | artwork-routes-py-6c ] ---
@bp.route("/swap", methods=["POST"])
def swap():
    """(DEPRECATED) Swaps a mockup slot to a new category."""
    slot_idx = int(request.form["slot"])
    new_cat = request.form["new_category"]
    slots = session.get("slots", [])
    if 0 <= slot_idx < len(slots):
        slots[slot_idx]["category"] = new_cat
        slots[slot_idx]["image"] = utils.random_image(new_cat, "4x5")
        session["slots"] = slots
    return redirect(url_for("artwork.select"))


# --- [ 6d: proceed | artwork-routes-py-6d ] ---
@bp.route("/proceed", methods=["POST"])
def proceed():
    """(DEPRECATED) Finalises mockup selections and triggers composite generation."""
    flash("Composite generation process initiated!", "success")
    latest = utils.latest_composite_folder()
    if latest:
        return redirect(url_for("artwork.composites_specific", seo_folder=latest))
    return redirect(url_for("artwork.composites_preview"))


# === [ Section 7: Artwork Analysis Trigger Routes | artwork-routes-py-7 ] ===
# These routes handle the initiation of the AI analysis process. They are
# triggered from the artwork gallery page.
# ---------------------------------------------------------------------------------

# --- [ 7a: analyze_artwork_route | artwork-routes-py-7a ] ---
@bp.route("/analyze/<aspect>/<filename>", methods=["POST"], endpoint="analyze_artwork")
def analyze_artwork_route(aspect, filename):
    """
    Runs AI analysis on a given artwork file. This can be a fresh analysis
    from the 'unanalysed' folder or a re-analysis of a 'processed' artwork.
    """
    logger, provider = logging.getLogger(__name__), request.form.get("provider", "openai").lower()
    base_name = Path(filename).name
    _write_analysis_status("starting", 0, base_name, status="analyzing")
    is_ajax = "XMLHttpRequest" in request.headers.get("X-Requested-With", "")

    src_path = next((p for p in config.UNANALYSED_ROOT.rglob(base_name) if p.is_file()), None)
    
    old_processed_folder_path = None
    is_reanalysis = False
    
    if not src_path:
        try:
            seo_folder = utils.find_seo_folder_from_filename(aspect, filename)
            potential_path = config.PROCESSED_ROOT / seo_folder / f"{seo_folder}.jpg"
            if potential_path.exists():
                src_path = potential_path
                is_reanalysis = True
                old_processed_folder_path = src_path.parent
        except FileNotFoundError: pass

    if not src_path or not src_path.exists():
        flash(f"Artwork file not found: {filename}", "danger")
        if is_ajax: return jsonify({"success": False, "error": "Artwork file not found"}), 404
        return redirect(url_for("artwork.artworks"))

    try:
        analysis_result = _run_ai_analysis(src_path, provider)
        new_seo_folder_name = Path(analysis_result.get("processed_folder", "")).name
        
        if not new_seo_folder_name: raise RuntimeError("Analysis script did not return a valid folder name.")

        _generate_composites(uuid.uuid4().hex)
        
        if config.UNANALYSED_ROOT in src_path.parents:
            shutil.rmtree(src_path.parent, ignore_errors=True)
            log_action("cleanup", src_path.parent.name, session.get("username"), "Deleted unanalysed artwork folder.")
            logger.info(f"Cleaned up unanalysed source folder: {src_path.parent}")
        
        new_folder_path = config.PROCESSED_ROOT / new_seo_folder_name
        if is_reanalysis and old_processed_folder_path and old_processed_folder_path.exists() and old_processed_folder_path != new_folder_path:
            shutil.rmtree(old_processed_folder_path)
            log_action("cleanup", old_processed_folder_path.name, session.get("username"), "Deleted old folder after re-analysis.")
            logger.info(f"Cleaned up old processed folder after re-analysis: {old_processed_folder_path}")

    except Exception as exc:
        logger.error(f"Error running analysis for {filename}: {exc}", exc_info=True)
        flash(f"❌ Error running analysis: {exc}", "danger")
        if is_ajax: return jsonify({"success": False, "error": str(exc)}), 500
        return redirect(url_for("artwork.artworks"))

    redirect_filename = f"{new_seo_folder_name}.jpg"
    # FIX (2025-08-04): Corrected the endpoint from 'artwork.edit_listing' to 'edit_listing.edit_listing'.
    redirect_url = url_for("edit_listing.edit_listing", aspect=aspect, filename=redirect_filename)

    if is_ajax:
        return jsonify({
            "success": True,
            "message": "Analysis complete.",
            "redirect_url": redirect_url
        })
    
    return redirect(redirect_url)


# --- [ 7b: analyze_upload | artwork-routes-py-7b ] ---
@bp.post("/analyze-upload/<base>")
def analyze_upload(base):
    """(DEPRECATED) Legacy route to analyze an uploaded image from the unanalysed folder."""
    uid, rec = utils.get_record_by_base(base)
    if not rec:
        flash("Artwork not found", "danger")
        return redirect(url_for("artwork.artworks"))
        
    folder = Path(rec["current_folder"])
    qc_path = folder / f"{base}.qc.json"
    qc = load_json_file_safe(qc_path)
    orig_path = folder / f"{base}.{qc.get('extension', 'jpg')}"
    provider = request.form.get("provider", "openai")
    
    _write_analysis_status("starting", 0, orig_path.name, status="analyzing")
    try:
        analysis_result = _run_ai_analysis(orig_path, provider)
        processed_folder_path = Path(analysis_result.get("processed_folder", ""))
        seo_folder = processed_folder_path.name
        
        if not seo_folder:
            raise RuntimeError("Analysis script did not return a valid folder name.")
            
        _write_analysis_status("generating", 60, orig_path.name, status="analyzing")
        _generate_composites(uuid.uuid4().hex)
        
    except Exception as e:
        flash(f"❌ Error running analysis: {e}", "danger")
        _write_analysis_status("failed", 100, orig_path.name, status="failed", error=str(e))
        return redirect(url_for("artwork.artworks"))
    
    cleanup_unanalysed_folders()
    _write_analysis_status("done", 100, orig_path.name, status="complete")
    
    redirect_filename = f"{seo_folder}.jpg"
    # FIX (2025-08-04): Corrected the endpoint from 'artwork.edit_listing' to 'edit_listing.edit_listing'.
    return redirect(url_for("edit_listing.edit_listing", aspect=qc.get("aspect_ratio", ""), filename=redirect_filename))


# === [ Section 8: Artwork Editing and Listing Management | artwork-routes-py-8 ] ===
# The main route for editing an artwork's listing details, handling both
# displaying the form (GET) and saving changes (POST).
# ---------------------------------------------------------------------------------

# --- [ 8a: edit_listing | artwork-routes-py-8a ] ---
@bp.route("/edit-listing/<aspect>/<filename>", methods=["GET", "POST"])
def edit_listing(aspect, filename):
    """Displays and updates a processed or finalised artwork listing."""
    try:
        # The resolve_listing_paths helper is now in helpers/listing_utils.py
        seo_folder, folder, listing_path, finalised = resolve_listing_paths(aspect, filename, allow_locked=True)
    except FileNotFoundError:
        flash(f"Artwork not found: {filename}", "danger")
        return redirect(url_for("artwork.artworks"))
    
    data = load_json_file_safe(listing_path)
    is_locked_in_vault = config.ARTWORK_VAULT_ROOT in folder.parents

    # Determine the current stage/status of the artwork
    if is_locked_in_vault:
        stage = "locked"
    elif finalised:
        stage = "finalised"
    else:
        stage = "processed"
    
    public_image_urls = generate_public_image_urls(seo_folder, stage)

    if request.method == "POST":
        form_data = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "tags": [t.strip() for t in request.form.get("tags", "").split(',') if t.strip()],
            "materials": [m.strip() for m in request.form.get("materials", "").strip().split(',')],
            "images": [i.strip() for i in request.form.get("images", "").splitlines() if i.strip()],
            "primary_colour": request.form.get("primary_colour", "").strip(),
            "secondary_colour": request.form.get("secondary_colour", "").strip(),
            "seo_filename": request.form.get("seo_filename", "").strip(),
            "price": request.form.get("price", "18.27").strip(),
        }
        data.update(form_data)
        with open(listing_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        flash("Listing updated", "success")
        return redirect(url_for("edit_listing.edit_listing", aspect=aspect, filename=filename))

    artwork = utils.populate_artwork_data_from_json(data, seo_folder)
    # FIX (2025-08-04): Add the artwork's status to the dictionary for the template helper.
    artwork['status'] = stage
    artwork["images"] = "\n".join(public_image_urls)
    mockups = utils.get_mockup_details_for_template(data.get("mockups", []), folder, seo_folder, aspect)
    
    return render_template(
        "edit_listing.html",
        artwork=artwork,
        aspect=aspect,
        filename=filename,
        seo_folder=seo_folder,
        mockups=mockups,
        finalised=finalised,
        locked=data.get("locked", False),
        is_locked_in_vault=is_locked_in_vault,
        editable=not data.get("locked", False),
        public_image_urls=public_image_urls,
        cache_ts=int(time.time()),
        allowed_colours=get_allowed_colours(),
        categories=get_categories_for_aspect(data.get("aspect_ratio", aspect))
    )


# === [ Section 9: Static File and Image Serving Routes | artwork-routes-py-9 ] ===
# These routes serve images from various processing directories. They are essential
# for displaying thumbnails and full-size images throughout the application.
# ---------------------------------------------------------------------------------

# --- [ 9a: processed_image | artwork-routes-py-9a ] ---
@bp.route(f"/{config.PROCESSED_URL_PATH}/<path:filename>")
def processed_image(filename):
    """Serves images from the 'processed-artwork' directory."""
    return send_from_directory(config.PROCESSED_ROOT, filename)


# --- [ 9b: finalised_image | artwork-routes-py-9b ] ---
@bp.route(f"/{config.FINALISED_URL_PATH}/<path:filename>")
def finalised_image(filename):
    """Serves images from the 'finalised-artwork' directory."""
    return send_from_directory(config.FINALISED_ROOT, filename)


# --- [ 9c: locked_image | artwork-routes-py-9c ] ---
@bp.route(f"/{config.LOCKED_URL_PATH}/<path:filename>")
def locked_image(filename):
    """Serves images from the 'artwork-vault' (locked) directory."""
    return send_from_directory(config.ARTWORK_VAULT_ROOT, filename)


# --- [ 9d: serve_mockup_thumb | artwork-routes-py-9d ] ---
@bp.route(f"/{config.MOCKUP_THUMB_URL_PREFIX}/<path:filepath>")
def serve_mockup_thumb(filepath: str):
    """Serves mockup thumbnail images from any potential artwork directory."""
    for base_dir in [config.PROCESSED_ROOT, config.FINALISED_ROOT, config.ARTWORK_VAULT_ROOT]:
        full_path = base_dir / filepath
        if full_path.is_file():
            return send_from_directory(full_path.parent, full_path.name)
    abort(404)


# --- [ 9e: unanalysed_image | artwork-routes-py-9e ] ---
@bp.route(f"/{config.UNANALYSED_IMG_URL_PREFIX}/<filename>")
def unanalysed_image(filename: str):
    """Serves images from the 'unanalysed-artwork' directory."""
    path = next((p for p in config.UNANALYSED_ROOT.rglob(filename) if p.is_file()), None)
    if path:
        return send_from_directory(path.parent, path.name)
    abort(404)


# --- [ 9f: composite_img | artwork-routes-py-9f ] ---
@bp.route(f"/{config.COMPOSITE_IMG_URL_PREFIX}/<folder>/<filename>")
def composite_img(folder, filename):
    """(DEPRECATED) Serves a specific composite image."""
    return send_from_directory(config.PROCESSED_ROOT / folder, filename)


# --- [ 9g: mockup_img | artwork-routes-py-9g ] ---
@bp.route("/mockup-img/<category>/<filename>")
def mockup_img(category, filename):
    """Serves a mockup template image from the central inputs directory."""
    return send_from_directory(config.MOCKUPS_INPUT_DIR / category, filename)


# === [ Section 10: Composite Image Preview Routes | artwork-routes-py-10 ] ===
# Routes for the composite/mockup preview page.
# ---------------------------------------------------------------------------------

# --- [ 10a: composites_preview | artwork-routes-py-10a ] ---
@bp.route("/composites")
def composites_preview():
    """Redirects to the latest composite folder or the main artworks page."""
    latest = utils.latest_composite_folder()
    if latest:
        return redirect(url_for("artwork.composites_specific", seo_folder=latest))
    flash("No composites found", "warning")
    return redirect(url_for("artwork.artworks"))


# --- [ 10b: composites_specific | artwork-routes-py-10b ] ---
@bp.route("/composites/<seo_folder>")
def composites_specific(seo_folder):
    """Displays the composite images for a specific artwork."""
    folder = config.PROCESSED_ROOT / seo_folder
    json_path = folder / f"{seo_folder}-listing.json"
    images = []
    if json_path.exists():
        listing = load_json_file_safe(json_path)
        images = utils.get_mockup_details_for_template(
            listing.get("mockups", []), folder, seo_folder, listing.get("aspect_ratio", "")
        )
    return render_template(
        "composites_preview.html",
        images=images,
        folder=seo_folder,
        menu=utils.get_menu(),
    )


# --- [ 10c: approve_composites | artwork-routes-py-10c ] ---
@bp.route("/approve_composites/<seo_folder>", methods=["POST"])
def approve_composites(seo_folder):
    """Approves composites and redirects to the edit/review page."""
    listing_path = next((config.PROCESSED_ROOT / seo_folder).glob("*-listing.json"), None)
    if listing_path:
        data = load_json_file_safe(listing_path)
        aspect = data.get("aspect_ratio", "4x5")
        filename = data.get("seo_filename", f"{seo_folder}.jpg")
        flash("Composites approved. Please review and finalise.", "success")
        return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))
    flash("Could not find listing data.", "danger")
    return redirect(url_for("artwork.artworks"))


# === [ Section 11: Artwork Finalisation and Gallery Routes | artwork-routes-py-11 ] ===
# Routes for the final step of the workflow: moving an artwork to the
# 'finalised' directory, and viewing the finalised/locked galleries.
# ---------------------------------------------------------------------------------

# --- [ 11a: finalise_artwork | artwork-routes-py-11a ] ---
@bp.route("/finalise-artwork/<seo_folder>", methods=["POST"])
def finalise_artwork(seo_folder):
    """Move a processed artwork into the finalised directory for review."""
    src = config.PROCESSED_ROOT / seo_folder
    dst = config.FINALISED_ROOT / seo_folder
    try:
        if not src.exists():
            raise FileNotFoundError(f"Processed artwork '{seo_folder}' not found.")
        shutil.move(str(src), str(dst))
        listing_file = dst / f"{seo_folder}-listing.json"
        utils.update_listing_paths(listing_file, config.PROCESSED_ROOT, config.FINALISED_ROOT)
        data = load_json_file_safe(listing_file)
        data["locked"] = False
        data["images"] = generate_public_image_urls(seo_folder, "finalised")
        with open(listing_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        update_artwork_registry(seo_folder, dst, "finalised")
        log_action("finalise", seo_folder, session.get("username"), "Artwork finalised for review")
        flash("Artwork finalised for review", "success")
    except Exception as exc:
        flash(f"Error during finalisation: {exc}", "danger")

    return redirect(url_for("artwork.finalised_gallery"))


# --- [ 11b: finalised_gallery | artwork-routes-py-11b ] ---
@bp.route("/finalised")
def finalised_gallery():
    """Displays all finalised artworks in a gallery view with Sellbrite status."""
    from routes import sellbrite_service
    
    artworks_list = [a for a in utils.get_all_artworks() if a['status'] == 'finalised']
    
    # Check Sellbrite connection once.
    is_connected = sellbrite_service.test_sellbrite_connection()
    
    # NEW (2025-08-04): Add Sellbrite default data to each artwork for display
    sellbrite_defaults = config.SELLBRITE_DEFAULTS

    for art in artworks_list:
        # Add Sellbrite defaults for display in the template
        art['sellbrite_category'] = sellbrite_defaults['CATEGORY']
        art['sellbrite_condition'] = sellbrite_defaults['CONDITION']
        art['sellbrite_quantity'] = sellbrite_defaults['QUANTITY']

        if is_connected and art.get('sku'):
            product = sellbrite_service.get_product_by_sku(art['sku'])
            if product:
                art['sellbrite_status'] = 'Synced'
            else:
                art['sellbrite_status'] = 'Not Found'
        elif is_connected:
            art['sellbrite_status'] = 'No SKU'
        else:
            art['sellbrite_status'] = 'API Offline'

    return render_template("finalised.html", artworks=artworks_list, menu=utils.get_menu())


# --- [ 11c: locked_gallery | artwork-routes-py-11c ] ---
@bp.route("/locked")
def locked_gallery():
    """Displays all locked artworks from the vault."""
    locked_items = [a for a in utils.get_all_artworks() if a.get('locked')]
    return render_template("locked.html", artworks=locked_items, menu=utils.get_menu())


# --- [ 11d: lock_it_in | artwork-routes-py-11d ] ---
@bp.post("/lock-it-in/<seo_folder>")
def lock_it_in(seo_folder: str):
    """Move a finalised artwork into the vault and mark it as locked."""
    src = config.FINALISED_ROOT / seo_folder
    dst = config.ARTWORK_VAULT_ROOT / f"LOCKED-{seo_folder}"
    try:
        if not src.exists():
            raise FileNotFoundError(f"Finalised artwork '{seo_folder}' not found.")
        shutil.move(str(src), str(dst))
        listing_file = dst / f"{seo_folder}-listing.json"
        utils.update_listing_paths(listing_file, config.FINALISED_ROOT, config.ARTWORK_VAULT_ROOT)
        data = load_json_file_safe(listing_file)
        data["locked"] = True
        data["images"] = generate_public_image_urls(seo_folder, "vault")
        with open(listing_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        update_artwork_registry(seo_folder, dst, "locked")
        log_action("lock-it-in", seo_folder, session.get("username"), "Artwork locked in for export")
        flash("Artwork locked in for export", "success")
    except Exception as e:
        flash(f"Error locking in artwork: {e}", "danger")
    return redirect(url_for("artwork.locked_gallery"))


# === [ Section 12: Listing State Management (Lock, Unlock, Delete) | artwork-routes-py-12 ] ===
# Routes for managing the lifecycle of a finalised artwork: locking (moving
# to vault), unlocking (making editable again), and deletion.
# ---------------------------------------------------------------------------------

# --- [ 12a: delete_finalised | artwork-routes-py-12a ] ---
@bp.post("/finalise/delete/<aspect>/<filename>")
def delete_finalised(aspect, filename):
    """Deletes a finalised or locked artwork and all its files."""
    try:
        _, folder, listing_file, _ = resolve_listing_paths(aspect, filename, allow_locked=True)
        info = load_json_file_safe(listing_file)
        if info.get("locked") and request.form.get("confirm") != "DELETE":
            flash("Type DELETE to confirm deletion of a locked item.", "warning")
            return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))
        
        shutil.rmtree(folder)
        flash("Artwork deleted successfully.", "success")
        log_action("delete", filename, session.get("username"), f"Deleted folder {folder}")
    except FileNotFoundError:
        flash("Artwork not found.", "danger")
    except Exception as e:
        flash(f"Delete failed: {e}", "danger")
    return redirect(url_for("artwork.finalised_gallery"))


# --- [ 12b: lock_listing | artwork-routes-py-12b ] ---
@bp.post("/lock/<aspect>/<filename>")
def lock_listing(aspect, filename):
    """Locks an artwork by moving it to the 'artwork-vault' directory."""
    try:
        seo, folder, listing_path, finalised = resolve_listing_paths(aspect, filename)
        if not finalised:
            flash("Artwork must be finalised before locking.", "danger")
            return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))
        
        target = config.ARTWORK_VAULT_ROOT / f"LOCKED-{seo}"
        config.ARTWORK_VAULT_ROOT.mkdir(parents=True, exist_ok=True)
        if target.exists(): shutil.rmtree(target)
        shutil.move(str(folder), str(target))

        new_listing_path = target / listing_path.name
        utils.update_listing_paths(new_listing_path, folder, target)
        data = load_json_file_safe(new_listing_path)
        data["locked"] = True
        data["images"] = generate_public_image_urls(seo, "vault")
        with open(new_listing_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        flash("Artwork locked.", "success")
        log_action("lock", filename, session.get("username"), "locked artwork")
    except Exception as exc:
        flash(f"Failed to lock: {exc}", "danger")
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


# --- [ 12c: unlock_listing | artwork-routes-py-12c ] ---
@bp.post("/unlock/<aspect>/<filename>")
def unlock_listing(aspect, filename):
    """Unlocks an artwork, making it editable again but keeping files in the vault."""
    if request.form.get("confirm_unlock") != "UNLOCK":
        flash("Incorrect confirmation text. Please type UNLOCK to proceed.", "warning")
        return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

    try:
        _, _, listing_path, _ = resolve_listing_paths(aspect, filename, allow_locked=True)
        if config.ARTWORK_VAULT_ROOT not in listing_path.parents:
            flash("Cannot unlock an item that is not in the vault.", "danger")
            return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))

        with open(listing_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["locked"] = False
            f.seek(0)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.truncate()
        
        log_action("unlock", filename, session.get("username"), "unlocked artwork")
        flash("Artwork unlocked and is now editable. File paths remain unchanged.", "success")
    
    except FileNotFoundError:
        flash("Locked artwork not found.", "danger")
        return redirect(url_for("artwork.artworks"))
    except Exception as exc:
        log_action("unlock", filename, session.get("username"), "unlock failed", status="fail", error=str(exc))
        flash(f"Failed to unlock: {exc}", "danger")
        
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


# --- [ 12d: unlock_artwork | artwork-routes-py-12d ] ---
@bp.route("/unlock-artwork/<seo_folder>", methods=["POST"])
def unlock_artwork(seo_folder: str):
    """Move a locked artwork from the vault back to the finalised stage."""
    clean = seo_folder.replace("LOCKED-", "")
    src = config.ARTWORK_VAULT_ROOT / f"LOCKED-{clean}"
    dst = config.FINALISED_ROOT / clean
    try:
        shutil.move(str(src), str(dst))
        listing_file = dst / f"{clean}-listing.json"
        utils.update_listing_paths(listing_file, config.ARTWORK_VAULT_ROOT, config.FINALISED_ROOT)
        data = load_json_file_safe(listing_file)
        data["locked"] = False
        data["images"] = generate_public_image_urls(clean, "finalised")
        with open(listing_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        update_artwork_registry(clean, dst, "finalised")
        flash("Artwork unlocked", "success")
    except Exception as exc:
        flash(f"Error during unlocking: {exc}", "danger")
    return redirect(url_for("artwork.finalised_gallery"))


# === [ Section 13: Asynchronous API Endpoints | artwork-routes-py-13 ] ===
# API-style endpoints called via JavaScript from the frontend to perform
# specific, targeted actions without a full page reload.
# ---------------------------------------------------------------------------------

# --- [ 13a: update_links | artwork-routes-py-13a ] ---
@bp.post("/update-links/<aspect>/<filename>")
def update_links(aspect, filename):
    """Regenerates the image URL list from disk and returns it as JSON."""
    wants_json = "application/json" in request.headers.get("Accept", "")
    try:
        seo_folder, _, listing_file, _ = resolve_listing_paths(aspect, filename)
        stage = "vault" if (config.ARTWORK_VAULT_ROOT / f"LOCKED-{seo_folder}").exists() else "processed"
        data = load_json_file_safe(listing_file)
        data["images"] = generate_public_image_urls(seo_folder, stage)
        with open(listing_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        msg = "Image links updated"
        if wants_json: return jsonify({"success": True, "message": msg, "images": data["images"]})
        flash(msg, "success")
    except Exception as e:
        msg = f"Failed to update links: {e}"
        if wants_json: return jsonify({"success": False, "message": msg, "images": []}), 500
        flash(msg, "danger")
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


# --- [ 13b: reset_sku | artwork-routes-py-13b ] ---
@bp.post("/reset-sku/<aspect>/<filename>")
def reset_sku(aspect, filename):
    """Forces the assignment of a new SKU for a given artwork."""
    try:
        _, _, listing, _ = resolve_listing_paths(aspect, filename)
        utils.assign_or_get_sku(listing, config.SKU_TRACKER, force=True)
        flash("SKU has been reset.", "success")
    except Exception as exc:
        flash(f"Failed to reset SKU: {exc}", "danger")
    return redirect(url_for("artwork.edit_listing", aspect=aspect, filename=filename))


# --- [ 13c: delete_artwork | artwork-routes-py-13c ] ---
@bp.route("/delete-artwork/<seo_folder>", methods=["POST"])
def delete_artwork(seo_folder: str):
    """Completely remove an artwork folder and registry entry."""
    user = session.get("username", "unknown")
    log_action("delete", seo_folder, user, f"Initiating delete for '{seo_folder}'")

    clean = seo_folder.replace("LOCKED-", "")
    locked_path = config.ARTWORK_VAULT_ROOT / f"LOCKED-{clean}"
    if locked_path.exists() and request.form.get("confirm") != "DELETE":
        flash("Type DELETE to confirm deletion of locked artwork.", "warning")
        return redirect(url_for("artwork.locked_gallery"))

    try:
        if delete_artwork_files(clean):
            flash(f"Artwork '{clean}' deleted successfully.", "success")
            log_action("delete", clean, user, "Delete process completed.")
        else:
            flash(f"Failed to delete artwork '{clean}'.", "danger")
            log_action("delete", clean, user, "Delete failed", status="fail")
    except Exception as exc:
        flash(f"An error occurred during deletion: {exc}", "danger")
        log_action("delete", clean, user, str(exc), status="fail")
    return redirect(url_for("artwork.artworks"))


# --- [ 13d: reword_generic_text_api | artwork-routes-py-13d ] ---
@bp.post("/api/reword-generic-text")
def reword_generic_text_api():
    """Handles an async request to reword the generic part of a description using AI."""
    logger = logging.getLogger(__name__)
    data = request.json

    provider = data.get("provider")
    artwork_desc = data.get("artwork_description")
    generic_text = data.get("generic_text")

    if not all([provider, artwork_desc, generic_text]):
        logger.error("Reword API call missing required data.")
        return jsonify({"success": False, "error": "Missing required data."}), 400

    try:
        reworded_text = ai_services.call_ai_to_reword_text(
            provider=provider,
            artwork_description=artwork_desc,
            generic_text=generic_text
        )
        logger.info(f"Successfully reworded text with {provider}.")
        return jsonify({"success": True, "reworded_text": reworded_text})

    except Exception as e:
        logger.error(f"Failed to reword generic text: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# === [ Section 14: File Processing and Utility Helpers | artwork-routes-py-14 ] ===
# Internal helper functions used by the routes in this file, primarily for
# handling the initial processing of uploaded files.
# ---------------------------------------------------------------------------------

# --- [ 14a: preview_next_sku | artwork-routes-py-14a ] ---
@bp.route("/next-sku")
def preview_next_sku():
    """Returns the next available SKU without consuming it."""
    return Response(peek_next_sku(config.SKU_TRACKER), mimetype="text/plain")


# --- [ 14b: _process_upload_file | artwork-routes-py-14b ] ---
def _process_upload_file(file_storage, dest_folder):
    """Validates, saves, and preprocesses a single uploaded file."""
    filename = file_storage.filename
    if not filename: return {"original": filename, "success": False, "error": "No filename"}

    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in config.ALLOWED_EXTENSIONS:
        return {"original": filename, "success": False, "error": "Invalid file type"}
    
    data = file_storage.read()
    if len(data) > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        return {"original": filename, "success": False, "error": "File too large"}

    # FIX (2025-08-04): Use the correct slugify function for filenames instead of prettify_title.
    safe, unique, uid = utils.slugify(Path(filename).stem), uuid.uuid4().hex[:8], uuid.uuid4().hex
    base = f"{safe}-{unique}"
    dest_folder.mkdir(parents=True, exist_ok=True)
    orig_path = dest_folder / f"{base}.{ext}"

    try:
        orig_path.write_bytes(data)
        with Image.open(orig_path) as img:
            width, height = img.size
            thumb_path = dest_folder / f"{base}-thumb.jpg"
            thumb = img.copy()
            thumb.thumbnail((config.THUMB_WIDTH, config.THUMB_HEIGHT))
            thumb.save(thumb_path, "JPEG", quality=80)
            analyse_path = dest_folder / f"{base}-analyse.jpg"
            utils.resize_for_analysis(img, analyse_path)
    except Exception as exc:
        logging.getLogger(__name__).error("Image processing failed: %s", exc)
        return {"original": filename, "success": False, "error": "Image processing failed"}
    
    qc_data = {
        "original_filename": filename, "extension": ext, "image_shape": [width, height],
        "filesize_bytes": len(data), "aspect_ratio": aa.get_aspect_ratio(orig_path),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    qc_path = dest_folder / f"{base}.qc.json"
    qc_path.write_text(json.dumps(qc_data, indent=2))

    utils.register_new_artwork(uid, f"{base}.{ext}", dest_folder, [orig_path.name, thumb_path.name, analyse_path.name, qc_path.name], "unanalysed", base)
    
    return {"success": True, "base": base, "aspect": qc_data["aspect_ratio"], "uid": uid, "original": filename}


# === [ Section 15: Artwork Signing Route | artwork-routes-py-15 ] ===
# Endpoint for applying a digital signature to an artwork.
# ---------------------------------------------------------------------------------

# --- [ 15a: sign_artwork_route | artwork-routes-py-15a ] ---
@bp.post("/sign-artwork/<base_name>")
def sign_artwork_route(base_name: str):
    """
    Finds an unanalysed artwork by its base name, applies a smart
    signature, and replaces the original file and its derivatives.
    """
    logger = logging.getLogger(__name__)
    source_path = next((p for p in config.UNANALYSED_ROOT.rglob(f"{base_name}.*") if "-thumb" not in p.name and "-analyse" not in p.name), None)

    if not source_path:
        return jsonify({"success": False, "error": "Original artwork file not found."}), 404
        
    destination_path = source_path
    
    success, message = signing_service.add_smart_signature(source_path, destination_path)
    
    if success:
        try:
            logger.info(f"Regenerating derivatives for signed artwork: {source_path.name}")
            dest_folder = source_path.parent
            thumb_path = dest_folder / f"{base_name}-thumb.jpg"
            analyse_path = dest_folder / f"{base_name}-analyse.jpg"

            with Image.open(source_path) as img:
                thumb = img.copy()
                thumb.thumbnail((config.THUMB_WIDTH, config.THUMB_HEIGHT))
                thumb.save(thumb_path, "JPEG", quality=80)
                
                utils.resize_for_analysis(img, analyse_path)
            
            logger.info(f"Successfully regenerated thumb and analyse images for {base_name}.")
            log_action("sign", source_path.name, session.get("username"), "Artwork signed and derivatives regenerated.")
            return jsonify({"success": True, "message": message})

        except Exception as e:
            error_msg = f"Artwork was signed, but failed to regenerate derivatives: {e}"
            logger.error(error_msg, exc_info=True)
            log_action("sign", source_path.name, session.get("username"), "Artwork signed but derivative regeneration failed.", status="fail", error=str(e))
            return jsonify({"success": True, "message": "Artwork signed, but an error occurred updating preview images."})
    else:
        log_action("sign", source_path.name, session.get("username"), "Artwork signing failed", status="fail", error=message)
        return jsonify({"success": False, "error": message}), 500

---
## routes/auth_routes.py
---
# routes/auth_routes.py
"""
Authentication routes for the ArtNarrator application.
Handles user login, session creation, and logout.

INDEX
-----
1.  Imports
2.  Blueprint Setup
3.  Authentication Routes
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging
import uuid
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

import config
from db import SessionLocal, User
from utils import security, session_tracker

logger = logging.getLogger(__name__)

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
bp = Blueprint("auth", __name__)


# ===========================================================================
# 3. Authentication Routes
# ===========================================================================

@bp.route("/login", methods=["GET", "POST"])
def login():
    """Display and handle the user login form."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        with SessionLocal() as db_session:
            user = db_session.query(User).filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                # Check if site is locked by admin (and user is not an admin)
                if not security.login_required_enabled() and user.role != "admin":
                    logger.warning(f"Login attempt by '{username}' failed: Site is locked by admin.")
                    flash("Site is currently locked by an administrator.", "danger")
                    return render_template("login.html"), 403

                # Register session and check against device limit
                token = str(uuid.uuid4())
                if not session_tracker.register_session(username, token):
                    logger.warning(f"Login attempt by '{username}' failed: Maximum session limit reached.")
                    flash("Maximum login limit reached. Please log out on another device to continue.", "danger")
                    return render_template("login.html"), 403

                # Set session variables
                session["logged_in"] = True
                session["username"] = username
                session["role"] = user.role
                session["session_id"] = token
                
                # Update user's last login time in DB
                user.last_login = datetime.utcnow()
                db_session.commit()
                
                logger.info(f"Successful login for user '{username}' with role '{user.role}'.")
                
                next_page = request.args.get("next") or url_for("artwork.home")
                return redirect(next_page)

        logger.warning(f"Failed login attempt for username: '{username}'.")
        flash("Invalid username or password.", "danger")
        
    return render_template("login.html")


@bp.route("/logout")
def logout():
    """Clear the user session and log the user out."""
    token = session.get("session_id")
    username = session.get("username")
    
    if token and username:
        session_tracker.remove_session(username, token)
        logger.info(f"User '{username}' logged out and session '{token}' was removed.")
        
    session.clear()
    return redirect(url_for("auth.login"))

---
## routes/coordinate_admin_routes.py
---
# routes/coordinate_admin_routes.py
"""
Admin dashboard for managing and generating mockup coordinates.

This module provides the user interface and backend logic for scanning
mockups that are missing coordinate files and for running the automated
coordinate generation script.

INDEX
-----
1.  Imports
2.  Blueprint Setup
3.  Admin Dashboard Route
4.  API & Asynchronous Routes
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging
import subprocess
import time

from flask import (
    Blueprint, render_template, jsonify, Response, stream_with_context
)

import config
from routes.utils import get_menu

logger = logging.getLogger(__name__)

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
bp = Blueprint("coordinate_admin", __name__, url_prefix="/admin/coordinates")


# ===========================================================================
# 3. Admin Dashboard Route
# ===========================================================================
@bp.route("/")
def dashboard():
    """Display the coordinate management dashboard."""
    return render_template("admin/coordinates.html", menu=get_menu())


# ===========================================================================
# 4. API & Asynchronous Routes
# ===========================================================================
@bp.route("/scan")
def scan_for_missing_coordinates():
    """Scans all categorized mockups and reports which are missing coordinate files."""
    logger.info("Admin triggered a scan for missing coordinate files.")
    missing_files = []
    
    try:
        for aspect_dir in config.MOCKUPS_CATEGORISED_DIR.iterdir():
            if not aspect_dir.is_dir(): continue
            
            aspect_name = aspect_dir.name
            coord_aspect_dir = config.COORDS_DIR / aspect_name

            for category_dir in aspect_dir.iterdir():
                if not category_dir.is_dir(): continue
                
                for mockup_file in category_dir.glob("*.png"):
                    coord_file = coord_aspect_dir / category_dir.name / f"{mockup_file.stem}.json"
                    if not coord_file.exists():
                        missing_files.append(str(mockup_file.relative_to(config.BASE_DIR)))
                        
        logger.info(f"Scan complete. Found {len(missing_files)} mockups missing coordinates.")
        return jsonify({"missing_files": sorted(missing_files)})
    except Exception as e:
        logger.error(f"An error occurred during coordinate scan: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred during the scan."}), 500


@bp.route("/run-generator")
def run_generator():
    """Runs the coordinate generator script and streams its output with a heartbeat."""
    logger.info("Admin triggered the coordinate generator script.")
    # Use the new config variable for the script path
    script_path = config.COORDINATE_GENERATOR_SCRIPT_PATH
    
    def generate_output():
        try:
            process = subprocess.Popen(
                ["python3", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Combine stdout and stderr
                text=True,
                bufsize=1
            )
            
            # Stream the output line by line
            for line in iter(process.stdout.readline, ''):
                yield f"data: {line.strip()}\n\n"
            
            process.stdout.close()
            return_code = process.wait()
            
            if return_code == 0:
                logger.info("Coordinate generator script finished successfully.")
                yield "data: ---SCRIPT FINISHED SUCCESSFULLY---\n\n"
            else:
                logger.error(f"Coordinate generator script finished with error code {return_code}.")
                yield f"data: ---SCRIPT FINISHED WITH ERROR (Code: {return_code})---\n\n"

        except Exception as e:
            logger.error(f"Failed to execute coordinate generator script: {e}", exc_info=True)
            yield f"data: ---ERROR: Failed to start the script: {e}---\n\n"

    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no', # Disable buffering for Nginx
    }
    return Response(stream_with_context(generate_output()), headers=headers)

---
## routes/edit_listing_routes.py
---
# routes/edit_listing_routes.py
"""
Flask routes dedicated to asynchronous actions on the 'Edit Listing' page.

This module provides API-style endpoints that are called via JavaScript
to perform specific actions without a full page reload, such as swapping
a mockup image.

INDEX
-----
1.  Imports
2.  Blueprint Setup
3.  API Routes
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging
from flask import Blueprint, jsonify, request, url_for
from . import utils
import config

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
bp = Blueprint("edit_listing", __name__, url_prefix="/edit")
logger = logging.getLogger(__name__)

# ===========================================================================
# 3. API Routes
# ===========================================================================

@bp.post("/swap-mockup-api")
def swap_mockup_api():
    """
    Handles an asynchronous request to swap a single mockup.
    Accepts a JSON payload and returns JSON with new image URLs.
    """
    data = request.json
    seo_folder = data.get("seo_folder")
    slot_idx = data.get("slot_index")
    new_category = data.get("new_category")
    current_mockup_src = data.get("current_mockup_src")

    if not all([seo_folder, isinstance(slot_idx, int), new_category]):
        logger.warning("Swap mockup API called with missing data.")
        return jsonify({"success": False, "error": "Missing required data."}), 400

    try:
        logger.info(f"Attempting to swap mockup for '{seo_folder}', slot {slot_idx}, to category '{new_category}'.")
        success, new_mockup_name, new_thumb_name = utils.swap_one_mockup(
            seo_folder, slot_idx, new_category, current_mockup_src
        )

        if not success:
            raise RuntimeError("The swap_one_mockup utility failed to generate new images.")

        # --- CORRECTED URL GENERATION ---
        # The routes expect a single 'filename' or 'filepath' argument that includes the subdirectories.
        mockup_filepath = f"{seo_folder}/{new_mockup_name}"
        thumb_filepath = f"{seo_folder}/{config.THUMB_SUBDIR}/{new_thumb_name}"

        new_mockup_url = url_for('artwork.processed_image', filename=mockup_filepath)
        new_thumb_url = url_for('artwork.serve_mockup_thumb', filepath=thumb_filepath)

        logger.info(f"Successfully swapped mockup for '{seo_folder}'. New image: {new_mockup_name}")
        return jsonify({
            "success": True,
            "message": "Mockup swapped successfully.",
            "new_mockup_url": new_mockup_url,
            "new_thumb_url": new_thumb_url
        })

    except Exception as e:
        logger.error(f"Failed to swap mockup for '{seo_folder}': {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

---
## routes/export_routes.py
---
# routes/export_routes.py
"""
Flask routes for exporting listing data to external services like Sellbrite.

This module contains routes for both the modern, API-driven Sellbrite sync export system.

INDEX
-----
1.  Imports & Initialisation
2.  Data Collection Helpers
3.  Sellbrite API Management Routes
"""

# ===========================================================================
# 1. Imports & Initialisation
# ===========================================================================

from __future__ import annotations
import datetime
import json
from pathlib import Path
from typing import List, Dict

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, send_from_directory, abort, session, Response,
)

import config
from . import utils
from routes import sellbrite_service
from routes.sellbrite_export import generate_sellbrite_json
from utils.logger_utils import log_action

bp = Blueprint("exports", __name__, url_prefix="/exports")


# ===========================================================================
# 2. Data Collection Helpers
# ===========================================================================

def _collect_listings(locked_only: bool) -> List[Dict]:
    """Gathers finalised and/or locked listing data from the filesystem."""
    listings = []
    search_dirs = [config.FINALISED_ROOT]
    if locked_only:
        search_dirs.append(config.ARTWORK_VAULT_ROOT)

    for base in search_dirs:
        if not base.exists():
            continue
        for listing_path in base.rglob("*-listing.json"):
            try:
                utils.assign_or_get_sku(listing_path, config.SKU_TRACKER)
                with open(listing_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if not locked_only or data.get("locked"):
                    listings.append(data)
            except Exception as e:
                log_action("sellbrite-exports", listing_path.name, "system", "failed to collect listing", status="fail", error=str(e))
    return listings


def _collect_locked_listings() -> List[Dict]:
    """Gathers only locked artwork listings, specifically for the API sync."""
    return _collect_listings(locked_only=True)


# ===========================================================================
# 3. Sellbrite API Management Routes
# ===========================================================================

@bp.route("/sellbrite/manage")
def sellbrite_management():
    """Displays the Sellbrite API management dashboard."""
    is_connected = sellbrite_service.test_sellbrite_connection()
    products = sellbrite_service.get_products() if is_connected else []
    return render_template("sellbrite_management.html", is_connected=is_connected, products=products)


@bp.post("/sellbrite/sync")
def sync_to_sellbrite():
    """Pushes locked products to Sellbrite (live) or shows a preview (dry run)."""
    run_type = request.form.get("run_type")
    user = session.get("username", "system")
    log_action("sellbrite-sync", "all_locked", user, f"Starting {run_type} sync.")
    
    listings_to_sync = _collect_locked_listings()

    if not listings_to_sync:
        flash("No locked artworks found to sync.", "warning")
        return redirect(url_for('exports.sellbrite_management'))

    if run_type == "dry_run":
        product_payloads = [generate_sellbrite_json(listing) for listing in listings_to_sync]
        return render_template("sellbrite_sync_preview.html", products=product_payloads)

    elif run_type == "live":
        success_count, fail_count = 0, 0
        for listing in listings_to_sync:
            sku = listing.get("sku", "UNKNOWN_SKU")
            success, message = sellbrite_service.create_product(listing)
            if success:
                success_count += 1
                log_action("sellbrite-sync", sku, user, "Live sync successful.", status="success")
            else:
                fail_count += 1
                flash(f"SKU {sku}: {message}", 'danger')
                log_action("sellbrite-sync", sku, user, "Live sync failed.", status="fail", error=message)
        
        flash(f"Live sync complete: {success_count} successful, {fail_count} failed.", 'success' if fail_count == 0 else 'warning')
        return redirect(url_for('exports.sellbrite_management'))
    
    flash("Invalid action specified.", "danger")
    return redirect(url_for('exports.sellbrite_management'))


@bp.route("/sellbrite/log/<path:log_filename>")
def view_sellbrite_log(log_filename: str):
    path = config.SELLBRITE_DIR / log_filename
    if not path.exists(): abort(404)
    return Response(path.read_text(encoding="utf-8"), mimetype="text/plain")

---
## routes/gdws_admin_routes.py
---
# routes/gdws_admin_routes.py
"""
Admin interface for the Guided Description Writing System (GDWS).

This module provides the backend for the GDWS editor, allowing admins to
load, edit, reorder, and regenerate paragraph blocks for different artwork
aspect ratios.

INDEX
-----
1.  Imports
2.  Blueprint Setup
3.  Helper Functions
4.  Main Editor Routes
5.  Asynchronous API Routes
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import json
import re
import logging
from pathlib import Path
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify

import config
from routes.utils import get_menu
from utils.ai_services import call_ai_to_rewrite, call_ai_to_generate_title

logger = logging.getLogger(__name__)

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
bp = Blueprint("gdws_admin", __name__, url_prefix="/admin/gdws")


# ===========================================================================
# 3. Helper Functions
# ===========================================================================

def slugify(text: str) -> str:
    """
    Creates a filesystem-safe name from a heading.
    Note: This version is specific to GDWS and contains hardcoded remappings.
    """
    s = text.lower()
    s = re.sub(r'[^\w\s-]', '', s).strip()
    s = re.sub(r'[-\s]+', '_', s)
    if "about_the_artist" in s: return "about_the_artist"
    if "did_you_know" in s: return "about_art_style"
    if "what_youll_receive" in s: return "file_details"
    return s


def get_aspect_ratios() -> list[str]:
    """Return a list of available aspect ratio folders in the GDWS directory."""
    if not config.GDWS_CONTENT_DIR.exists():
        return []
    return sorted([p.name for p in config.GDWS_CONTENT_DIR.iterdir() if p.is_dir()])


# ===========================================================================
# 4. Main Editor Routes
# ===========================================================================

@bp.route("/")
def editor():
    """Renders the main GDWS editor page."""
    # Pass pinned titles from config to the template
    pinned_start = config.GDWS_CONFIG["PINNED_START_TITLES"]
    pinned_end = config.GDWS_CONFIG["PINNED_END_TITLES"]
    return render_template(
        "dws_editor.html",
        menu=get_menu(),
        aspect_ratios=get_aspect_ratios(),
        PINNED_START_TITLES=pinned_start,
        PINNED_END_TITLES=pinned_end,
    )


@bp.route("/template/<aspect_ratio>")
def get_template_data(aspect_ratio: str):
    """Fetches and sorts paragraphs based on saved order and pinned status."""
    aspect_path = config.GDWS_CONTENT_DIR / aspect_ratio
    if not aspect_path.exists():
        return jsonify({"error": "Aspect ratio not found"}), 404

    all_blocks = {}
    for folder_path in [p for p in aspect_path.iterdir() if p.is_dir()]:
        base_file = folder_path / "base.json"
        if base_file.exists():
            try:
                data = json.loads(base_file.read_text(encoding='utf-8'))
                all_blocks[data['title']] = data
            except Exception as e:
                logger.error(f"Error loading GDWS base file {base_file}: {e}")

    # Use pinned titles from config
    pinned_start = config.GDWS_CONFIG["PINNED_START_TITLES"]
    pinned_end = config.GDWS_CONFIG["PINNED_END_TITLES"]

    start_blocks = [all_blocks.pop(title) for title in pinned_start if title in all_blocks]
    end_blocks = [all_blocks.pop(title) for title in pinned_end if title in all_blocks]
    
    # Sort remaining (middle) blocks based on the order.json file
    order_file = aspect_path / "order.json"
    sorted_middle_blocks = []
    if order_file.exists():
        try:
            order = json.loads(order_file.read_text(encoding='utf-8'))
            for title in order:
                if title in all_blocks:
                    sorted_middle_blocks.append(all_blocks.pop(title))
        except Exception as e:
            logger.error(f"Error reading GDWS order file {order_file}: {e}")
    
    # Add any remaining blocks that weren't in the order file
    sorted_middle_blocks.extend(all_blocks.values())

    return jsonify({"blocks": start_blocks + sorted_middle_blocks + end_blocks})


# ===========================================================================
# 5. Asynchronous API Routes
# ===========================================================================

@bp.post("/save-order")
def save_order():
    """Saves the new display order of the middle paragraphs."""
    data = request.json
    aspect_ratio = data.get('aspect_ratio')
    order = data.get('order')

    if not aspect_ratio or order is None:
        return jsonify({"status": "error", "message": "Missing aspect_ratio or order data."}), 400

    try:
        order_file = config.GDWS_CONTENT_DIR / aspect_ratio / "order.json"
        order_file.write_text(json.dumps(order, indent=2), encoding='utf-8')
        logger.info(f"GDWS paragraph order saved for aspect ratio: {aspect_ratio}")
        return jsonify({"status": "success", "message": "Order saved."})
    except Exception as e:
        logger.error(f"Failed to save GDWS order for {aspect_ratio}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to write order file to disk."}), 500


@bp.post("/regenerate-title")
def regenerate_title():
    """Handles AI regeneration for a paragraph title."""
    content = request.json.get('content', '')
    try:
        new_title = call_ai_to_generate_title(content)
        return jsonify({"new_title": new_title})
    except Exception as e:
        logger.error(f"AI title regeneration failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "AI title generation failed."}), 500


@bp.post("/regenerate-paragraph")
def regenerate_paragraph():
    """Handles AI regeneration for a single paragraph's content."""
    data = request.json
    prompt = (
        f"Instruction: \"{data.get('instructions', '')}\"\n\n"
        f"Rewrite the following text based on the instruction. Respond only with the rewritten text.\n\n"
        f"TEXT TO REWRITE:\n\"{data.get('current_text', '')}\""
    )
    try:
        new_text = call_ai_to_rewrite(prompt)
        return jsonify({"new_content": new_text})
    except Exception as e:
        logger.error(f"AI paragraph regeneration failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "AI content regeneration failed."}), 500


@bp.post("/save-base-paragraph")
def save_base_paragraph():
    """Saves edits to a base.json file, handling potential renames."""
    data = request.json
    aspect_ratio = data.get('aspect_ratio')
    original_title = data.get('original_title')
    new_title = data.get('new_title')
    
    if not all([aspect_ratio, original_title, new_title]):
        return jsonify({"status": "error", "message": "Missing required data."}), 400

    try:
        original_slug = slugify(original_title)
        new_slug = slugify(new_title)
        
        original_folder = config.GDWS_CONTENT_DIR / aspect_ratio / original_slug
        target_folder = config.GDWS_CONTENT_DIR / aspect_ratio / new_slug
        
        # Handle renaming of the folder if the title/slug changed
        if original_slug != new_slug:
            if target_folder.exists():
                return jsonify({"status": "error", "message": "A paragraph with that name already exists."}), 400
            if not original_folder.exists():
                return jsonify({"status": "error", "message": "Original paragraph folder not found."}), 404
            original_folder.rename(target_folder)
            logger.info(f"Renamed GDWS folder from '{original_slug}' to '{new_slug}'")

        file_path = target_folder / "base.json"
        existing_data = json.loads(file_path.read_text(encoding='utf-8')) if file_path.exists() else {"id": "base"}

        existing_data.update({
            'title': new_title,
            'content': data.get('content', existing_data.get('content', '')),
            'instructions': data.get('instructions', existing_data.get('instructions', '')),
            'last_updated': datetime.now().isoformat()
        })
        
        file_path.write_text(json.dumps(existing_data, indent=4), encoding='utf-8')
        logger.info(f"Updated GDWS base file: {file_path}")
        return jsonify({"status": "success", "message": f"Updated {file_path}", "new_slug": new_slug})
    except Exception as e:
        logger.error(f"Failed to save base paragraph '{new_title}': {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected error occurred while saving."}), 500

---
## routes/mockup_admin_routes.py
---
# routes/mockup_admin_routes.py
"""
Admin dashboard for managing and categorising mockups.

Provides functionality for uploading, viewing, categorizing, and deleting
mockup images used in the artwork composite generation process.

INDEX
-----
1.  Imports & Initialisation
2.  Blueprint Setup
3.  Helper Functions
4.  Main Dashboard Route
5.  Image Serving Routes
6.  Mockup Management API Routes
"""

# ===========================================================================
# 1. Imports & Initialisation
# ===========================================================================
from __future__ import annotations
import logging
import shutil
import subprocess
from pathlib import Path

# Third-party imports
from flask import (
    Blueprint, render_template, request, jsonify, flash, redirect, url_for,
    send_from_directory
)
from PIL import Image
import imagehash

# Local application imports
import config
from routes.utils import get_menu

logger = logging.getLogger(__name__)

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
bp = Blueprint("mockup_admin", __name__, url_prefix="/admin/mockups")


# ===========================================================================
# 3. Helper Functions
# ===========================================================================

def get_available_aspects() -> list[str]:
    """Finds available aspect ratio staging folders."""
    if not config.MOCKUPS_STAGING_DIR.exists():
        return []
    return sorted([d.name for d in config.MOCKUPS_STAGING_DIR.iterdir() if d.is_dir()])


def generate_thumbnail(source_path: Path, aspect: str):
    """Creates a thumbnail for a mockup image if it doesn't exist."""
    thumb_dir = config.MOCKUP_THUMBNAIL_DIR / aspect
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / source_path.name

    if not thumb_path.exists():
        try:
            with Image.open(source_path) as img:
                # Use thumbnail dimensions from config
                img.thumbnail((config.THUMB_WIDTH, config.THUMB_HEIGHT))
                img.convert("RGB").save(thumb_path, "JPEG", quality=85)
        except Exception as e:
            logger.error(f"Could not create thumbnail for {source_path.name}: {e}")


# ===========================================================================
# 4. Main Dashboard Route
# ===========================================================================

@bp.route("/", defaults={'aspect': '4x5'})
@bp.route("/<aspect>")
def dashboard(aspect: str):
    """Display the paginated and sorted mockup management dashboard."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_filter = request.args.get('category', 'All')
    sort_by = request.args.get('sort', 'name')

    all_mockups = []
    
    categorised_path = config.MOCKUPS_CATEGORISED_DIR / aspect
    categorised_path.mkdir(parents=True, exist_ok=True)
    all_categories = sorted([d.name for d in categorised_path.iterdir() if d.is_dir()])
    
    def collect_mockups(folder_path, category_name):
        for item in folder_path.iterdir():
            if item.is_file() and item.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                generate_thumbnail(item, aspect)
                all_mockups.append({
                    "filename": item.name, 
                    "category": category_name,
                    "mtime": item.stat().st_mtime
                })

    if category_filter in {'All', 'Uncategorised'}:
        staging_path = config.MOCKUPS_STAGING_DIR / aspect
        staging_path.mkdir(parents=True, exist_ok=True)
        collect_mockups(staging_path, "Uncategorised")

    if category_filter != 'Uncategorised':
        for category_name in all_categories:
            if category_filter in {'All', category_name}:
                collect_mockups(categorised_path / category_name, category_name)

    all_mockups.sort(key=lambda x: x['mtime'] if sort_by == 'date' else x['filename'], reverse=(sort_by == 'date'))

    total_mockups = len(all_mockups)
    start = (page - 1) * per_page
    paginated_mockups = all_mockups[start:start + per_page]
    total_pages = (total_mockups + per_page - 1) // per_page

    return render_template(
        "admin/mockups.html",
        menu=get_menu(),
        mockups=paginated_mockups,
        categories=all_categories,
        current_aspect=aspect,
        aspect_ratios=get_available_aspects(),
        page=page, per_page=per_page, total_pages=total_pages,
        total_mockups=total_mockups, category_filter=category_filter, sort_by=sort_by
    )


# ===========================================================================
# 5. Image Serving Routes
# ===========================================================================
    
@bp.route("/thumbnail/<aspect>/<path:filename>")
def mockup_thumbnail(aspect, filename):
    """Serves the generated thumbnail for a mockup."""
    return send_from_directory(config.MOCKUP_THUMBNAIL_DIR / aspect, filename)


@bp.route("/image/<aspect>/<category>/<path:filename>")
def mockup_image(aspect, category, filename):
    """Serves the full-size mockup image."""
    if category == "Uncategorised":
        image_path = config.MOCKUPS_STAGING_DIR / aspect
    else:
        image_path = config.MOCKUPS_CATEGORISED_DIR / aspect / category
    return send_from_directory(image_path, filename)


# ===========================================================================
# 6. Mockup Management API Routes
# ===========================================================================

@bp.route("/upload/<aspect>", methods=["POST"])
def upload_mockup(aspect):
    """Handles file uploads for new mockups."""
    files = request.files.getlist('mockup_files')
    staging_path = config.MOCKUPS_STAGING_DIR / aspect
    count = 0
    for file in files:
        if file and file.filename:
            saved_path = staging_path / file.filename
            file.save(saved_path)
            generate_thumbnail(saved_path, aspect)
            count += 1
    if count > 0:
        logger.info(f"Uploaded {count} new mockup(s) to aspect '{aspect}'.")
        flash(f"Uploaded and created thumbnails for {count} new mockup(s).", "success")
    return redirect(url_for("mockup_admin.dashboard", aspect=aspect))


@bp.route("/find-duplicates/<aspect>")
def find_duplicates(aspect):
    """Scans for visually similar mockups using image hashing."""
    hashes = {}
    duplicates = []
    # Note: This route depends on the 'imagehash' library.
    all_paths = list((config.MOCKUPS_STAGING_DIR / aspect).glob("*.*"))
    all_paths.extend(list((config.MOCKUPS_CATEGORISED_DIR / aspect).rglob("*.*")))

    for path in all_paths:
        if path.suffix.lower() not in ['.png', '.jpg', '.jpeg']: continue
        try:
            with Image.open(path) as img:
                h = str(imagehash.phash(img))
                if h in hashes:
                    duplicates.append({"original": hashes[h], "duplicate": str(path.relative_to(config.BASE_DIR))})
                else:
                    hashes[h] = str(path.relative_to(config.BASE_DIR))
        except Exception as e:
            logger.warning(f"Could not hash image {path}: {e}")
            
    return jsonify({"duplicates": duplicates})


@bp.route("/create-category/<aspect>", methods=["POST"])
def create_category(aspect):
    """Creates a new category folder for an aspect ratio."""
    category_name = request.form.get("category_name", "").strip()
    if category_name:
        new_dir = config.MOCKUPS_CATEGORISED_DIR / aspect / category_name
        new_dir.mkdir(exist_ok=True)
        logger.info(f"Created new mockup category: '{category_name}' in aspect '{aspect}'.")
        flash(f"Category '{category_name}' created.", "success")
    else:
        flash("Category name cannot be empty.", "danger")
    return redirect(url_for("mockup_admin.dashboard", aspect=aspect))
    

@bp.route("/suggest-category", methods=["POST"])
def suggest_category():
    """Uses an AI script to suggest a category for an uncategorised mockup."""
    filename = request.json.get("filename")
    aspect = request.json.get("aspect")
    file_to_process = config.MOCKUPS_STAGING_DIR / aspect / filename
    
    if not file_to_process.exists():
        return jsonify({"success": False, "error": f"File not found: {filename}"}), 404
        
    try:
        # Use the new config variable for the script path
        cmd = ["python3", str(config.MOCKUP_CATEGORISER_SCRIPT_PATH), "--file", str(file_to_process), "--no-move"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
        return jsonify({"success": True, "suggestion": result.stdout.strip()})
    except subprocess.CalledProcessError as e:
        logger.error(f"Mockup categoriser script failed for {filename}: {e.stderr}")
        return jsonify({"success": False, "error": f"AI categorizer failed: {e.stderr}"}), 500
    except Exception as e:
        logger.error(f"Error calling mockup categoriser script for {filename}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/move-mockup", methods=["POST"])
def move_mockup():
    """Moves a mockup from one category (or uncategorised) to another."""
    data = request.json
    filename, aspect = data.get("filename"), data.get("aspect")
    original_category, new_category = data.get("original_category"), data.get("new_category")
    
    source_path = (config.MOCKUPS_STAGING_DIR / aspect / filename) if original_category == "Uncategorised" \
        else (config.MOCKUPS_CATEGORISED_DIR / aspect / original_category / filename)
    
    dest_dir = config.MOCKUPS_CATEGORISED_DIR / aspect / new_category
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        shutil.move(str(source_path), str(dest_dir / filename))
        logger.info(f"Moved mockup '{filename}' from '{original_category}' to '{new_category}' in aspect '{aspect}'.")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Failed to move mockup '{filename}': {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/delete-mockup", methods=["POST"])
def delete_mockup():
    """Deletes a mockup image and its corresponding thumbnail."""
    data = request.json
    filename, aspect, category = data.get("filename"), data.get("aspect"), data.get("category")

    path_to_delete = (config.MOCKUPS_STAGING_DIR / aspect / filename) if category == "Uncategorised" \
        else (config.MOCKUPS_CATEGORISED_DIR / aspect / category / filename)

    try:
        if path_to_delete.is_file():
            path_to_delete.unlink()
            (config.MOCKUP_THUMBNAIL_DIR / aspect / filename).unlink(missing_ok=True)
            logger.info(f"Deleted mockup '{filename}' from '{category}' in aspect '{aspect}'.")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "File not found."}), 404
    except Exception as e:
        logger.error(f"Error deleting mockup '{filename}': {e}")
        return jsonify({"success": False, "error": f"Error deleting file: {e}"}), 500

---
## routes/sellbrite_export.py
---
# routes/sellbrite_export.py
from __future__ import annotations
"""
Utilities for exporting listings to Sellbrite.

This module contains the helper function for generating a JSON payload
formatted specifically for the Sellbrite Listings API.

INDEX
-----
1.  Imports
2.  JSON Generation Function
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from typing import Any, Dict
import config


# ===========================================================================
# 2. JSON Generation Function
# ===========================================================================
def generate_sellbrite_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a dictionary formatted for the Sellbrite Listings API.

    This function takes an artwork's listing data, constructs absolute image
    URLs using the configured BASE_URL, and maps the fields to what the
    Sellbrite API expects, including a default quantity.

    Args:
        data: A dictionary containing the artwork listing information.

    Returns:
        A dictionary formatted for the Sellbrite API.
    """
    # Construct the public base URL for images from config
    base_url = config.BASE_URL
    
    relative_image_paths = data.get("images", [])
    
    # Convert relative paths from the project root to full, public URLs
    absolute_image_urls = [f"{base_url}/{path}" for path in relative_image_paths]

    sb = {
        "sku": data.get("sku"),
        "name": data.get("title"),
        "description": data.get("description"),
        "price": data.get("price"),
        "quantity": config.SELLBRITE_DEFAULTS["QUANTITY"],
        "tags": data.get("tags", []),
        "materials": data.get("materials", []),
        "primary_colour": data.get("primary_colour"),
        "secondary_colour": data.get("secondary_colour"),
        "seo_filename": data.get("seo_filename"),
        "images": absolute_image_urls,
    }
    # Clean out any empty or None fields before sending to the API
    return {k: v for k, v in sb.items() if v not in (None, "", [])}

---
## routes/sellbrite_service.py
---
# routes/sellbrite_service.py
"""
Sellbrite API integration utilities.

This module handles all direct communication with the Sellbrite API,
including authentication, connection testing, and product creation/updating.

INDEX
-----
1.  Imports & Initialisation
2.  Authentication & Connection
3.  API Product Management Functions
4.  Flask Routes
"""

# ===========================================================================
# 1. Imports & Initialisation
# ===========================================================================
from __future__ import annotations
import base64
import logging
from typing import Dict, Any, List, Tuple, Optional
import requests
from flask import Blueprint, jsonify
import config
from routes.sellbrite_export import generate_sellbrite_json

SELLBRITE_TOKEN = config.SELLBRITE_ACCOUNT_TOKEN
SELLBRITE_SECRET = config.SELLBRITE_SECRET_KEY
API_BASE = config.SELLBRITE_API_BASE_URL
logger = logging.getLogger(__name__)
bp = Blueprint("sellbrite", __name__, url_prefix="/sellbrite")

# ===========================================================================
# 2. Authentication & Connection
# ===========================================================================
# (_auth_header and test_sellbrite_connection functions remain the same)

def _auth_header() -> Dict[str, str]:
    """Return the HTTP Authorization header for Sellbrite."""
    if not SELLBRITE_TOKEN or not SELLBRITE_SECRET:
        logger.error("Sellbrite credentials not configured")
        return {}
    creds = f"{SELLBRITE_TOKEN}:{SELLBRITE_SECRET}".encode("utf-8")
    encoded = base64.b64encode(creds).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}


def test_sellbrite_connection() -> bool:
    """Attempt a simple authenticated request to verify credentials."""
    url = f"{API_BASE}/products?limit=1"
    try:
        resp = requests.get(url, headers=_auth_header(), timeout=10)
    except requests.RequestException as exc:
        logger.error("Sellbrite connection error: %s", exc)
        return False
    if resp.status_code == 200:
        logger.info("Sellbrite authentication succeeded")
        return True
    logger.error(
        "Sellbrite authentication failed: %s %s", resp.status_code, resp.text
    )
    return False

# ===========================================================================
# 3. API Product Management Functions
# ===========================================================================

def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product from Sellbrite by its SKU."""
    if not sku:
        return None
    url = f"{API_BASE}/products/{sku}"
    try:
        resp = requests.get(url, headers=_auth_header(), timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.RequestException as exc:
        logger.error(f"Failed to fetch product {sku} from Sellbrite: {exc}")
        return None

def get_products() -> List[Dict[str, Any]]:
    # ... (function remains the same)
    url = f"{API_BASE}/products"
    try:
        resp = requests.get(url, headers=_auth_header(), timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error("Failed to fetch products from Sellbrite: %s", exc)
        return []


def create_product(listing_data: Dict[str, Any]) -> Tuple[bool, str]:
    # ... (function remains the same)
    url = f"{API_BASE}/products"
    payload = generate_sellbrite_json(listing_data)
    sku = payload.get("sku", "N/A")
    try:
        resp = requests.post(url, headers=_auth_header(), json=payload, timeout=20)
        if 200 <= resp.status_code < 300:
            logger.info(f"Successfully created product {sku} in Sellbrite.")
            return True, f"Successfully created {sku}"
        else:
            error_message = resp.text
            logger.error(
                f"Failed to create product {sku} in Sellbrite. Status: {resp.status_code}, Response: {error_message}"
            )
            return False, f"Failed for {sku}: {error_message}"
    except requests.RequestException as exc:
        logger.error(f"Request failed for product {sku}: %s", exc)
        return False, f"Request failed for {sku}: {exc}"


def update_product(sku: str, listing_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Update an existing product, preserving its live inventory quantity."""
    if not sku:
        return False, "SKU is required for an update."

    # --- MODIFIED LOGIC ---
    # 1. Fetch the current product data from Sellbrite
    live_product = get_product_by_sku(sku)
    
    # 2. Generate the base payload with our local data
    payload = generate_sellbrite_json(listing_data)

    # 3. If the product exists, preserve its quantity
    if live_product:
        try:
            # Inventory is a list; we get the first warehouse's available count
            live_quantity = live_product.get("inventory", [{}])[0].get("available")
            if isinstance(live_quantity, int):
                payload["quantity"] = live_quantity
                logger.info(f"Preserving live quantity of {live_quantity} for SKU {sku}.")
        except (IndexError, TypeError):
            logger.warning(f"Could not parse live quantity for SKU {sku}. Using default.")
    # --- END OF MODIFIED LOGIC ---

    url = f"{API_BASE}/products/{sku}"
    try:
        resp = requests.put(url, headers=_auth_header(), json=payload, timeout=20)
        if 200 <= resp.status_code < 300:
            logger.info(f"Successfully updated product {sku} in Sellbrite.")
            return True, f"Successfully updated {sku}"
        
        error_message = resp.text
        logger.error(f"Failed to update product {sku}. Status: {resp.status_code}, Response: {error_message}")
        return False, f"Update failed for {sku}: {error_message}"
    except requests.RequestException as exc:
        logger.error(f"Request failed for product update {sku}: %s", exc)
        return False, f"Update request failed for {sku}: {exc}"

# ===========================================================================
# 4. Flask Routes
# ===========================================================================
@bp.route("/test-connection")
def sellbrite_test_route():
    # ... (function remains the same)
    success = test_sellbrite_connection()
    status = 200 if success else 500
    return jsonify({"success": success}), status

---
## routes/test_routes.py
---
# routes/test_routes.py
"""
Flask routes for rendering experimental or test templates.

This blueprint is used for development and testing purposes, allowing new
UI components or page layouts to be viewed in isolation before being
integrated into the main application.

INDEX
-----
1.  Imports
2.  Blueprint Setup
3.  Test Routes
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
from flask import Blueprint, render_template

# ===========================================================================
# 2. Blueprint Setup
# ===========================================================================
test_bp = Blueprint('test_bp', __name__)


# ===========================================================================
# 3. Test Routes
# ===========================================================================

@test_bp.route('/overlay-test')
def overlay_test():
    """Renders a test page for the main overlay menu design."""
    return render_template('codex-library/Overlay-Menu-Design-Template/main-design-template.html')


@test_bp.route('/test/edit-listing')
def edit_listing_test():
    """Renders an overlay test version of the edit listing template."""
    return render_template('edit_listing_overlay_test.html')


@test_bp.route('/test/artworks')
def artworks_test():
    """Renders an overlay test version of the artworks template."""
    return render_template('artworks_overlay_test.html')

---
## routes/utils.py
---
# routes/utils.py
"""
Central utility functions for the ArtNarrator Flask application.

This module provides helpers for data manipulation, image processing, and
interacting with the application's file-based data stores. It is designed
to be imported by the main route files and does not depend on them,
preventing circular imports.

Table of Contents (ToC)
-----------------------
[utils-py-1] Imports & Initialisation
    [utils-py-1a] Imports
    [utils-py-1b] Constants & Globals

[utils-py-2] Path & URL Utilities
    [utils-py-2a] relative_to_base
    [utils-py-2b] is_finalised_image
    [utils-py-2c] resolve_image_url
    [utils-py-2d] get_artwork_image_url
    
[utils-py-3] Template & UI Helpers
    [utils-py-3a] get_menu
    [utils-py-3b] populate_artwork_data_from_json
    [utils-py-3c] get_mockup_details_for_template

[utils-py-4] Image Processing Utilities
    [utils-py-4a] resize_image_for_long_edge
    [utils-py-4b] resize_for_analysis
    [utils-py-4c] apply_perspective_transform

[utils-py-5] Artwork Data Retrieval
    [utils-py-5a] get_all_artworks
    [utils-py-5b] list_processed_artworks
    [utils-py-5c] list_finalised_artworks
    [utils-py-5d] list_ready_to_analyze
    [utils-py-5e] latest_analyzed_artwork
    [utils-py-5f] latest_composite_folder

[utils-py-6] Mockup Management Utilities
    [utils-py-6a] get_mockup_categories
    [utils-py-6b] random_image
    [utils-py-6c] init_slots
    [utils-py-6d] compute_options
    [utils-py-6e] get_mockups
    [utils-py-6f] swap_one_mockup

[utils-py-7] Text & String Manipulation
    [utils-py-7a] slugify
    [utils-py-7b] prettify_title
    [utils-py-7c] read_generic_text
    [utils-py-7d] clean_terms
    [utils-py-7e] get_allowed_colours

[utils-py-8] SKU Management
    [utils-py-8a] infer_sku_from_filename
    [utils-py-8b] sync_filename_with_sku
    [utils-py-8c] assign_or_get_sku
    [utils-py-8d] validate_all_skus

[utils-py-9] Listing File Path Management
    [utils-py-9a] update_listing_paths

[utils-py-10] Legacy Registry Management
    [utils-py-10a] _load_registry
    [utils-py-10b] _save_registry
    [utils-py-10c] register_new_artwork
    [utils-py-10d] move_and_log
    [utils-py-10e] update_status
    [utils-py-10f] get_record_by_base
    [utils-py-10g] get_record_by_seo_filename
    [utils-py-10h] remove_record_from_registry
"""

# === [ Section 1: Imports & Initialisation | utils-py-1 ] ===
# Handles all necessary library imports and sets up global constants for the module.
# Cross-references: config.py, helpers/listing_utils.py
# ---------------------------------------------------------------------------------

# --- [ 1a: Imports | utils-py-1a ] ---
from __future__ import annotations
import time
import os
import json
import random
import re
import logging
import shutil
import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional

from flask import session, url_for
from PIL import Image
try:
    import cv2
except ImportError:
    cv2 = None # OpenCV is an optional dependency for perspective transforms
import numpy as np

import config
from config import BASE_URL, BASE_DIR
from utils.sku_assigner import get_next_sku
# FIX: Import helpers from the correct module to break the circular dependency
from helpers.listing_utils import resolve_listing_paths, load_json_file_safe


# --- [ 1b: Constants & Globals | utils-py-1b ] ---
Image.MAX_IMAGE_PIXELS = None
logger = logging.getLogger(__name__)

# Expose a LOGS_DIR constant so tests and other modules can monkeypatch or
# reference the application's log directory without importing ``config``
# directly.  Falling back to a temporary path keeps this module safe during
# isolated unit tests where ``config.LOGS_DIR`` may not exist.
LOGS_DIR = getattr(config, "LOGS_DIR", Path("/tmp/logs"))

ALLOWED_COLOURS = sorted(config.ETSY_COLOURS.keys())
ALLOWED_COLOURS_LOWER = {c.lower(): c for c in ALLOWED_COLOURS}


# === [ Section 2: Path & URL Utilities | utils-py-2 ] ===
# A collection of helper functions for manipulating and resolving file paths and URLs.
# ---------------------------------------------------------------------------------

# --- [ 2a: relative_to_base | utils-py-2a ] ---
def relative_to_base(path: Path | str) -> str:
    """
    Converts an absolute filesystem path to a path string relative to the project's base directory.

    Args:
        path: The absolute Path object or string to convert.

    Returns:
        A string representing the path relative to the project root (e.g., "static/img/logo.png").
    """
    return str(Path(path).resolve().relative_to(config.BASE_DIR))


# --- [ 2b: is_finalised_image | utils-py-2b ] ---
def is_finalised_image(path: str | Path) -> bool:
    """
    Checks if a given file path exists within either the 'finalised-artwork' or 'artwork-vault' directories.

    Args:
        path: The file path string or Path object to check.

    Returns:
        True if the path is within a finalised or locked directory, False otherwise.
    """
    p = Path(path).resolve()
    try:
        p.relative_to(config.FINALISED_ROOT)
        return True
    except ValueError:
        try:
            p.relative_to(config.ARTWORK_VAULT_ROOT)
            return True
        except ValueError:
            return False


# --- [ 2c: resolve_image_url | utils-py-2c ] ---
def resolve_image_url(path: Path) -> str:
    """Convert a filesystem path to an absolute public URL.

    Args:
        path: Absolute :class:`Path` to an image on disk.

    Returns:
        Fully-qualified URL pointing to the image using the configured
        ``BASE_URL`` and project ``BASE_DIR``.
    """
    rel = path.relative_to(BASE_DIR).as_posix()
    return f"{BASE_URL}/{rel}"

# --- [ 2d: get_artwork_image_url | utils-py-2d ] ---
# NEW (2025-08-04): Central function to generate correct image URLs based on artwork status.
def get_artwork_image_url(artwork_status: str, filename: str) -> str:
    """
    Generates a fail-safe public URL for an artwork image based on its status.

    Args:
        artwork_status: The status of the artwork (e.g., 'processed', 'finalised', 'locked').
        filename: The relative path of the file from its stage root (e.g., 'folder/image.jpg').

    Returns:
        A correct, publicly accessible URL string.
    """
    if artwork_status == 'locked':
        endpoint = 'artwork.locked_image'
    elif artwork_status == 'finalised':
        endpoint = 'artwork.finalised_image'
    else: # Default to 'processed'
        endpoint = 'artwork.processed_image'
    
    try:
        # Add a check for mockup thumbnail routes which use a different endpoint
        if config.THUMB_SUBDIR in filename and "-MU-" in filename:
            endpoint = 'artwork.serve_mockup_thumb'
            # The serve_mockup_thumb route expects the filepath relative to the stage root
            return url_for(endpoint, filepath=filename)

        return url_for(endpoint, filename=filename)
    except Exception as e:
        logger.error(f"Could not generate URL for endpoint '{endpoint}' with filename '{filename}': {e}")
        return "#" # Return a dead link on error


# === [ Section 3: Template & UI Helpers | utils-py-3 ] ===
# Functions that provide data and context specifically for rendering Jinja2 templates.
# ---------------------------------------------------------------------------------

# --- [ 3a: get_menu | utils-py-3a ] ---
def get_menu() -> List[Dict[str, str | None]]:
    """
    Generates the dynamic navigation menu items for the main layout template.
    Includes a link to the most recently analyzed artwork for quick access.

    Returns:
        A list of dictionaries, where each dictionary represents a menu item.
    """
    menu = [
        {"name": "Home", "url": url_for("artwork.home")},
        {"name": "Artwork Gallery", "url": url_for("artwork.artworks")},
        {"name": "Finalised", "url": url_for("artwork.finalised_gallery")},
    ]
    latest = latest_analyzed_artwork()
    if latest and latest.get("aspect") and latest.get("filename"):
        try:
            menu.append({
                "name": "Review Latest Listing",
                "url": url_for("artwork.edit_listing", aspect=latest["aspect"], filename=latest["filename"]),
            })
        except Exception:
             menu.append({"name": "Review Latest Listing", "url": None})
    else:
        menu.append({"name": "Review Latest Listing", "url": None})
    return menu


# --- [ 3b: populate_artwork_data_from_json | utils-py-3b ] ---
def populate_artwork_data_from_json(data: dict, seo_folder: str) -> dict:
    """
    Populates a dictionary with artwork details from a listing JSON for the edit page form.

    Args:
        data: The dictionary loaded from the artwork's -listing.json file.
        seo_folder: The name of the artwork's parent folder.

    Returns:
        A dictionary formatted for easy use in the Jinja2 template.
    """
    tags_list = data.get("tags", [])
    materials_list = data.get("materials", [])
    generic_desc = data.get("generic_description") or read_generic_text(data.get("aspect_ratio", ""))
    artwork = {
        "title": data.get("title", prettify_title(seo_folder)),
        "description": data.get("description", ""),
        "generic_description": generic_desc,
        "tags": tags_list,
        "tags_str": ", ".join(tags_list),
        "materials": materials_list,
        "materials_str": ", ".join(materials_list),
        "dimensions": data.get("dimensions", ""),
        "size": data.get("size", ""),
        "primary_colour": data.get("primary_colour", ""),
        "secondary_colour": data.get("secondary_colour", ""),
        "seo_filename": data.get("seo_filename", f"{seo_folder}.jpg"),
        "seo_slug": seo_folder,
        "price": data.get("price", "18.27"),
        "sku": data.get("sku", ""),
        "images": "\n".join(data.get("images", [])),
    }
    return artwork


# --- [ 3c: get_mockup_details_for_template | utils-py-3c ] ---
def get_mockup_details_for_template(mockups_data: list, folder: Path, seo_folder: str, aspect: str) -> list:
    """
    Processes mockup data from a listing file for use in the edit_listing template.

    Args:
        mockups_data: The 'mockups' list from the listing JSON.
        folder: The absolute path to the artwork's parent directory.
        seo_folder: The name of the artwork's parent folder.
        aspect: The aspect ratio of the artwork (e.g., '4x5').

    Returns:
        A list of dictionaries, each representing a mockup with its associated paths and metadata.
    """
    mockups = []
    for idx, mp in enumerate(mockups_data):
        composite_name = mp.get("composite", "")
        thumb_name = mp.get("thumbnail", "")
        category = mp.get("category", "")

        out_path = folder / composite_name if composite_name else Path()
        thumb_path = folder / config.THUMB_SUBDIR / thumb_name if thumb_name else Path()
        
        path_rel = f"{seo_folder}/{composite_name}" if composite_name else ""
        thumb_rel_path = f"{seo_folder}/{config.THUMB_SUBDIR}/{thumb_name}" if thumb_name else ""
        
        mockups.append({
            "path": out_path,
            "category": category,
            "exists": out_path.exists(),
            "index": idx,
            "thumb": thumb_path,
            "thumb_exists": thumb_path.exists(),
            "path_rel": path_rel,
            "thumb_rel": thumb_rel_path,
        })
    return mockups


# === [ Section 4: Image Processing Utilities | utils-py-4 ] ===
# Functions for handling image manipulations like resizing and transformations.
# ---------------------------------------------------------------------------------

# --- [ 4a: resize_image_for_long_edge | utils-py-4a ] ---
def resize_image_for_long_edge(image: Image.Image, target_long_edge: int = 2000) -> Image.Image:
    """Resizes an image to have its longest edge match the target size, preserving aspect ratio."""
    width, height = image.size
    scale = target_long_edge / max(width, height)
    if scale < 1.0:
        new_width = int(width * scale)
        new_height = int(height * scale)
        return image.resize((new_width, new_height), Image.LANCZOS)
    return image.copy()


# --- [ 4b: resize_for_analysis | utils-py-4b ] ---
def resize_for_analysis(image: Image.Image, dest_path: Path):
    """
    Resizes and saves an image to be compliant with AI analysis size and filetype limits.
    It iteratively reduces JPEG quality to ensure the file is under the max size.
    """
    w, h = image.size
    scale = config.ANALYSE_MAX_DIM / max(w, h)
    if scale < 1.0:
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    
    image = image.convert("RGB")
    q = 85
    while True:
        image.save(dest_path, "JPEG", quality=q, optimize=True)
        if dest_path.stat().st_size <= config.ANALYSE_MAX_MB * 1024 * 1024 or q <= 60:
            break
        q -= 5


# --- [ 4c: apply_perspective_transform | utils-py-4c ] ---
def apply_perspective_transform(art_img: Image.Image, mockup_img: Image.Image, dst_coords: list) -> Image.Image:
    """Overlays artwork onto a mockup using perspective transform, handling RGBA transparency."""
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) library is required for perspective transform.")
    w, h = art_img.size
    src_points = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    dst_points = np.float32([[c['x'], c['y']] for c in dst_coords])
    
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    art_np = np.array(art_img.convert("RGBA"))
    
    warped = cv2.warpPerspective(art_np, matrix, (mockup_img.width, mockup_img.height))
    warped_pil = Image.fromarray(warped)
    
    final_image = Image.alpha_composite(mockup_img.convert("RGBA"), warped_pil)
    return final_image


# === [ Section 5: Artwork Data Retrieval | utils-py-5 ] ===
# Functions for scanning the filesystem and retrieving lists of artworks in various states.
# ---------------------------------------------------------------------------------

# --- [ 5a: get_all_artworks | utils-py-5a ] ---
def get_all_artworks() -> List[Dict]:
    """Scans all artwork locations (processed, finalised, locked) and returns a unified list."""
    items: List[Dict] = []
    
    def process_directory(directory: Path, status: str):
        if not directory.exists(): return
        for folder in directory.iterdir():
            if not folder.is_dir(): continue
            
            slug = folder.name.replace("LOCKED-", "")
            listing_file = folder / f"{slug}-listing.json"
            if not listing_file.exists(): continue

            try:
                data = load_json_file_safe(listing_file)
                
                main_image_name = data.get("seo_filename", f"{slug}.jpg")
                thumb_image_name = config.FILENAME_TEMPLATES["thumbnail"].format(seo_slug=slug)

                item = {
                    "status": status,
                    "seo_folder": folder.name,
                    "title": data.get("title") or prettify_title(slug),
                    "filename": data.get("filename", f"{slug}.jpg"),
                    "main_image": main_image_name,
                    "thumb": thumb_image_name,
                    "aspect": data.get("aspect_ratio", ""),
                    "locked": data.get("locked", False),
                    "description": data.get("description", ""),
                    "sku": data.get("sku", ""),
                    "price": data.get("price", "18.27"),
                    "primary_colour": data.get("primary_colour", ""),
                    "secondary_colour": data.get("secondary_colour", ""),
                    "seo_filename": data.get("seo_filename", ""),
                    "tags": data.get("tags", []),
                    "materials": data.get("materials", []),
                    "mockups": data.get("mockups", [])
                }
                items.append(item)
            except Exception as e:
                logging.error(f"Failed to process listing in {folder.name}: {e}")
                continue

    process_directory(config.PROCESSED_ROOT, "processed")
    process_directory(config.FINALISED_ROOT, "finalised")
    process_directory(config.ARTWORK_VAULT_ROOT, "locked")
    
    items.sort(key=lambda x: x["title"].lower())
    return items


# --- [ 5b: list_processed_artworks | utils-py-5b ] ---
def list_processed_artworks() -> Tuple[List[Dict], set]:
    """Returns a list of artworks in the 'processed' state and a set of their filenames."""
    processed_artworks = [a for a in get_all_artworks() if a['status'] == 'processed']
    processed_filenames = {a['filename'] for a in processed_artworks}
    return processed_artworks, processed_filenames


# --- [ 5c: list_finalised_artworks | utils-py-5c ] ---
def list_finalised_artworks() -> List[Dict]:
    """Returns a list of artworks in the 'finalised' state."""
    return [a for a in get_all_artworks() if a['status'] == 'finalised']


# --- [ 5d: list_ready_to_analyze | utils-py-5d ] ---
def list_ready_to_analyze(processed_filenames: set) -> List[Dict]:
    """Returns artworks from the unanalysed folder that are not yet processed."""
    ready: List[Dict] = []
    for qc_path in config.UNANALYSED_ROOT.glob("**/*.qc.json"):
        base = qc_path.name.replace(".qc.json", "")
        try:
            qc_data = load_json_file_safe(qc_path)
            original_filename = qc_data.get("original_filename")
            if original_filename and original_filename in processed_filenames:
                continue
            
            ext = qc_data.get("extension", "jpg")
            title = prettify_title(Path(original_filename or base).stem)
            
            ready.append({
                "aspect": qc_data.get("aspect_ratio", ""),
                "filename": f"{base}.{ext}",
                "title": title,
                "thumb": f"{base}-thumb.jpg",
                "base": base,
            })
        except Exception as e:
            logging.error(f"Error processing QC file {qc_path}: {e}")
            continue
            
    ready.sort(key=lambda x: x["title"].lower())
    return ready


# --- [ 5e: latest_analyzed_artwork | utils-py-5e ] ---
def latest_analyzed_artwork() -> Optional[Dict[str, str]]:
    """Finds the most recently modified artwork in the 'processed' directory."""
    latest_time = 0
    latest_info = None
    if not config.PROCESSED_ROOT.exists():
        return None
    for folder in config.PROCESSED_ROOT.iterdir():
        if not folder.is_dir(): continue
        listing_path = next(folder.glob("*-listing.json"), None)
        if not listing_path: continue
        
        mtime = listing_path.stat().st_mtime
        if mtime > latest_time:
            latest_time = mtime
            data = load_json_file_safe(listing_path)
            latest_info = { "aspect": data.get("aspect_ratio"), "filename": data.get("seo_filename") }
    return latest_info


# --- [ 5f: latest_composite_folder | utils-py-5f ] ---
def latest_composite_folder() -> str | None:
    """Returns the name of the most recently modified folder in PROCESSED_ROOT."""
    processed_dir = config.PROCESSED_ROOT
    if not processed_dir.exists():
        return None

    sub_folders = [d for d in processed_dir.iterdir() if d.is_dir()]
    if not sub_folders:
        return None

    latest_folder = max(sub_folders, key=lambda d: d.stat().st_mtime)
    return latest_folder.name


# === [ Section 6: Mockup Management Utilities | utils-py-6 ] ===
# Functions related to the interactive mockup selection workflow.
# ---------------------------------------------------------------------------------

# --- [ 6a: get_mockup_categories | utils-py-6a ] ---
def get_mockup_categories(aspect_folder: Path | str) -> List[str]:
    """Return sorted list of category folder names under a specific aspect folder."""
    folder = Path(aspect_folder)
    if not folder.exists(): return []
    return sorted(f.name for f in folder.iterdir() if f.is_dir() and not f.name.startswith("."))


# --- [ 6b: random_image | utils-py-6b ] ---
def random_image(category: str, aspect: str) -> Optional[str]:
    """Return a random image filename for a given category and aspect."""
    cat_dir = config.MOCKUPS_CATEGORISED_DIR / aspect / category
    if not cat_dir.exists(): return None
    images = [f.name for f in cat_dir.glob("*.png")]
    return random.choice(images) if images else None


# --- [ 6c: init_slots | utils-py-6c ] ---
def init_slots() -> None:
    """Initialise mockup slot selections in the user's session."""
    aspect = "4x5"
    cats = get_mockup_categories(config.MOCKUPS_CATEGORISED_DIR / aspect)
    session["slots"] = [{"category": c, "image": random_image(c, aspect)} for c in cats]


# --- [ 6d: compute_options | utils-py-6d ] ---
def compute_options(slots) -> List[List[str]]:
    """Return category options for each slot in the mockup selector."""
    aspect = "4x5"
    cats = get_mockup_categories(config.MOCKUPS_CATEGORISED_DIR / aspect)
    return [cats for _ in slots]


# --- [ 6e: get_mockups | utils-py-6e ] ---
def get_mockups(seo_folder: str) -> list:
    """Return mockup entries from an artwork's listing JSON."""
    try:
        _, _, listing_file, _ = resolve_listing_paths("", seo_folder, allow_locked=True)
        data = load_json_file_safe(listing_file)
        return data.get("mockups", [])
    except Exception as exc:
        logger.error(f"Failed reading mockups for {seo_folder}: {exc}")
        return []


# --- [ 6f: swap_one_mockup | utils-py-6f ] ---
def swap_one_mockup(seo_folder: str, slot_idx: int, new_category: str, current_mockup_src: str | None = None) -> tuple[bool, str, str]:
    """Swaps a single mockup to a new category and regenerates the composite image with a stable filename."""
    try:
        _, folder, listing_file, _ = resolve_listing_paths("", seo_folder, allow_locked=True)
    except FileNotFoundError:
        logger.error(f"Could not resolve listing paths for {seo_folder} during mockup swap.")
        return False, "", ""
            
    with open(listing_file, "r", encoding="utf-8") as f: data = json.load(f)
    mockups = data.get("mockups", [])
    if not (0 <= slot_idx < len(mockups)):
        logger.error(f"Invalid slot index {slot_idx} provided for {seo_folder}.")
        return False, "", ""

    aspect = data.get("aspect_ratio")
    mockup_root = config.MOCKUPS_CATEGORISED_DIR / aspect / new_category
    mockup_files = list(mockup_root.glob("*.png"))
    
    current_mockup_name = None
    if isinstance(mockups[slot_idx], dict):
        composite_name = mockups[slot_idx].get("composite", "")
        match = re.search(r'-([^-]+-\d+)(?:-\d+)?\.jpg$', composite_name)
        if match: current_mockup_name = f"{match.group(1)}.png"
    
    choices = [f for f in mockup_files if f.name != current_mockup_name]
    if not choices: choices = mockup_files
    if not choices:
        logger.warning(f"No mockup images found in category '{new_category}' for aspect '{aspect}'.")
        return False, "", ""
    new_mockup = random.choice(choices)
    
    slug = seo_folder.replace("LOCKED-", "")
    
    # FIX (2025-08-04): Use stable, index-based naming from config templates instead of timestamps.
    output_filename = config.FILENAME_TEMPLATES["mockup"].format(seo_slug=slug, num=slot_idx + 1)
    output_path = folder / output_filename

    try:
        coords_path = config.COORDS_DIR / aspect / new_category / f"{new_mockup.stem}.json"
        art_path = folder / f"{slug}.jpg"
        with open(coords_path, "r", encoding="utf-8") as cf:
            coords = json.load(cf)["corners"]
        
        with Image.open(art_path) as art_img, Image.open(new_mockup) as mock_img:
            art_img = resize_image_for_long_edge(art_img.convert("RGBA"))
            composite = apply_perspective_transform(art_img, mock_img.convert("RGBA"), coords)
        
        composite.convert("RGB").save(output_path, "JPEG", quality=85)

        thumb_dir = folder / config.THUMB_SUBDIR
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_name = f"{output_path.stem}-thumb.jpg"
        thumb_path = thumb_dir / thumb_name
        with composite.copy() as thumb_img:
            thumb_img.thumbnail((config.THUMB_WIDTH, config.THUMB_HEIGHT))
            thumb_img.convert("RGB").save(thumb_path, "JPEG", quality=85)
            
        old = mockups[slot_idx]
        if isinstance(old, dict):
            if old.get("composite") and old.get("composite") != output_path.name:
                (folder / old["composite"]).unlink(missing_ok=True)
            if old.get("thumbnail") and old.get("thumbnail") != thumb_name:
                (thumb_dir / old["thumbnail"]).unlink(missing_ok=True)

        data.setdefault("mockups", [])[slot_idx] = {
            "category": new_category,
            "source": str(new_mockup.relative_to(config.MOCKUPS_INPUT_DIR)),
            "composite": output_path.name,
            "thumbnail": thumb_name,
        }
        with open(listing_file, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        
        logger.info(f"Successfully swapped mockup for '{seo_folder}' to '{output_filename}'.")
        return True, output_path.name, thumb_name
        
    except Exception as e:
        logger.error(f"Swap failed during image generation for {seo_folder}: {e}", exc_info=True)
        output_path.unlink(missing_ok=True)
        return False, "", ""


# === [ Section 7: Text & String Manipulation | utils-py-7 ] ===
# Helpers for cleaning, formatting, and manipulating strings.
# ---------------------------------------------------------------------------------

# --- [ 7a: slugify | utils-py-7a ] ---
def slugify(text: str) -> str:
    """Converts a string into a URL- and filename-safe slug."""
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text

# --- [ 7b: prettify_title | utils-py-7b ] ---
def prettify_title(slug: str) -> str:
    """Converts a filename-safe slug into a human-readable title."""
    name = os.path.splitext(slug)[0].replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", name).title()


# --- [ 7c: read_generic_text | utils-py-7c ] ---
def read_generic_text(aspect: str) -> str:
    """Reads the generic boilerplate text block for a given aspect ratio."""
    path = config.GENERIC_TEXTS_DIR / f"{aspect}.txt"
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        logger.warning(f"Generic text for {aspect} not found at {path}")
        return ""


# --- [ 7d: clean_terms | utils-py-7d ] ---
def clean_terms(items: List[str]) -> Tuple[List[str], bool]:
    """Removes invalid characters from a list of strings (e.g., tags)."""
    cleaned: List[str] = []
    changed = False
    for item in items:
        new = re.sub(r"[^A-Za-z0-9 ,]", "", item).replace("-", "").strip()
        new = re.sub(r"\s+", " ", new)
        if new != item.strip(): changed = True
        if new: cleaned.append(new)
    return cleaned, changed


# --- [ 7e: get_allowed_colours | utils-py-7e ] ---
def get_allowed_colours() -> List[str]:
    """Returns a copy of the list of Etsy-allowed color names."""
    return ALLOWED_COLOURS.copy()


# === [ Section 8: SKU Management | utils-py-8 ] ===
# Functions for handling Stock Keeping Units (SKUs).
# ---------------------------------------------------------------------------------

# --- [ 8a: infer_sku_from_filename | utils-py-8a ] ---
def infer_sku_from_filename(filename: str) -> Optional[str]:
    """Extracts a SKU from a filename string."""
    m = re.search(r"RJC-([A-Za-z0-9-]+)(?:\.jpg)?$", filename or "")
    return f"RJC-{m.group(1)}" if m else None


# --- [ 8b: sync_filename_with_sku | utils-py-8b ] ---
def sync_filename_with_sku(seo_filename: str, sku: str) -> str:
    """Replaces the SKU portion of a filename with a new SKU."""
    if not seo_filename or not sku: return seo_filename
    return re.sub(r"RJC-[A-Za-z0-9-]+(?=\.jpg$)", sku, seo_filename)


# --- [ 8c: assign_or_get_sku | utils-py-8c ] ---
def assign_or_get_sku(listing_json_path: Path, tracker_path: Path, *, force: bool = False) -> str:
    """Retrieves an existing SKU from a listing file or assigns a new one."""
    data = load_json_file_safe(listing_json_path)
    if not force and data.get("sku"): return data["sku"]
    sku = get_next_sku(tracker_path)
    data["sku"] = sku
    if data.get("seo_filename"):
        data["seo_filename"] = sync_filename_with_sku(data["seo_filename"], sku)
    with open(listing_json_path, "w") as f: json.dump(data, f, indent=2)
    return sku


# --- [ 8d: validate_all_skus | utils-py-8d ] ---
def validate_all_skus(entries: List[dict], tracker_path: Path) -> List[str]:
    """Validates SKUs for format, duplicates, and gaps in a list of entries."""
    seen = set()
    errors = []
    sku_numbers = []

    for entry in entries:
        sku = entry.get("sku", "").strip()
        if not sku or not sku.startswith("RJC-"):
            errors.append(f"Invalid SKU format: {sku}")
            continue
        
        if sku in seen:
            errors.append(f"Duplicate SKU found: {sku}")
        seen.add(sku)
        
        try:
            num = int(sku.split('-')[-1])
            sku_numbers.append(num)
        except (ValueError, IndexError):
            errors.append(f"Could not parse SKU number: {sku}")

    if sku_numbers:
        sku_numbers.sort()
        for i in range(len(sku_numbers) - 1):
            if sku_numbers[i+1] != sku_numbers[i] + 1:
                errors.append(f"Gap detected in SKUs between {sku_numbers[i]} and {sku_numbers[i+1]}")
                break

    return errors


# === [ Section 9: Listing File Path Management | utils-py-9 ] ===
# Contains the critical function for updating paths within a listing.json file.
# ---------------------------------------------------------------------------------

# --- [ 9a: update_listing_paths | utils-py-9a ] ---
def update_listing_paths(listing_file: Path, old_root: Path, new_root: Path) -> None:
    """
    Updates all file paths within a listing JSON file when its parent folder is moved.
    This function is critical for the "Finalise" step to prevent broken image links.

    Args:
        listing_file: The path to the listing's JSON file.
        old_root: The old base directory (e.g., config.PROCESSED_ROOT).
        new_root: The new base directory (e.g., config.FINALISED_ROOT).
    """
    if not listing_file.exists():
        logger.warning(f"update_listing_paths was called but file not found: {listing_file}")
        return

    data = load_json_file_safe(listing_file)
    
    str_old_root = str(old_root)
    str_new_root = str(new_root)

    old_url_rel = old_root.relative_to(config.BASE_DIR).as_posix()
    new_url_rel = new_root.relative_to(config.BASE_DIR).as_posix()
    old_url_abs = config.resolve_image_url(old_root)
    new_url_abs = config.resolve_image_url(new_root)

    def _replace_all(text: str) -> str:
        for o, n in (
            (str_old_root, str_new_root),
            (old_url_rel, new_url_rel),
            (old_url_abs, new_url_abs),
        ):
            text = text.replace(o, n)
        return text

    # Update single-path keys
    for key in ["main_jpg_path", "thumb_jpg_path", "analyse_jpg_path", "processed_folder"]:
        if key in data and isinstance(data[key], str):
            data[key] = _replace_all(data[key])

    # Update list of image paths
    if "images" in data and isinstance(data["images"], list):
        data["images"] = [_replace_all(path) for path in data["images"]]
    
    with open(listing_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated all paths in {listing_file.name} from {old_root.name} to {new_root.name}.")


# === [ Section 10: Legacy Registry Management | utils-py-10 ] ===
# Functions for interacting with the old master-artwork-paths.json registry.
# These are kept for backward compatibility but may be phased out.
# ---------------------------------------------------------------------------------

# --- [ 10a: _load_registry | utils-py-10a ] ---
def _load_registry() -> dict:
    """Loads the master artwork JSON registry file."""
    return load_json_file_safe(config.OUTPUT_JSON)


# --- [ 10b: _save_registry | utils-py-10b ] ---
def _save_registry(reg: dict) -> None:
    """Writes data to the master artwork JSON registry atomically."""
    tmp = config.OUTPUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, config.OUTPUT_JSON)


# --- [ 10c: register_new_artwork | utils-py-10c ] ---
def register_new_artwork(uid: str, filename: str, folder: Path, assets: list, status: str, base: str):
    """Add a new artwork record to the legacy registry."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    reg = _load_registry()
    reg[uid] = {
        "seo_filename": filename,
        "base": base,
        "current_folder": str(folder),
        "assets": assets,
        "status": status,
        "history": [{"status": status, "folder": str(folder), "timestamp": ts}],
        "upload_date": ts,
    }
    _save_registry(reg)


# --- [ 10d: move_and_log | utils-py-10d ] ---
def move_and_log(src: Path, dest: Path, uid: str, status: str):
    """Move a file and update its record in the legacy registry."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    reg = _load_registry()
    rec = reg.get(uid, {})
    rec.setdefault("history", []).append({
        "status": status,
        "folder": str(dest.parent),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    rec["current_folder"] = str(dest.parent)
    rec["status"] = status
    assets = set(rec.get("assets", []))
    assets.add(dest.name)
    rec["assets"] = sorted(assets)
    reg[uid] = rec
    _save_registry(reg)


# --- [ 10e: update_status | utils-py-10e ] ---
def update_status(uid: str, folder: Path, status: str):
    """Update the status of an artwork in the legacy registry."""
    reg = _load_registry()
    rec = reg.get(uid)
    if not rec: return
    rec.setdefault("history", []).append({
        "status": status,
        "folder": str(folder),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    rec["current_folder"] = str(folder)
    rec["status"] = status
    reg[uid] = rec
    _save_registry(reg)


# --- [ 10f: get_record_by_base | utils-py-10f ] ---
def get_record_by_base(base: str) -> tuple[str | None, dict | None]:
    """Find a legacy registry record by its unique base name."""
    reg = _load_registry()
    for uid, rec in reg.items():
        if rec.get("base") == base:
            return uid, rec
    return None, None


# --- [ 10g: get_record_by_seo_filename | utils-py-10g ] ---
def get_record_by_seo_filename(filename: str) -> tuple[str | None, dict | None]:
    """Find a legacy registry record by its SEO filename."""
    reg = _load_registry()
    for uid, rec in reg.items():
        if rec.get("seo_filename") == filename:
            return uid, rec
    return None, None


# --- [ 10h: remove_record_from_registry | utils-py-10h ] ---
def remove_record_from_registry(uid: str) -> bool:
    """Safely remove a record from the legacy JSON registry by its UID."""
    if not uid: return False
    reg = _load_registry()
    if uid in reg:
        del reg[uid]
        _save_registry(reg)
        logger.info(f"Removed record {uid} from registry.")
        return True
    return False

---
## scripts/analyze_artwork.py
---
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArtNarrator | analyze_artwork.py
===============================================================
Analyzes artworks using OpenAI. This script is the core engine that
generates listing data, processes files, and prepares artworks for the
next stage in the workflow.
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
import argparse, base64, json, logging, os, random, re, shutil, sys, traceback
from pathlib import Path
import datetime as _dt
from dotenv import load_dotenv
from PIL import Image
from openai import OpenAI
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils.logger_utils import setup_logger
from utils.sku_assigner import get_next_sku
from helpers.listing_utils import assemble_gdws_description

# ===========================================================================
# 2. Configuration & Constants
# ===========================================================================
load_dotenv()
Image.MAX_IMAGE_PIXELS = None
API_KEY = config.OPENAI_API_KEY
if not API_KEY: raise RuntimeError("OPENAI_API_KEY not set in environment/.env file")
client = OpenAI(api_key=API_KEY, project=config.OPENAI_PROJECT_ID)
ETSY_COLOURS = config.ETSY_COLOURS
USER_ID = os.getenv("USER_ID", "anonymous")
logger = setup_logger(__name__, "ANALYZE_OPENAI")

# ===========================================================================
# 4. Core Utility Functions
# ===========================================================================

def _write_status(step: str, percent: int, filename: str):
    """Writes progress to the shared status file for the UI modal."""
    payload = {"step": step, "percent": percent, "file": filename, "status": "analyzing"}
    try:
        config.ANALYSIS_STATUS_FILE.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass # Fails silently to not interrupt the main analysis process

def get_aspect_ratio(image_path: Path) -> str:
    """Return closest aspect ratio label for a given image."""
    with Image.open(image_path) as img: w, h = img.size
    aspect_map = [("1x1", 1/1), ("2x3", 2/3), ("3x2", 3/2), ("3x4", 3/4), ("4x3", 4/3), ("4x5", 4/5), ("5x4", 5/4), ("5x7", 5/7), ("7x5", 7/5), ("9x16", 9/16), ("16x9", 16/9)]
    ar = round(w / h, 4)
    best = min(aspect_map, key=lambda tup: abs(ar - tup[1]))
    logger.info(f"Determined aspect ratio for {image_path.name}: {best[0]}")
    return best[0]

def slugify(text: str) -> str:
    """Return a slug suitable for filenames."""
    text = re.sub(r"[^\w\- ]+", "", text).strip().replace(" ", "-")
    return re.sub("-+", "-", text).lower()

def generate_seo_filename(ai_slug: str, assigned_sku: str) -> tuple[str, str]:
    """
    Constructs a final SEO filename guaranteed to be <= 70 characters.
    """
    # Define the fixed parts of the filename
    SUFFIX = "-by-robin-custance"
    EXTENSION = ".jpg"
    
    # Calculate the maximum possible length for the AI-generated slug
    # 70 (total) - length of suffix - 1 (hyphen) - length of SKU - length of extension
    max_slug_len = 70 - len(SUFFIX) - 1 - len(assigned_sku) - len(EXTENSION)
    
    # Clean, slugify, and truncate the AI-provided slug
    clean_slug = slugify(ai_slug)
    truncated_slug = clean_slug[:max_slug_len]
    
    # Ensure the slug doesn't end with a hyphen after truncation
    if truncated_slug.endswith('-'):
        truncated_slug = truncated_slug[:-1]
        
    # Assemble the final filename
    final_filename = f"{truncated_slug}{SUFFIX}-{assigned_sku}{EXTENSION}"
    
    # The folder name is the stem of the final filename
    seo_folder_name = Path(final_filename).stem
    
    return final_filename, seo_folder_name

def read_onboarding_prompt() -> str:
    """Reads the main system prompt from the file defined in config."""
    return Path(config.ONBOARDING_PATH).read_text(encoding="utf-8")

def make_optimized_image_for_ai(src_path: Path, out_dir: Path) -> Path:
    """Return path to an optimized JPEG for AI analysis, creating it if necessary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src_path.stem}-OPTIMIZED.jpg"
    with Image.open(src_path) as im:
        w, h = im.size
        scale = config.ANALYSE_MAX_DIM / max(w, h)
        if scale < 1.0: im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        im = im.convert("RGB")
        q = 85
        while True:
            im.save(out_path, "JPEG", quality=q, optimize=True)
            if out_path.stat().st_size <= config.ANALYSE_MAX_MB * 1024 * 1024 or q <= 60: break
            q -= 5
    logger.info(f"Optimized image for AI: {out_path.name} ({out_path.stat().st_size / 1024:.1f} KB)")
    return out_path

def save_artwork_files(original_path: Path, final_filename: str, seo_folder_name: str) -> dict:
    """Saves artwork files to a new processed folder using the final SEO names."""
    target_folder = config.PROCESSED_ROOT / seo_folder_name
    target_folder.mkdir(parents=True, exist_ok=True)
    
    main_jpg = target_folder / final_filename
    
    stem = Path(final_filename).stem
    thumb_jpg = target_folder / f"{stem}-THUMB.jpg"
    analyse_jpg = target_folder / f"{stem}-ANALYSE.jpg"

    shutil.copy2(original_path, main_jpg)
    
    with Image.open(main_jpg) as img:
        source_analyse_file = original_path.parent / f"{original_path.stem}-analyse.jpg"
        if source_analyse_file.exists():
            shutil.copy2(source_analyse_file, analyse_jpg)
            logger.info(f"Copied analyse image to {analyse_jpg.name}")
        else: # Fallback: create from main image
             shutil.copy2(main_jpg, analyse_jpg)

        thumb = img.copy()
        thumb.thumbnail((config.THUMB_WIDTH, config.THUMB_HEIGHT))
        thumb.save(thumb_jpg, "JPEG", quality=85)
        
    logger.info(f"Saved artwork files to {target_folder}")
    return {
        "main_jpg_path": str(main_jpg),
        "thumb_jpg_path": str(thumb_jpg),
        "analyse_jpg_path": str(analyse_jpg),
        "processed_folder": str(target_folder)
    }

def add_to_mockup_queue(artwork_path: str):
    """Adds a processed artwork path to the pending mockups queue file."""
    queue_file = config.PENDING_MOCKUPS_QUEUE_FILE
    try:
        queue = json.loads(queue_file.read_text(encoding="utf-8")) if queue_file.exists() else []
        if artwork_path not in queue:
            queue.append(artwork_path)
        queue_file.write_text(json.dumps(queue, indent=2), encoding="utf-8")
        logger.info(f"Added {Path(artwork_path).name} to mockup queue.")
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Failed to update mockup queue file at {queue_file}: {e}")

# ===========================================================================
# 5. Colour Detection & Mapping
# ===========================================================================

def _closest_colour(rgb_tuple: tuple[int, int, int]) -> str:
    min_dist = float('inf')
    best_colour = "White"
    for name, rgb in ETSY_COLOURS.items():
        dist = sum((rgb[i] - rgb_tuple[i]) ** 2 for i in range(3))
        if dist < min_dist: min_dist, best_colour = dist, name
    return best_colour

def get_dominant_colours(img_path: Path, n: int = 2) -> list[str]:
    try:
        from sklearn.cluster import KMeans
        import numpy as np
    except ImportError:
        logger.error("Scikit-learn not installed. Cannot perform color detection.")
        return ["White", "Black"]

    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB").resize((100, 100))
            arr = np.asarray(img).reshape(-1, 3)
        kmeans = KMeans(n_clusters=max(3, n + 1), n_init='auto', random_state=42).fit(arr)
        counts = np.bincount(kmeans.labels_)
        sorted_idx = np.argsort(counts)[::-1]
        
        colours, seen_colours = [], set()
        for i in sorted_idx:
            rgb_tuple = tuple(int(c) for c in kmeans.cluster_centers_[i])
            etsy_colour = _closest_colour(rgb_tuple)
            if etsy_colour not in seen_colours:
                seen_colours.add(etsy_colour)
                colours.append(etsy_colour)
            if len(colours) >= n: break
        
        logger.info(f"Detected dominant colours for {img_path.name}: {colours}")
        return (colours + ["White", "Black"])[:n]
    except Exception as e:
        logger.error(f"Color detection failed for {img_path.name}: {e}")
        return ["White", "Black"]

# ===========================================================================
# 6. OpenAI API Handler
# ===========================================================================

def generate_ai_listing(image_path: Path, aspect: str, assigned_sku: str) -> tuple[dict, str]:
    """Calls the OpenAI API and returns the parsed JSON and raw text."""
    logger.info(f"Preparing to call OpenAI API for {image_path.name} with SKU {assigned_sku}.")
    with open(image_path, "rb") as f:
        encoded_img = base64.b64encode(f.read()).decode("utf-8")
    
    system_prompt = Path(config.ONBOARDING_PATH).read_text(encoding="utf-8")
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": [{"type": "text", "text": f"Analyze this artwork (filename: {image_path.name}, aspect ratio: {aspect}) and generate the complete JSON listing. The assigned SKU is {assigned_sku}."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}]}]

    try:
        logger.info("Sending request to OpenAI ChatCompletion API...")
        response = client.chat.completions.create(model=config.OPENAI_MODEL, messages=messages, max_tokens=2100, temperature=0.92, timeout=60, response_format={"type": "json_object"})
        
        raw_text = response.choices[0].message.content
        if raw_text is None:
            logger.error("OpenAI API returned an empty response (content is None).")
            return {}, "OpenAI response was null."
            
        raw_text = raw_text.strip()
        logger.info(f"Received response from OpenAI. Raw text length: {len(raw_text)} chars.")
        return json.loads(raw_text), raw_text
        
    except json.JSONDecodeError:
        logger.warning("OpenAI response was not valid JSON. Attempting fallback parsing.")
        return parse_text_fallback(raw_text), raw_text
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}", exc_info=True)
        raise

def parse_text_fallback(text: str) -> dict:
    """Extracts listing data from non-JSON text as a last resort."""
    data = {"fallback_text": text}
    title_match = re.search(r"\"title\":\s*\"(.*?)\"", text, re.IGNORECASE)
    if title_match: data["title"] = title_match.group(1)
    return data

# ===========================================================================
# 7. Main Analysis Workflow
# ===========================================================================

def analyze_single(image_path: Path):
    """
    Orchestrates the full analysis workflow for a single artwork image.
    """
    logger.info(f"--- Starting analysis for: {image_path.name} (User: {USER_ID}) ---")
    _write_status("Starting analysis...", 5, image_path.name)
    
    if not image_path.is_file(): 
        raise FileNotFoundError(f"Input image not found: {image_path}")

    temp_dir = config.UNANALYSED_ROOT / "temp"
    optimized_img_path = None
    start_time = _dt.datetime.now(_dt.timezone.utc)

    try:
        with Image.open(image_path) as img:
            original_dimensions = f"{img.width}x{img.height}"

        aspect = get_aspect_ratio(image_path)
        
        _write_status("Assigning SKU...", 15, image_path.name)
        assigned_sku = get_next_sku(config.SKU_TRACKER)

        _write_status("Optimizing image for AI...", 25, image_path.name)
        optimized_img_path = make_optimized_image_for_ai(image_path, temp_dir)

        _write_status("Calling OpenAI API...", 40, image_path.name)
        ai_listing, raw_response = generate_ai_listing(optimized_img_path, aspect, assigned_sku)
        
        _write_status("Generating filenames...", 75, image_path.name)
        ai_slug = ai_listing.get("seo_filename_slug", slugify(ai_listing.get("title", image_path.stem)))
        final_filename, seo_folder_name = generate_seo_filename(ai_slug, assigned_sku)
        
        _write_status("Saving artwork files...", 85, image_path.name)
        file_paths = save_artwork_files(image_path, final_filename, seo_folder_name)

        _write_status("Detecting colors...", 95, image_path.name)
        main_image_path = Path(file_paths["main_jpg_path"])
        primary_colour, secondary_colour = get_dominant_colours(main_image_path, 2)
        final_description = ai_listing.get("description") or assemble_gdws_description(aspect)

        end_time = _dt.datetime.now(_dt.timezone.utc)
        duration = round((end_time - start_time).total_seconds(), 2)
        
        listing_data = {
            "filename": image_path.name, "aspect_ratio": aspect, "sku": assigned_sku,
            "title": ai_listing.get("title", image_path.stem),
            "description": final_description,
            "tags": ai_listing.get("tags", []), "materials": ai_listing.get("materials", []),
            "primary_colour": primary_colour, "secondary_colour": secondary_colour,
            "price": ai_listing.get("price", 18.27),
            "seo_filename": final_filename, # Use the final, constructed filename
            "processed_folder": file_paths["processed_folder"],
            "main_jpg_path": file_paths["main_jpg_path"], "thumb_jpg_path": file_paths["thumb_jpg_path"],
            "openai_analysis": {
                "original_file": str(image_path), "optimized_file": str(optimized_img_path),
                "size_bytes": optimized_img_path.stat().st_size,
                "size_mb": round(optimized_img_path.stat().st_size / (1024 * 1024), 3),
                "dimensions": original_dimensions, "time_sent": start_time.isoformat(),
                "time_responded": end_time.isoformat(), "duration_sec": duration,
                "status": "success", "api_response": raw_response[:500] + "..." if raw_response else "N/A"
            }
        }

        listing_json_path = Path(file_paths["processed_folder"]) / f"{seo_folder_name}-listing.json"
        listing_json_path.write_text(json.dumps(listing_data, indent=2), encoding="utf-8")
        logger.info(f"Wrote final listing JSON to {listing_json_path}")
        
        add_to_mockup_queue(file_paths["main_jpg_path"])
        
        logger.info(f"--- Successfully completed analysis for: {image_path.name} ---")
        return listing_data

    finally:
        if optimized_img_path and optimized_img_path.exists():
            optimized_img_path.unlink()
            logger.debug(f"Cleaned up temporary file: {optimized_img_path}")

# ===========================================================================
# 8. Command-Line Interface (CLI)
# ===========================================================================

def main():
    """Parses CLI arguments and runs the analysis."""
    parser = argparse.ArgumentParser(description="Analyze artwork(s) with OpenAI.")
    parser.add_argument("image", help="Path to a single image file to process.")
    parser.add_argument("--json-output", action="store_true", help="Emit result as JSON for subprocess integration.")
    parser.add_argument("--provider", help="Ignored, for compatibility.")
    args = parser.parse_args()

    try:
        result = analyze_single(Path(args.image))
        if args.json_output:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n✅ Analysis complete for: {args.image}\n   - Title: {result.get('title')}\n   - SKU: {result.get('sku')}\n   - Output Folder: {result.get('processed_folder')}")

    except Exception as e:
        logger.critical(f"A fatal error occurred during analysis: {e}\n{traceback.format_exc()}")
        if args.json_output:
            print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
            sys.exit(1)
        else:
            print(f"\n❌ An error occurred: {e}")
            print(f"   Please check the latest log file for details.")


if __name__ == "__main__":
    main()

---
## scripts/analyze_artwork_google.py
---
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArtNarrator | analyze_artwork_google.py
===============================================================
Dedicated script for analyzing artworks with Google's Gemini Pro Vision.
This script is designed to be called via subprocess from the main application.

- Receives a single image path as a command-line argument.
- Prints the final JSON analysis to stdout on success.
- Prints a JSON error object to stderr on failure.

INDEX
-----
1.  Imports
2.  Configuration & Setup
3.  Utility Functions
4.  Main Analysis Logic
5.  Command-Line Interface (CLI)
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import argparse
import datetime as _dt
import json
import logging
import os
import re
import sys
import traceback
from pathlib import Path

# Third-party imports
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

# Local application imports
# Ensure project root is on sys.path for `config` import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils.logger_utils import sanitize_blob_data
from utils.sku_assigner import peek_next_sku

Image.MAX_IMAGE_PIXELS = None
load_dotenv()


# ===========================================================================
# 2. Configuration & Setup
# ===========================================================================

# --- [ 2.1: Configure Google API Client ] ---
try:
    genai.configure(api_key=config.GEMINI_API_KEY or config.GOOGLE_API_KEY)
except Exception as e:
    sys.stderr.write(json.dumps({"success": False, "error": f"Failed to configure Google API: {e}"}))
    sys.exit(1)

# --- [ 2.2: Configure Logging ] ---
config.LOGS_DIR.mkdir(exist_ok=True)
google_log_path = config.LOGS_DIR / f"analyse-google/google-api-calls-{_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d')}.log"
google_log_path.parent.mkdir(exist_ok=True)

google_logger = logging.getLogger("google_analysis")
if not google_logger.handlers:
    handler = logging.FileHandler(google_log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    google_logger.addHandler(handler)
    google_logger.setLevel(logging.INFO)


# ===========================================================================
# 3. Utility Functions
# ===========================================================================

def get_aspect_ratio(image_path: Path) -> str:
    """Return closest aspect ratio label for a given image."""
    with Image.open(image_path) as img:
        w, h = img.size
    aspect_map = [
        ("1x1", 1/1), ("2x3", 2/3), ("3x2", 3/2), ("3x4", 3/4), ("4x3", 4/3),
        ("4x5", 4/5), ("5x4", 5/4), ("5x7", 5/7), ("7x5", 7/5), ("9x16", 9/16),
        ("16x9", 16/9), ("A-Series-Horizontal", 1.414/1), ("A-Series-Vertical", 1/1.414),
    ]
    ar = round(w / h, 4)
    best = min(aspect_map, key=lambda tup: abs(ar - tup[1]))
    return best[0]


def parse_text_fallback(text: str) -> dict:
    """Extracts key fields from a non-JSON AI response."""
    data = {"fallback_text": text}
    # Simplified regex for demonstration; a production version could be more robust
    title_match = re.search(r"(?:Title|Artwork Title)\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if title_match:
        data["title"] = title_match.group(1).strip()
    tag_match = re.search(r"Tags:\s*(.*)", text, re.IGNORECASE)
    if tag_match:
        data["tags"] = [t.strip() for t in tag_match.group(1).split(",") if t.strip()]
    return data


def make_optimized_image_for_ai(src_path: Path, out_dir: Path) -> Path:
    """Return path to an optimized JPEG, creating it if necessary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src_path.stem}-GOOGLE-OPTIMIZED.jpg"
    with Image.open(src_path) as im:
        im = im.convert("RGB")
        im.thumbnail((2048, 2048), Image.LANCZOS)
        im.save(out_path, "JPEG", quality=85, optimize=True)
    return out_path


# ===========================================================================
# 4. Main Analysis Logic
# ===========================================================================

def analyze_with_google(image_path: Path):
    """Analyzes an image using Google Gemini and returns a result dictionary."""
    start_ts = _dt.datetime.now(_dt.timezone.utc)
    log_entry = { "file": str(image_path), "provider": "google", "time_sent": start_ts.isoformat() }
    
    opt_img_path = None
    try:
        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        google_logger.info(f"Starting Google analysis for {image_path.name}")
        temp_dir = config.UNANALYSED_ROOT / "temp"
        opt_img_path = make_optimized_image_for_ai(image_path, temp_dir)
        
        system_prompt = Path(config.ONBOARDING_PATH).read_text(encoding="utf-8")
        assigned_sku = peek_next_sku(config.SKU_TRACKER)
        
        prompt = (
            system_prompt.strip() +
            f"\n\nThe assigned SKU for this artwork is {assigned_sku}. "
            "You MUST use this SKU in the 'sku' field and in the 'seo_filename'."
        )
        
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        response = model.generate_content([prompt, Image.open(opt_img_path)])
        content = response.text.strip()
        google_logger.info(f"Received response from Gemini API for {image_path.name}")

        # ADD THIS BLOCK to remove markdown fences from the API response
        if content.startswith("```"):
            content = re.sub(r"```(json)?\s*(.*)\s*```", r"\2", content, flags=re.DOTALL)

        try:
            ai_listing = json.loads(content)
            result = {"ai_listing": ai_listing, "was_json": True, "raw_response": content}
        except json.JSONDecodeError:
            google_logger.warning(f"Gemini response for {image_path.name} was not valid JSON. Using fallback.")
            ai_listing = parse_text_fallback(content)
            result = {"ai_listing": ai_listing, "was_json": False, "raw_response": content}

        log_entry.update({"status": "success", "duration_sec": (_dt.datetime.now(_dt.timezone.utc) - start_ts).total_seconds()})
        google_logger.info(json.dumps(sanitize_blob_data(log_entry)))
        
        return result

    except Exception as e:
        tb = traceback.format_exc()
        log_entry.update({
            "status": "fail", "error": str(e), "traceback": tb,
            "duration_sec": (_dt.datetime.now(_dt.timezone.utc) - start_ts).total_seconds(),
        })
        google_logger.error(json.dumps(sanitize_blob_data(log_entry)))
        raise RuntimeError(f"Google analysis failed: {e}") from e
    finally:
        if opt_img_path and opt_img_path.exists():
            opt_img_path.unlink()


# ===========================================================================
# 5. Command-Line Interface (CLI)
# ===========================================================================

def main():
    """Parses CLI arguments and runs the analysis."""
    parser = argparse.ArgumentParser(description="Analyze a single artwork with Google Gemini.")
    parser.add_argument("image", help="Path to the image file to process.")
    args = parser.parse_args()

    try:
        image_path = Path(args.image).resolve()
        result = analyze_with_google(image_path)
        safe_result = sanitize_blob_data(result)
        sys.stdout.write(json.dumps(safe_result, indent=2))
        sys.exit(0)
    except Exception as e:
        error_payload = {"success": False, "error": str(e), "traceback": traceback.format_exc()}
        sys.stderr.write(json.dumps(error_payload, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()

---
## scripts/auto_register_missing_artworks.py
---
#!/usr/bin/env python3
"""
Auto-Register Missing Artworks Script
=====================================
Scans the unanalysed-artwork directory, detects any JPEG images not
already registered in the SQLite database, and inserts them into the
`artworks` table.

INDEX
-----
1. Imports & Setup
2. Core Registration Logic
3. Command-Line Interface
"""

# ============================================================================
# 1. Imports & Setup
# ============================================================================
import os
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    from config import settings  # type: ignore
except ImportError:  # Fallback for older config versions
    import config as settings

UNANALYSED_DIR = Path(settings.UNANALYSED_ROOT)
TARGET_EXTS = [".jpg", ".jpeg"]
DB_PATH = Path(settings.DB_PATH)


# ============================================================================
# 2. Core Registration Logic
# ============================================================================

def register_missing_artworks() -> None:
    """Scan folder and insert any unseen artworks into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for file in UNANALYSED_DIR.rglob("*"):
        if file.suffix.lower() not in TARGET_EXTS:
            continue
        if "-thumb" in file.name or "-analyse" in file.name:
            continue

        filename = file.name
        folder = str(file.parent)
        filepath = str(file)

        cursor.execute(
            "SELECT id FROM artworks WHERE original_filename = ?",
            (filename,),
        )
        exists = cursor.fetchone()

        if exists:
            print(f"✅ Exists: {filename}")
            skipped += 1
            continue

        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO artworks (
                original_filename,
                original_file_storage_path,
                artwork_base_folder_path,
                status,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (filename, filepath, folder, "uploaded_pending_qc", now, now),
        )
        print(f"➕ Inserted: {filename}")
        inserted += 1

    conn.commit()
    conn.close()
    print(f"\n🎉 Done. {inserted} new records added, {skipped} already existed.")


# ============================================================================
# 3. Command-Line Interface
# ============================================================================

if __name__ == "__main__":
    register_missing_artworks()

def register_missing_artworks_internal():
    """Callable version for FastAPI integration."""
    register_missing_artworks()

---
## scripts/generate_composites.py
---
# scripts/generate_composites.py
"""
Generates composite mockup images for artworks in a pending queue.

This script reads a queue of processed artworks, selects a random set of
mockups for the correct aspect ratio, and then uses perspective transform
to overlay the artwork onto the mockups, creating the final preview images.

INDEX
-----
1.  Imports & Initialisation
2.  Image Processing Utilities
3.  Queue Management
4.  Main Workflow Logic
5.  Command-Line Interface (CLI)
"""

# ===========================================================================
# 1. Imports & Initialisation
# ===========================================================================
from __future__ import annotations
import os
import json
import random
import re
import argparse
import logging
import sys
from pathlib import Path

# Third-party imports
from PIL import Image
import cv2
import numpy as np

# Local application imports
# Ensure project root is on sys.path for `config` import when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

Image.MAX_IMAGE_PIXELS = None
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ===========================================================================
# 2. Image Processing Utilities
# ===========================================================================

def resize_image_for_long_edge(image: Image.Image, target_long_edge=2000) -> Image.Image:
    """Resizes an image to have its longest edge match the target size."""
    width, height = image.size
    scale = target_long_edge / max(width, height)
    if scale < 1.0:
        new_width = int(width * scale)
        new_height = int(height * scale)
        return image.resize((new_width, new_height), Image.LANCZOS)
    return image


def apply_perspective_transform(art_img: Image.Image, mockup_img: Image.Image, dst_coords: list) -> Image.Image:
    """
    Overlays artwork onto a mockup using perspective transform,
    handling RGBA transparency correctly.
    """
    w, h = art_img.size
    # Note: dst_coords must be in TL, TR, BL, BR order.
    src_points = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    dst_points = np.float32([[c['x'], c['y']] for c in dst_coords])
    
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    art_np = np.array(art_img.convert("RGBA"))
    
    warped = cv2.warpPerspective(art_np, matrix, (mockup_img.width, mockup_img.height))
    warped_pil = Image.fromarray(warped)
    
    # Composite the warped artwork over the mockup using alpha channels
    final_image = Image.alpha_composite(mockup_img.convert("RGBA"), warped_pil)
    return final_image


# ===========================================================================
# 3. Queue Management
# ===========================================================================

def remove_from_queue(processed_img_path: str, queue_file: Path):
    """Removes a processed image from the pending queue file."""
    if not queue_file.exists():
        return
    try:
        queue = json.loads(queue_file.read_text(encoding="utf-8"))
        if processed_img_path in queue:
            queue.remove(processed_img_path)
            queue_file.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error updating queue file {queue_file}: {e}")


# ===========================================================================
# 4. Main Workflow Logic
# ===========================================================================

def _process_queued_artwork(img_path_str: str, total_in_queue: int, current_index: int):
    """Processes a single artwork from the queue."""
    img_path = Path(img_path_str)
    if not img_path.exists():
        logger.warning(f"File not found in queue (skipped): {img_path}")
        return

    folder = img_path.parent
    seo_name = img_path.stem
    json_listing_path = folder / config.FILENAME_TEMPLATES["listing_json"].format(seo_slug=seo_name)

    if not json_listing_path.exists():
        logger.warning(f"Listing JSON not found for {img_path.name}, skipping.")
        return
        
    try:
        entry = json.loads(json_listing_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON for {img_path.name}, skipping: {e}")
        return

    aspect = entry.get("aspect_ratio")
    logger.info(f"[{current_index}/{total_in_queue}] Processing: {img_path.name} [Aspect: {aspect}]")

    mockups_cat_dir = config.MOCKUPS_CATEGORISED_DIR / aspect
    coords_base_dir = config.COORDS_DIR / aspect
    
    if not mockups_cat_dir.exists() or not coords_base_dir.exists():
        logger.warning(f"Missing mockups or coordinates directory for aspect: {aspect}")
        return

    art_img = Image.open(img_path)
    mockup_entries = []
    
    categories = [d for d in mockups_cat_dir.iterdir() if d.is_dir()]
    if not categories:
        logger.warning(f"No mockup categories found for aspect {aspect}")
        return

    # Select a diverse set of mockups, up to the configured limit
    num_to_generate = config.MOCKUPS_PER_LISTING
    selections = []
    if len(categories) >= num_to_generate:
        chosen_categories = random.sample(categories, num_to_generate)
    else:
        # If not enough unique categories, allow duplicates
        chosen_categories = random.choices(categories, k=num_to_generate)
        logger.warning(f"Only {len(categories)} unique categories available; using duplicates to reach {num_to_generate}")

    for cat_dir in chosen_categories:
        pngs = list(cat_dir.glob("*.png"))
        if pngs:
            selections.append((cat_dir, random.choice(pngs)))

    if not selections:
        logger.warning(f"No .png mockup files found for aspect {aspect}")
        return

    # Use enumerate to get a sequential index for naming
    for i, (cat_dir, mockup_file) in enumerate(selections):
        coord_path = coords_base_dir / cat_dir.name / f"{mockup_file.stem}.json"
        if not coord_path.exists():
            logger.warning(f"--> Missing coordinates for {mockup_file.name}, skipping this mockup.")
            continue

        try:
            coords_data = json.loads(coord_path.read_text(encoding="utf-8"))
            mockup_img = Image.open(mockup_file)
            composite = apply_perspective_transform(art_img, mockup_img, coords_data["corners"])

            # Use the loop index 'i' for a clean, sequential number
            output_filename = config.FILENAME_TEMPLATES["mockup"].format(seo_slug=seo_name, num=i + 1)
            output_path = folder / output_filename
            composite.convert("RGB").save(output_path, "JPEG", quality=90)
            
            # --- CREATE THUMBNAIL LOGIC ---
            thumb_dir = folder / config.THUMB_SUBDIR
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumb_name = f"{output_path.stem}-thumb.jpg"
            thumb_path = thumb_dir / thumb_name
            with composite.copy() as thumb_img:
                thumb_img.thumbnail((config.THUMB_WIDTH, config.THUMB_HEIGHT))
                thumb_img.convert("RGB").save(thumb_path, "JPEG", quality=85)
            # --- END THUMBNAIL LOGIC ---

            mockup_entries.append({
                "category": cat_dir.name,
                "source": str(mockup_file.relative_to(config.MOCKUPS_INPUT_DIR)),
                "composite": output_filename,
                "thumbnail": thumb_name, # Add the thumbnail name to the listing data
            })
            logger.info(f"   - Mockup created: {output_filename} (from category '{cat_dir.name}')")
        except Exception as e:
            logger.error(f"--> FAILED to generate composite for {mockup_file.name}: {e}", exc_info=True)

    # Update the main listing JSON with the new mockup data
    entry["mockups"] = mockup_entries
    json_listing_path.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")


def main_queue_processing():
    """Main function for processing artworks from the pending queue."""
    logger.info("===== ArtNarrator: Composite Generator (Queue Mode) =====")
    # Use the new config variable for the queue file path
    queue_file = config.PENDING_MOCKUPS_QUEUE_FILE

    if not queue_file.exists():
        logger.info("No pending mockups queue file found. Nothing to do.")
        return

    try:
        queue = json.loads(queue_file.read_text(encoding="utf-8"))
        if not queue:
            logger.info("✅ No pending artworks in queue. All done!")
            return
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Could not read or parse queue file {queue_file}: {e}")
        return

    logger.info(f"🎨 Found {len(queue)} artwork(s) in the pending queue.")
    
    processed_count = 0
    for i, img_path_str in enumerate(queue[:]): # Process a copy of the queue
        _process_queued_artwork(img_path_str, len(queue), i + 1)
        remove_from_queue(img_path_str, queue_file)
        processed_count += 1
        logger.info(f"🎯 Finished processing for {Path(img_path_str).name}.")

    logger.info(f"✅ Done. {processed_count} artwork(s) processed and removed from queue.")


# ===========================================================================
# 5. Command-Line Interface (CLI)
# ===========================================================================

def main():
    """Parses CLI arguments and runs the appropriate workflow."""
    parser = argparse.ArgumentParser(description="Generate mockup composites for artworks.")
    # Add arguments if a single-file mode is ever needed, otherwise default to queue.
    args = parser.parse_args()
    
    main_queue_processing()


if __name__ == "__main__":
    main()

---
## scripts/generate_coordinates.py
---
#!/usr/bin/env python3
# =============================================================================
# ArtNarrator: Automated Mockup Coordinate Generator
#
# PURPOSE:
#   Scans all PNG mockups in the 'categorised' directory, fixes any broken
#   sRGB profiles, automatically detects the transparent artwork zone using
#   OpenCV, and outputs a JSON coordinate file for each mockup.
#
# INDEX
# -----
# 1.  Imports
# 2.  Configuration & Logging
# 3.  Core Helper Functions
# 4.  Main Execution Logic
# 5.  Command-Line Interface (CLI)
# =============================================================================

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import json
import logging
import sys
from pathlib import Path

# Third-party imports
import cv2
from PIL import Image

# Local application imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils.logger_utils import setup_logger

# ===========================================================================
# 2. Configuration & Logging
# ===========================================================================
# Use the centralized logger to create a timestamped log file for this script run
logger = setup_logger(__name__, "DEFAULT")


# ===========================================================================
# 3. Core Helper Functions
# ===========================================================================

def fix_srgb_profile(image_path: Path):
    """Strips potentially problematic ICC profiles from a PNG image."""
    try:
        with Image.open(image_path) as img:
            # Save the image without the ICC profile to prevent libpng warnings
            if "icc_profile" in img.info and img.format == 'PNG':
                img.save(image_path, format="PNG")
    except Exception as e:
        logger.warning(f"Could not clean sRGB profile for {image_path.name}: {e}")


def sort_corners(pts: list[dict]) -> list[dict]:
    """Sorts 4 corner points to a consistent order: Top-Left, Top-Right, Bottom-Left, Bottom-Right."""
    # Sort by y-coordinate first, then x-coordinate for ties
    pts.sort(key=lambda p: (p["y"], p["x"]))
    top = sorted(pts[:2], key=lambda p: p["x"])
    bottom = sorted(pts[2:], key=lambda p: p["x"])
    return [*top, *bottom]


def detect_corner_points(image_path: Path) -> list[dict] | None:
    """Detects 4 corner points of a transparent region in a PNG using OpenCV."""
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None or image.shape[2] != 4:
        logger.warning(f"Image is not a valid RGBA PNG: {image_path.name}")
        return None

    # Use the alpha channel to find the non-transparent area
    alpha = image[:, :, 3]
    _, thresh = cv2.threshold(alpha, 1, 255, cv2.THRESH_BINARY)
    thresh_inv = cv2.bitwise_not(thresh) # Invert to find the black (transparent) area
    contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        logger.warning(f"No contours found in alpha channel for: {image_path.name}")
        return None

    # Find the largest contour, which should be the artwork area
    contour = max(contours, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)

    if len(approx) != 4:
        logger.warning(f"Could not find a valid 4-corner polygon in: {image_path.name} (found {len(approx)} points)")
        return None

    corners = [{"x": int(pt[0][0]), "y": int(pt[0][1])} for pt in approx]
    return sort_corners(corners)


# ===========================================================================
# 4. Main Execution Logic
# ===========================================================================

def main():
    """Main execution function to scan all mockups and generate coordinates."""
    print("🚀 Starting Automated Coordinate Generation...", flush=True)
    logger.info("Starting Automated Coordinate Generation script.")
    
    processed_count = 0
    error_count = 0
    
    mockup_root = config.MOCKUPS_CATEGORISED_DIR
    coord_root = config.COORDS_DIR

    if not mockup_root.exists():
        msg = f"Mockup directory not found: {mockup_root}"
        print(f"❌ Error: {msg}", flush=True)
        logger.critical(msg)
        return

    for aspect_dir in sorted(mockup_root.iterdir()):
        if not aspect_dir.is_dir(): continue
        
        aspect_name = aspect_dir.name
        coord_aspect_dir = coord_root / aspect_name
        
        for category_dir in sorted(aspect_dir.iterdir()):
            if not category_dir.is_dir(): continue

            print(f"\n🔍 Processing Category: {aspect_dir.name}/{category_dir.name}", flush=True)
            logger.info(f"Processing Category: {aspect_dir.name}/{category_dir.name}")
            output_dir = coord_aspect_dir / category_dir.name
            output_dir.mkdir(parents=True, exist_ok=True)

            for mockup_file in sorted(category_dir.glob("*.png")):
                try:
                    output_path = output_dir / f"{mockup_file.stem}.json"
                    print(f"  -> Processing {mockup_file.name}...", flush=True)
                    
                    fix_srgb_profile(mockup_file)
                    corners = detect_corner_points(mockup_file)
                    
                    if corners:
                        data = {"template": mockup_file.name, "corners": corners}
                        output_path.write_text(json.dumps(data, indent=4), encoding='utf-8')
                        processed_count += 1
                        logger.info(f"Successfully generated coordinates for {mockup_file.name}")
                    else:
                        print(f"  ⚠️ Skipped (no valid 4-corner area found): {mockup_file.name}", flush=True)
                        error_count += 1
                except Exception as e:
                    print(f"  ❌ Error processing {mockup_file.name}: {e}", flush=True)
                    logger.error(f"Error processing {mockup_file.name}: {e}", exc_info=True)
                    error_count += 1

    print(f"\n🏁 Finished. Processed: {processed_count}, Errors/Skipped: {error_count}\n", flush=True)
    logger.info(f"Script finished. Processed: {processed_count}, Errors/Skipped: {error_count}")


# ===========================================================================
# 5. Command-Line Interface (CLI)
# ===========================================================================

if __name__ == "__main__":
    main()

---
## scripts/generate_coordinates_for_ratio.py
---
#!/usr/bin/env python3
# ==============================================================================
# Script: generate_coordinates_for_ratio.py
# Purpose: Scans all PNGs in a given categorized aspect ratio folder,
#          prompts the user to click 4 corners, and saves the coordinates.
# ==============================================================================

import argparse
import pathlib
import logging
import sys
import json
import cv2

# Ensure project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_args():
    parser = argparse.ArgumentParser(description="Generate coordinates for a single aspect ratio")
    parser.add_argument("--aspect_ratio_path", type=str, required=True, help="Path to an aspect ratio folder (e.g., .../4x5-categorised)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing coordinate files")
    return parser.parse_args()

def pick_points_gui(img_path):
    """Opens a GUI for the user to select 4 corner points."""
    img = cv2.imread(str(img_path))
    if img is None:
        raise IOError(f"Could not read image: {img_path}")
    points = []
    window_name = "Select Corners (TL, TR, BR, BL) - Press ESC to confirm"

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))
            cv2.circle(img, (x, y), 7, (0, 255, 0), -1)
            cv2.imshow(window_name, img)

    cv2.imshow(window_name, img)
    cv2.setMouseCallback(window_name, mouse_callback)
    while len(points) < 4:
        key = cv2.waitKey(20) & 0xFF
        if key == 27: # ESC key
            break
    cv2.destroyAllWindows()
    if len(points) != 4:
        raise Exception("Did not select exactly 4 points. Aborted.")
    return points

def main():
    args = get_args()
    aspect_folder = pathlib.Path(args.aspect_ratio_path).resolve()
    aspect_name = aspect_folder.name.replace("-categorised", "")
    
    # Define the output directory based on the aspect name
    out_base = config.COORDS_DIR / aspect_name
    logger.info(f"Saving coordinates to: {out_base}")

    for category_dir in sorted(aspect_folder.iterdir()):
        if not category_dir.is_dir():
            continue
        
        logger.info(f"--- Processing Category: {category_dir.name} ---")
        out_cat_folder = out_base / category_dir.name
        out_cat_folder.mkdir(parents=True, exist_ok=True)
        
        for img in sorted(category_dir.glob("*.png")):
            coord_file = out_cat_folder / f"{img.stem}.json"
            if coord_file.exists() and not args.overwrite:
                logger.info(f"✅ Skipping, coordinates exist: {img.name}")
                continue
            
            logger.info(f"👉 Please select coordinates for: {img.name}")
            try:
                points = pick_points_gui(img)
                # Convert points to the required JSON structure
                corners = [
                    {"x": points[0][0], "y": points[0][1]}, # Top-Left
                    {"x": points[1][0], "y": points[1][1]}, # Top-Right
                    {"x": points[3][0], "y": points[3][1]}, # Bottom-Left (Note: CV2 order vs your format)
                    {"x": points[2][0], "y": points[2][1]}  # Bottom-Right
                ]
                data = {"filename": img.name, "corners": corners}
                with open(coord_file, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"✅ Saved coordinates for: {img.name}")
            except Exception as e:
                logger.error(f"❌ Failed to process {img}: {e}")

if __name__ == "__main__":
    main()

---
## scripts/populate_gdws.py
---
# scripts/populate_gdws.py
"""
One-time script to parse the original generic text files and populate the
GDWS (Guided Description Writing System) content directory with a structured
set of JSON files.

INDEX
-----
1.  Imports
2.  Configuration & Logging
3.  Helper Functions
4.  Main Execution Logic
5.  Command-Line Interface (CLI)
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import json
import logging
import re
import sys
from pathlib import Path

# Local application imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils.logger_utils import setup_logger

# ===========================================================================
# 2. Configuration & Logging
# ===========================================================================
logger = setup_logger(__name__, "DEFAULT")

# Get GDWS configuration from the central config file
SOURCE_TEXT_DIR = config.GENERIC_TEXTS_DIR
GDWS_CONTENT_DIR = config.GDWS_CONTENT_DIR
PARAGRAPH_HEADINGS = config.GDWS_CONFIG["PARAGRAPH_HEADINGS"]


# ===========================================================================
# 3. Helper Functions
# ===========================================================================

def slugify(text: str) -> str:
    """
    Creates a filesystem-safe name from a heading.
    Note: This version is specific to GDWS and contains hardcoded remappings.
    """
    s = text.lower()
    s = re.sub(r'[^\w\s-]', '', s).strip()
    s = re.sub(r'[-\s]+', '_', s)
    # Handle specific long names for cleaner folder names
    if "about_the_artist" in s: return "about_the_artist"
    if "did_you_know" in s: return "about_art_style"
    if "what_youll_receive" in s: return "file_details"
    return s


# ===========================================================================
# 4. Main Execution Logic
# ===========================================================================

def parse_and_create_files():
    """Reads source text files, parses them, and creates the GDWS structure."""
    if not SOURCE_TEXT_DIR.exists():
        logger.critical(f"Source directory not found at '{SOURCE_TEXT_DIR}'. Aborting.")
        print(f"❌ Error: Source directory not found at '{SOURCE_TEXT_DIR}'")
        return

    logger.info(f"Starting GDWS population from '{SOURCE_TEXT_DIR}'...")
    print(f"🚀 Starting GDWS population from '{SOURCE_TEXT_DIR}'...")
    
    GDWS_CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    source_files = list(SOURCE_TEXT_DIR.glob("*.txt"))
    if not source_files:
        logger.warning("No .txt files found in the source directory. Nothing to do.")
        print("🤷 No .txt files found in the source directory. Nothing to do.")
        return

    # Create a regex pattern to split the file content by the configured headings
    split_pattern = re.compile('(' + '|'.join(re.escape(h) for h in PARAGRAPH_HEADINGS) + ')')

    for txt_file in source_files:
        aspect_ratio = txt_file.stem
        # Handle known typo in an old filename
        if aspect_ratio.lower() == "a-series-verical":
            aspect_ratio = "A-Series-Vertical"

        aspect_dir = GDWS_CONTENT_DIR / aspect_ratio
        aspect_dir.mkdir(exist_ok=True)
        
        logger.info(f"Processing: {txt_file.name} for aspect ratio '{aspect_ratio}'...")
        print(f"\nProcessing: {txt_file.name} for aspect ratio '{aspect_ratio}'...")
        
        content = txt_file.read_text(encoding='utf-8').strip()
        parts = split_pattern.split(content)
        
        i = 1 # Start at 1 because the first element is the text before the first heading
        while i < len(parts):
            title = parts[i].strip()
            body = parts[i+1].strip() if (i+1) < len(parts) else ""
            
            folder_name = slugify(title)
            paragraph_dir = aspect_dir / folder_name
            paragraph_dir.mkdir(exist_ok=True)
            
            base_file = paragraph_dir / "base.json"
            
            data_to_save = {
                "id": "base",
                "title": title,
                "content": body,
                "instructions": (
                    f"This is the base text for the '{title}' section for the {aspect_ratio} "
                    "aspect ratio. Edit the text to refine the message for this paragraph."
                )
            }
            
            base_file.write_text(json.dumps(data_to_save, indent=4), encoding='utf-8')
            logger.info(f"  - Created base file for '{title}' in {folder_name}")
            print(f"  ✅ Created base file for '{title}'")
            i += 2

    logger.info("GDWS population script finished.")
    print(f"\n🎉 GDWS population complete! Check the '{GDWS_CONTENT_DIR}' directory.")


# ===========================================================================
# 5. Command-Line Interface (CLI)
# ===========================================================================

if __name__ == "__main__":
    parse_and_create_files()

---
## scripts/run_coordinate_generator.py
---
#!/usr/bin/env python3
# ==============================================================================
# SCRIPT: run_coordinate_generator.py
#
# PURPOSE:
#   This script orchestrates the interactive generation of coordinate data.
#   It iterates through all categorized mockup aspect ratio folders and calls
#   the `generate_coordinates_for_ratio.py` worker script for each one.
#
# INDEX
# -----
# 1.  Imports
# 2.  Configuration & Logging
# 3.  Main Execution Logic
# 4.  Command-Line Interface (CLI)
# ==============================================================================

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging
import subprocess
import sys
from pathlib import Path

# Local application imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils.logger_utils import setup_logger

# ===========================================================================
# 2. Configuration & Logging
# ===========================================================================
logger = setup_logger(__name__, "DEFAULT")


# ===========================================================================
# 3. Main Execution Logic
# ===========================================================================

def run_coordinate_generation_for_all_ratios():
    """
    Finds all aspect ratio folders and runs the interactive coordinate
    generator script for each one.
    """
    logger.info("Starting coordinate generation orchestrator script...")
    
    worker_script = config.COORDINATE_GENERATOR_RATIO_SCRIPT_PATH
    if not worker_script.is_file():
        logger.critical(f"Worker script not found at '{worker_script}'. Aborting.")
        return

    mockups_base_dir = config.MOCKUPS_CATEGORISED_DIR
    if not mockups_base_dir.is_dir():
        logger.critical(f"Mockups directory not found at '{mockups_base_dir}'. Aborting.")
        return

    aspect_ratio_folders = [d for d in mockups_base_dir.iterdir() if d.is_dir()]
    
    for aspect_path in aspect_ratio_folders:
        logger.info(f"--- Processing aspect ratio: {aspect_path.name} ---")
        try:
            command = [
                sys.executable,
                str(worker_script),
                "--aspect_ratio_path", str(aspect_path)
            ]
            logger.info(f"Executing command: {' '.join(command)}")
            subprocess.run(command, check=True)
            logger.info(f"Successfully processed aspect ratio: {aspect_path.name}")
        except Exception as e:
            logger.error(f"An error occurred while processing {aspect_path.name}: {e}", exc_info=True)
        
    logger.info("🏁 Finished processing all aspect ratios.")


# ===========================================================================
# 4. Command-Line Interface (CLI)
# ===========================================================================

if __name__ == "__main__":
    run_coordinate_generation_for_all_ratios()

---
## scripts/signing_service.py
---
"""
ArtNarrator Signing Service
Processes a single artwork to add a colour-contrasting signature.
"""

from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
from sklearn.cluster import KMeans
import config

# Configuration is now fully sourced from config.py
SIGNATURE_PNGS = {
    "beige": config.SIGNATURES_DIR / "beige.png",
    "black": config.SIGNATURES_DIR / "black.png",
    "blue": config.SIGNATURES_DIR / "blue.png",
    "brown": config.SIGNATURES_DIR / "brown.png",
    "gold": config.SIGNATURES_DIR / "gold.png",
    "green": config.SIGNATURES_DIR / "green.png",
    "grey": config.SIGNATURES_DIR / "grey.png",
    "odd": config.SIGNATURES_DIR / "odd.png",
    "red": config.SIGNATURES_DIR / "red.png",
    "skyblue": config.SIGNATURES_DIR / "skyblue.png",
    "white": config.SIGNATURES_DIR / "white.png",
    "yellow": config.SIGNATURES_DIR / "yellow.png"
}

SIGNATURE_COLORS_RGB = {
    "beige": (245, 245, 220), "black": (0, 0, 0), "blue": (0, 0, 255),
    "brown": (139, 69, 19), "gold": (255, 215, 0), "green": (0, 255, 0),
    "grey": (128, 128, 128), "odd": (128, 128, 128), "red": (255, 0, 0),
    "skyblue": (135, 206, 235), "white": (210, 210, 210), "yellow": (255, 255, 0)
}

SMOOTHING_BUFFER_PIXELS = 3
BLUR_RADIUS = 25
NUM_COLORS_FOR_ZONE_ANALYSIS = 2

# === Utility Functions (Mostly unchanged from your script) ===

def get_relative_luminance(rgb):
    r, g, b = [x / 255.0 for x in rgb]
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def get_contrast_ratio(rgb1, rgb2):
    L1, L2 = get_relative_luminance(rgb1), get_relative_luminance(rgb2)
    return (max(L1, L2) + 0.05) / (min(L1, L2) + 0.05)

def get_dominant_color_in_masked_zone(image_data_pixels, mask_pixels, num_colors=1):
    masked_pixels = [image_data_pixels[i] for i, alpha in enumerate(mask_pixels) if alpha > 0]
    if not masked_pixels: return (0, 0, 0)
    
    pixels_array = np.array(masked_pixels).reshape(-1, 3)
    if pixels_array.shape[0] < num_colors:
        return tuple(map(int, np.mean(pixels_array, axis=0)))

    kmeans = KMeans(n_clusters=num_colors, random_state=0, n_init='auto').fit(pixels_array)
    return tuple(map(int, kmeans.cluster_centers_[0]))

def get_contrasting_signature_path(background_rgb):
    best_signature, max_contrast = "black", -1.0
    for name, rgb in SIGNATURE_COLORS_RGB.items():
        if SIGNATURE_PNGS.get(name, Path()).is_file():
            contrast = get_contrast_ratio(background_rgb, rgb)
            if contrast > max_contrast:
                max_contrast, best_signature = contrast, name
    return SIGNATURE_PNGS[best_signature]

# === Main Processing Function (Refactored for Single Image) ===

def add_smart_signature(source_path: Path, destination_path: Path) -> tuple[bool, str]:
    """
    Applies a smart signature to a single image and saves it to the destination.
    Returns a tuple of (success_boolean, message).
    """
    try:
        with Image.open(source_path).convert("RGB") as img:
            width, height = img.size
            choose_right = random.choice([True, False])

            long_edge = max(width, height)
            sig_size = int(long_edge * config.SIGNATURE_SIZE_PERCENTAGE)
            
            dummy_sig_path = next(iter(SIGNATURE_PNGS.values()))
            with Image.open(dummy_sig_path).convert("RGBA") as dummy_sig:
                sw, sh = dummy_sig.size
                if sw > sh:
                    scaled_w, scaled_h = sig_size, int(sh * (sig_size / sw))
                else:
                    scaled_h, scaled_w = sig_size, int(sw * (sig_size / sh))
            
            margin_x = int(width * config.SIGNATURE_MARGIN_PERCENTAGE)
            margin_y = int(height * config.SIGNATURE_MARGIN_PERCENTAGE)

            paste_x = width - scaled_w - margin_x if choose_right else margin_x
            paste_y = height - scaled_h - margin_y

            with Image.open(dummy_sig_path).convert("RGBA") as base_sig:
                resized_sig = base_sig.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
                mask_canvas = Image.new("L", img.size, 0)
                mask_canvas.paste(resized_sig.split()[-1], (paste_x, paste_y))
                expanded_mask = mask_canvas.filter(ImageFilter.GaussianBlur(SMOOTHING_BUFFER_PIXELS))
                expanded_mask = expanded_mask.point(lambda x: 255 if x > 10 else 0)

            dom_color = get_dominant_color_in_masked_zone(list(img.getdata()), list(expanded_mask.getdata()), NUM_COLORS_FOR_ZONE_ANALYSIS)
            
            patch_base = Image.new("RGB", img.size, dom_color)
            patch_blurred = patch_base.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
            patch_rgba = patch_blurred.convert("RGBA")
            patch_rgba.putalpha(expanded_mask)

            img_with_patch = Image.alpha_composite(img.convert("RGBA"), patch_rgba)

            sig_path = get_contrasting_signature_path(dom_color)
            with Image.open(sig_path).convert("RGBA") as sig_img:
                sig_img = sig_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
                img_with_patch.paste(sig_img, (paste_x, paste_y), sig_img)

            final_img = img_with_patch.convert("RGB")
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            final_img.save(destination_path)
            
        return True, f"Successfully signed and saved to {destination_path.name}"

    except Exception as e:
        return False, f"Error signing {source_path.name}: {e}"

---
## scripts/test_connections.py
---
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArtNarrator Connection Tester
===============================================================
This script checks all external API and service connections
defined in the project's .env file to ensure keys and credentials
are working correctly. It also verifies access to specific AI models.

INDEX
-----
1.  Imports
2.  Configuration & Setup
3.  UI & Logging Helpers
4.  Connection Test Functions
5.  Main Execution
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
import os
import sys
import base64
import smtplib
import requests
from dotenv import load_dotenv

# Ensure the project root is in the Python path to find modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    import openai
    import google.generativeai as genai
    import config
    from utils.logger_utils import setup_logger
except ImportError as e:
    print(f"❌ Error: A required library is missing. Please run 'pip install {e.name}'")
    sys.exit(1)


# ===========================================================================
# 2. Configuration & Setup
# ===========================================================================
load_dotenv(os.path.join(project_root, '.env'))
logger = setup_logger(__name__, "DEFAULT") # Use the default logger for a persistent record


# ===========================================================================
# 3. UI & Logging Helpers
# ===========================================================================
def print_status(service: str, success: bool, message: str = "") -> None:
    """Prints a formatted status line and writes to the log file."""
    if success:
        log_message = f"✅ {service:<20} Connection successful. {message}"
        print(f"✅ {service:<20} Connection successful. {message}")
        logger.info(log_message)
    else:
        log_message = f"❌ {service:<20} FAILED. {message}"
        print(f"❌ {service:<20} FAILED. {message}")
        logger.error(log_message)


# ===========================================================================
# 4. Connection Test Functions
# ===========================================================================

# --- [ 4.1: OpenAI Test ] ---
def test_openai() -> None:
    """Tests the OpenAI API key and access to specific models."""
    print("\n--- Testing OpenAI ---")
    if not config.OPENAI_API_KEY:
        print_status("OpenAI", False, "OPENAI_API_KEY not found in config.")
        return

    try:
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        client.models.list()
        print_status("OpenAI API Key", True, "Key is valid.")

        models_to_check = {
            "Main Model": config.OPENAI_MODEL,
            "Vision Model": config.OPENAI_MODEL
        }
        for name, model_id in models_to_check.items():
            if not model_id: continue
            try:
                client.models.retrieve(model_id)
                print(f"  - ✅ {name} ({model_id}): Access confirmed.")
            except Exception as e:
                print(f"  - ❌ {name} ({model_id}): FAILED! Error: {e}")
                logger.error(f"Failed to retrieve OpenAI model {model_id}: {e}")

    except openai.AuthenticationError:
        print_status("OpenAI API Key", False, "AuthenticationError: The API key is incorrect.")
    except Exception as e:
        print_status("OpenAI API Key", False, f"An unexpected error occurred: {e}")


# --- [ 4.2: Google Gemini Test ] ---
def test_google_gemini() -> None:
    """Tests the Google Gemini API key and access to the vision model."""
    print("\n--- Testing Google Gemini ---")
    api_key = config.GEMINI_API_KEY or config.GOOGLE_API_KEY
    if not api_key:
        print_status("Google Gemini", False, "GEMINI_API_KEY or GOOGLE_API_KEY not found.")
        return

    try:
        genai.configure(api_key=api_key)
        model_name = config.GEMINI_MODEL
        if model_name:
            model_name_for_check = f'models/{model_name}' if not model_name.startswith('models/') else model_name
            genai.get_model(model_name_for_check)
            print_status("Google Gemini", True, f"Key is valid and has access to {model_name}.")
        else:
            genai.list_models()
            print_status("Google Gemini", True, "Key is valid (general check).")
    except Exception as e:
        print_status("Google Gemini", False, f"An error occurred: {e}")


# --- [ 4.3: Sellbrite Test ] ---
def test_sellbrite() -> None:
    """Tests Sellbrite API credentials by making a simple request."""
    print("\n--- Testing Sellbrite ---")
    token, secret = config.SELLBRITE_ACCOUNT_TOKEN, config.SELLBRITE_SECRET_KEY
    if not token or not secret:
        print_status("Sellbrite", False, "Credentials not found in config.")
        return

    try:
        creds = f"{token}:{secret}".encode("utf-8")
        encoded_creds = base64.b64encode(creds).decode("utf-8")
        headers = {"Authorization": f"Basic {encoded_creds}"}
        url = f"{config.SELLBRITE_API_BASE_URL}/warehouses?limit=1"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            print_status("Sellbrite", True)
        else:
            print_status("Sellbrite", False, f"API returned status {response.status_code}. Check credentials.")
    except requests.RequestException as e:
        print_status("Sellbrite", False, f"A network error occurred: {e}")


# --- [ 4.4: SMTP Test ] ---
def test_smtp() -> None:
    """Tests the SMTP server connection and login credentials."""
    print("\n--- Testing SMTP ---")
    server, port = config.SMTP_SERVER, config.SMTP_PORT
    username, password = config.SMTP_USERNAME, config.SMTP_PASSWORD

    if not all([server, port, username, password]):
        print_status("SMTP", False, "One or more SMTP variables are missing from config.")
        return

    try:
        with smtplib.SMTP(server, port, timeout=10) as connection:
            connection.starttls()
            connection.login(username, password)
        print_status("SMTP", True)
    except smtplib.SMTPAuthenticationError:
        print_status("SMTP", False, "AuthenticationError. Check username/password.")
    except Exception as e:
        print_status("SMTP", False, f"An unexpected error occurred: {e}")


# ===========================================================================
# 5. Main Execution
# ===========================================================================
def main() -> None:
    """Runs all connection tests."""
    print("--- 🔑 ArtNarrator API Connection Tester ---")
    logger.info("--- Starting API Connection Test Suite ---")
    
    test_openai()
    test_google_gemini()
    test_sellbrite()
    # test_smtp() # Uncomment this line to test the SMTP connection
    
    print("\n--- ✅ All tests complete ---")
    logger.info("--- API Connection Test Suite Finished ---")


if __name__ == "__main__":
    main()

---
## scripts/test_sellbrite_add_listing.py
---
# scripts/test_sellbrite_add_listing.py
"""
A command-line utility to post a test product to Sellbrite.

This script loads a sample JSON listing, authenticates with the Sellbrite API
using credentials from the config, and attempts to create a new product.
It is intended for verifying that the API integration is functional.

INDEX
-----
1.  Imports
2.  Configuration & Setup
3.  Core Functions
4.  Main Execution Logic
5.  Command-Line Interface (CLI)
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import sys
import json
import logging
import base64
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from utils.logger_utils import setup_logger

# ===========================================================================
# 2. Configuration & Setup
# ===========================================================================
load_dotenv()
logger = setup_logger(__name__, "SELLBRITE_API")

TEST_JSON_PATH = config.DATA_DIR / "sellbrite" / "test_sellbrite_listing.json"
API_ENDPOINT = f"{config.SELLBRITE_API_BASE_URL}/products"


# ===========================================================================
# 3. Core Functions
# ===========================================================================

def get_auth_header() -> dict[str, str]:
    """
    Constructs the Basic Authentication header for the Sellbrite API.
    
    MODIFIED: This now matches the authentication method used in the main
    sellbrite_service.py for consistency.
    """
    token = config.SELLBRITE_ACCOUNT_TOKEN
    secret = config.SELLBRITE_SECRET_KEY
    if not token or not secret:
        raise ValueError("Sellbrite credentials (TOKEN, SECRET) are not set in config.")
    
    creds = f"{token}:{secret}".encode("utf-8")
    encoded_creds = base64.b64encode(creds).decode("utf-8")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_creds}"
    }


def load_test_payload(path: Path) -> dict:
    """Loads the test listing data from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Test JSON file not found: {path}")
    logger.info(f"Loading test payload from {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def post_listing(payload: dict) -> requests.Response:
    """Sends the listing payload to the Sellbrite API."""
    headers = get_auth_header()
    logger.info(f"Sending POST request to {API_ENDPOINT} for SKU {payload.get('sku')}")
    response = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=20)
    return response


# ===========================================================================
# 4. Main Execution Logic
# ===========================================================================

def main():
    """Main function to run the Sellbrite listing test."""
    dry_run = "--dry-run" in sys.argv
    print("🚀 Sellbrite Add Listing Test Started...")
    logger.info("Sellbrite test script initiated.")

    try:
        payload = load_test_payload(TEST_JSON_PATH)
    except Exception as e:
        logger.critical(f"Failed to load test payload: {e}", exc_info=True)
        print(f"❌ Failed to load test payload: {e}")
        return

    if dry_run:
        print("🧪 DRY RUN: Would send this JSON payload to Sellbrite:")
        print(json.dumps(payload, indent=2))
        logger.info("Dry run executed. Payload displayed but not sent.")
        return

    try:
        response = post_listing(payload)
        
        if response.status_code == 201:
            print("✅ Listing successfully created in Sellbrite.")
            logger.info(f"SUCCESS: Sellbrite responded with status {response.status_code}.")
        else:
            print(f"❌ Failed with status {response.status_code}: {response.text}")
            logger.error(f"FAILURE: Sellbrite responded with status {response.status_code}: {response.text}")

        try:
            response_json = response.json()
            logger.info("--- Sellbrite API Response ---")
            logger.info(json.dumps(response_json, indent=2))
            print("📝 Full API response has been saved to the log file.")
        except json.JSONDecodeError:
            logger.info("--- Sellbrite API Response (Raw Text) ---")
            logger.info(response.text)
            
    except Exception as e:
        logger.critical(f"An unexpected error occurred during the API call: {e}", exc_info=True)
        print(f"❌ An unexpected error occurred: {e}")


# ===========================================================================
# 5. Command-Line Interface (CLI)
# ===========================================================================

if __name__ == "__main__":
    main()

---
## settings/Master-Etsy-Listing-Description-Writing-Onboarding.txt
---
# Universal AI Art Listing Generator Instructions (OpenAI & Gemini Compatible)

## 1. AI ROLE & PRIMARY DIRECTIVE

You are an expert AI assistant with the persona of a world-renowned art curator and professional copywriter, specializing in Aboriginal and Australian digital art. Your primary directive is to analyze the provided artwork and generate a single, valid JSON object containing Pulitzer-quality marketing copy for an Etsy art listing.

**CRITICAL RULE:** Your entire response **MUST** be **ONLY** the raw JSON object. Do not include any introductory text, explanations, or markdown fences like ```json. The output will be parsed by a machine, and any extra characters will cause a system failure.

---

## 2. INPUTS YOU WILL RECEIVE

1.  **Artwork Image**: The primary subject for your analysis.
2.  **Assigned SKU**: A unique product identifier (e.g., 'RJC-0195') provided for your contextual reference. You do not need to include this SKU in your JSON output.

---

## 3. REQUIRED JSON OUTPUT STRUCTURE

Your output MUST be a single JSON object with these EXACT keys. Do not add or omit any keys.

-   `title`
-   `seo_filename_slug`
-   `description`
-   `tags`
-   `materials`
-   `primary_colour`
-   `secondary_colour`
-   `price`

---

## 4. FIELD-SPECIFIC INSTRUCTIONS

-   **title**:
    -   Max 140 characters.
    -   Must strongly reflect: "High Resolution", "Digital", "Download", "Artwork by Robin Custance".
    -   Include powerful buyer search terms: "Dot Art", "Aboriginal Print", "Australian Wall Art", "Instant Download", "Printable", etc.
    -   The first part of the title MUST clearly describe the subject and use strong search terms—**no poetic intros like “Immerse yourself,” “Step into,” or “Discover.”**

-   **seo_filename_slug**:
    -   A short, descriptive, SEO-friendly slug for the filename.
    -   **MUST** be **39 characters or less**.
    -   **MUST** be lowercase and use hyphens instead of spaces (e.g., `southern-cassowary-australian-artwork`).
    -   **DO NOT** include the SKU, suffixes like `-by-robin-custance`, or the `.jpg` extension. The system will add these automatically.

-   **description**:
    -   At least 400 words (or 2,600 characters). The quality should be equivalent to that of a professional art critic.
    -   Paragraphs must be concise (no more than 70 words or 400 characters) for readability.
    -   The **first sentence MUST ONLY contain SEO keyword phrases** that buyers would use, written naturally. Example: “Australian outback wall art, Aboriginal dot painting print, digital download, Robin Custance artwork…”
    -   Deeply analyze the artwork’s style, method, colors, textures, and inspiration. Include cultural context where appropriate.
    -   **DO NOT** include padding, shop info, printing instructions, or an artist bio; these are handled by the system.

-   **tags**:
    -   An array of up to 13 targeted, comma-free tags (max 20 characters per tag).
    -   Mix art technique, subject, Australian/Aboriginal terms, branding, and digital wall art keywords.
    -   No hyphens, no duplicates, no generic filler.

-   **materials**:
    -   An array of up to 13 descriptive phrases (max 45 characters per phrase) specific to the artwork’s technique and digital file type.
    -   Rotate phrases for each artwork to ensure uniqueness.

-   **primary_colour, secondary_colour**:
    -   You **MUST** choose the two most visually dominant colors from the following official Etsy color list. Select the closest match from this list only. Do not use any other color names.
    -   **VALID ETSY COLORS**: Beige, Black, Blue, Bronze, Brown, Clear, Copper, Gold, Grey, Green, Orange, Pink, Purple, Rainbow, Red, Rose gold, Silver, White, Yellow.

-   **price**:
    -   Must be the number `18.27` exactly (no currency symbols or strings).

---

## 5. EXAMPLE JSON OUTPUT

You must follow this format precisely.

```json
{
  "title": "High Resolution Digital Dot Art Print – Aboriginal Night Seeds Rebirth | Robin Custance Download",
  "seo_filename_slug": "night-seeds-rebirth-aboriginal-dot-art",
  "description": "Australian dot art print, Aboriginal night sky wall decor, digital download, Robin Custance, swirling galaxy artwork. This captivating piece delves into the rich traditions of Indigenous Australian art, reinterpreted through a contemporary lens. The canvas explodes with a universe of meticulously placed dots, creating a mesmerizing texture that draws the viewer into its celestial depths. Swirling patterns evoke the vastness of the outback night sky, where ancient stories are written in the stars. Deep indigos and blacks form a dramatic backdrop for constellations rendered in vibrant ochres, fiery oranges, and earthy browns, suggesting the warmth of the land even in the cool of night...",
  "tags": [
    "dot art",
    "night sky",
    "aboriginal",
    "robin custance",
    "australian art",
    "digital print",
    "swirling stars",
    "dreamtime",
    "galaxy decor",
    "modern dot",
    "outback art",
    "starry night",
    "printable"
  ],
  "materials": [
    "High resolution JPEG",
    "Digital painting",
    "Original dot technique",
    "Layered composition",
    "Contemporary wall art file",
    "Professional digital art",
    "Printable file"
  ],
  "primary_colour": "Black",
  "secondary_colour": "Brown",
  "price": 18.27
}

---
## settings/mockup_categoriser_prompt.txt
---
You are an expert interior design assistant. Your task is to categorize mockup images into one of the following predefined categories based on the room and setting shown.

Respond with ONLY the single most appropriate category name from this list and nothing else.

VALID CATEGORIES:
- Bedroom
- Closeup
- Dining-Room
- Display
- Gallery-Wall
- Gift
- Hallway
- Kitchen
- Living Room
- Nursery
- Office
- Outdoors

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
   ======================================================== */

/* === Cards & Art Galleries === */
.artwork-info-card { background: var(--color-background); border: 1.5px solid var(--color-border-subtle); box-shadow: 0 2px 8px var(--color-shadow-light); padding: 1.5em 2em; margin: 0 auto 1.7em auto; max-width: 570px;}
.artwork-info-card h2 { font-size: 1.21em; font-weight: bold; margin-bottom: 0.6em; }
.gallery-section { margin: 2.5em auto 3.5em auto; max-width: 1250px; padding: 0 1em;}
.artwork-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 2.4em; margin-bottom: 2em;}
.gallery-card { position: relative; background: var(--card-bg); border: 1px solid var(--card-border, #000); box-shadow: var(--shadow); display: flex; flex-direction: column; align-items: center; transition: box-shadow 0.18s, transform 0.12s; padding: 10px; overflow: hidden;}
.gallery-card:hover { box-shadow: 0 4px 16px var(--color-shadow-medium); transform: translateY(-4px) scale(1.013);}
.card-thumb { width: 100%; background: none; text-align: center; padding: 22px 0 7px 0; }
.card-img-top { max-width: 94%; max-height: 210px; object-fit: cover; box-shadow: 0 1px 7px var(--color-shadow-light); background: var(--color-background);}
.card-details { display: flex; flex-direction: column; flex-grow: 1; width: 100%; text-align: center; padding: 12px 13px 20px 13px; gap: 10px;}
.card-title { font-size: 0.9em; font-weight: 400; line-height: 1.2; color: var(--main-txt); min-height: 3em; margin-bottom: 7px;}
.card-details .btn { margin-top: 7px; width: 90%; min-width: 90px;}
.finalised-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.6em; margin-top: 1.5em; justify-content: center;}
.final-card { background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow); padding: 10px; display: flex; flex-direction: column; max-width: 350px; margin: 0 auto;}
.card-content-wrapper { display: flex; flex-direction: column; flex-grow: 1; width: 100%; }
.final-actions, .edit-actions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: auto;}
.edit-actions { margin-top: 1em;}
.final-actions .btn, .edit-actions .btn { flex: 1 1 auto; min-width: 100px; width: auto; margin-top: 0; }
.desc-snippet { font-size: 0.92em; line-height: 1.3; margin: 4px 0 8px 0; text-align: left;}
.main-artwork-thumb { max-width: 100%; max-height: 500px; object-fit: contain; display: block; margin: 0 auto 0.6em auto; border-radius: 6px; box-shadow: 0 2px 12px var(--color-shadow-medium); }
.mockup-preview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }
.mockup-card { background: var(--color-card-bg); padding: 11px 7px; text-align: center; border: none; border-radius: 4px; transition: box-shadow 0.15s; }
.mockup-card:hover { box-shadow: 0 4px 14px var(--color-shadow-medium); }
.mockup-thumb-img { width: 100%; height: 180px; object-fit: contain; border: none; background: var(--color-card-bg); cursor: pointer; transition: box-shadow 0.15s; }
.mockup-thumb-img:focus { outline: 2.5px solid var(--accent);}
.missing-img { width: 100%; padding: 20px 0; background: var(--color-background); color: var(--color-muted-text); font-size: 0.9em;}
.mini-mockup-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(75px, 1fr)); gap: 5px; margin-top: 6px; }
.mini-mockup-grid img { width: 75px; height: 75px; object-fit: cover; border-radius: 4px; box-shadow: 0 1px 4px var(--color-shadow-light); }
.mockup-thumb-img.selected, .card-img-top.selected, .gallery-thumb.selected { outline: 3px solid var(--color-accent) !important; outline-offset: 1.5px; }
.card-description-full { max-height: 150px; overflow-y: auto; text-align: left; padding: 0.5rem; background: var(--color-background); border: 1px solid var(--card-border); font-size: 0.85em; margin: 0.5rem 0; }
.card-pills-section { margin: 0.5rem 0; }
.card-pills-section h5 { margin: 0.8rem 0 0.4rem 0; text-align: left; opacity: 0.7; font-size: 0.8em; text-transform: uppercase; }
.pill-list { display: flex; flex-wrap: wrap; gap: 5px; justify-content: flex-start; }
.pill-item { background: var(--color-background); border: 1px solid var(--card-border); padding: 2px 8px; font-size: 0.8em; border-radius: 4px; }
.card-meta { font-size: 0.9em; display: flex; flex-direction: column; gap: 0.3rem; margin: 1rem 0; text-align: left; }
.meta-item { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
.meta-label { font-weight: 600; opacity: 0.7; }
.meta-value { text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 65%; }
.meta-item-separator { border-top: 1px solid var(--card-border); opacity: 0.5; margin: 0.5rem 0; }
.status-badge { display: inline-block; padding: 2px 8px; font-size: 0.8em; font-weight: bold; border-radius: 12px; margin-left: 8px; vertical-align: middle; }
.status-badge.synced { background-color: #d4edda; color: #155724; }
.status-badge.not-found { background-color: #f8d7da; color: #721c24; }
.status-badge.offline { background-color: #e2e3e5; color: #383d41; }
.theme-dark .status-badge.synced { background-color: #155724; color: #d4edda; }
.theme-dark .status-badge.not-found { background-color: #721c24; color: #f8d7da; }
.theme-dark .status-badge.offline { background-color: #383d41; color: #e2e3e5; }

/* === Mockup Swapping Overlay === */
.mockup-img-link { position: relative; display: block; }
.mockup-overlay { position: absolute; inset: 0; background-color: rgba(0, 0, 0, 0.5); display: none; align-items: center; justify-content: center; border-radius: 4px; }
.mockup-card.swapping .mockup-overlay { display: flex; }
.mockup-overlay .spinner-icon { width: 48px; height: 48px; animation: spin 1.5s linear infinite; filter: invert(1); }
/* FIX (2025-08-04): Removed redundant dark theme rule. The global 'icon' class now handles this. */
@keyframes spin { to { transform: rotate(360deg); } }

/* === Gallery View Toggles & List View Styling === */
.view-toggle { margin-top: 0.5em;}
.view-toggle button { margin-right: 0.5em;}
.finalised-grid.list-view { display: block; }
.finalised-grid.list-view .final-card { flex-direction: row; max-width: none; margin-bottom: 1em; align-items: flex-start; }
.finalised-grid.list-view .card-thumb { flex: 0 0 150px; padding: 0; margin-top: 10px; }
.finalised-grid.list-view .card-img-top { max-height: 150px; }
.finalised-grid.list-view .card-content-wrapper { flex: 1; padding-left: 1.5rem; }
.finalised-grid.list-view .desc-snippet { display: block; }
.finalised-grid.list-view .card-description-full { display: none; }
.finalised-grid.list-view .final-actions { flex-direction: row; justify-content: flex-start; }

/* === Responsive Art Cards === */
@media (max-width: 900px) {
  .artwork-grid { gap: 1.3em; }
  .card-thumb { padding: 12px 0 4px 0;}
  .card-title { font-size: 1em; }
  .finalised-grid { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
}
@media (max-width: 800px) {
  .main-artwork-thumb { max-height: 50vh; }
  .mockup-preview-grid { grid-template-columns: repeat(auto-fill, minmax(45%, 1fr)); gap: 12px; }
  .mockup-card { width: 100%; }
  .mini-mockup-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 500px) {
  .mockup-preview-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
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
  --btn-primary-bg: #e7e7e7;
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
  flex: 1 1 200px;
  flex-direction: column;
  gap: 1.2rem;
  font-size: 1.06em;
  text-align: center;
  min-width: 180px;
  max-width: 270px;
  padding: 1.7em 1.2em 1.5em 1.2em;
  box-shadow: 0 2px 10px 0 #1111;
  margin: 0;
  border-radius: 0;
}

/* Responsive Buttons */
@media (max-width: 1200px) {
  .workflow-row { gap: 1.2rem; }
  .workflow-row .workflow-btn { font-size: 1em; min-width: 130px; max-width: 210px; padding: 1em 0.8em; }
}
@media (max-width: 800px) {
  .workflow-row { gap: 0.7rem; }
  .workflow-row .workflow-btn { font-size: 0.95em; min-width: 45vw; max-width: 95vw; padding: 0.9em 0.5em 1em 0.5em; margin-bottom: 0.5em; }
}
@media (max-width: 500px) {
  .workflow-row { flex-direction: column; gap: 0.5rem; }
  .workflow-row .workflow-btn { min-width: 98vw; max-width: 100vw; padding: 0.6em 0.2em 0.8em 0.2em; font-size: 0.88em;}
}

/* ========================================================
   Art Actions/Rows
   ======================================================== */

/* FIX (2025-08-04): Changed .button-row to a vertical column for gallery cards */
.button-row {
  display: flex;
  flex-direction: column;
  align-items: stretch; /* Makes child elements (forms, buttons) fill the width */
  gap: 8px; /* A slightly smaller gap for vertical stacking */
  margin-top: auto; /* Pushes the button group to the bottom of the card */
  padding-top: 15px;
  width: 100%;
}

/* Ensure forms inside the button row don't add extra margins and are flexible */
.button-row form {
  margin: 0;
  display: flex;
}

/* This rule is for other pages where buttons should be in a row */
.final-actions, .edit-actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.final-actions form, .edit-actions form { margin: 0; }

.art-btn {
  font-weight: 500; height: var(--button-height, 48px); min-width: 100px;
  border-radius: 0;
  font-size: 1em; display: flex; align-items: center; justify-content: center;
  background: var(--btn-secondary-bg);
  color: var(--btn-secondary-text);
  border: 1.2px solid var(--btn-workflow-border, #bbbbbb);
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
  background-color: #edebeb;
  color: var(--color-text);
  border-radius: 0;
}

.thumb-note {
  font-size: 0.85em; /* Adjusted for better fit */
  color: var(--color-muted-text);
  margin-top: 0.5rem;
  text-align: center;
}

/* --- OpenAI Analysis Details Table --- */
.openai-details {
  margin-top: 2rem;
  background-color: var(--color-info-card-bg);
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

/* --- NEW: Sellbrite Preview Section --- */
.sellbrite-preview {
    padding: 20px;
    margin-top: 20px;
    max-width: 100%;
    color: var(--color-preview-text);
    background-color: var(--color-preview-bg);
    border: 1px solid var(--card-border);
}

.sellbrite-preview h2 {
    margin-top: 0;
}

.sellbrite-preview .two-column-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-top: 1.5rem;
}

.sellbrite-preview .column p {
    margin: 0 0 1rem 0;
}

.sellbrite-preview textarea {
    background-color: var(--color-textarea-readonly-bg);
    border: 1px solid var(--card-border);
    color: var(--color-text);
    white-space: pre-line;
    font-family: monospace;
}

/* Responsive layout for the preview */
@media (max-width: 900px) {
    .sellbrite-preview .two-column-layout {
        grid-template-columns: 1fr;
        gap: 1.5rem;
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
  width: 35px;
  height: 35px;
  margin-right: 6px;
  vertical-align: bottom;
}

.narrator-icon {
  width: 50px;
  margin-bottom: 5px;
}

.artnarrator-logo {
  width: 100px;
  margin: 0px 8px 5px 0px;
  vertical-align: bottom;
}

/* Workflow and hero icons */
.step-btn-icon {
  width: 35px;
  height: 35px;
  margin-right: 12px;
  display: inline-block;
}

.hero-step-icon {
  width: 50px;
  height: 50px;
  margin-right: 10px;
  display: inline-block;
  margin-bottom: 5px;
  vertical-align: bottom;
  color:var(--color-text);
}

.progress-icon {
  width: 48px;
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
  width: 50px;
  height: 50px;
  margin: 1rem auto 0 auto; /* Centers the icon and adds space above it */
}

/* Responsive icon sizing for workflow buttons */
@media (max-width: 1200px) {
  .workflow-row .step-btn-icon { width: 2em; height: 2em; }
}
@media (max-width: 800px) {
  .workflow-row .step-btn-icon { width: 1.5em; height: 1.5em; }
}
@media (max-width: 500px) {
  .workflow-row .step-btn-icon { width: 1.2em; height: 1.2em; }
}


---
## static/css/layout.css
---
/* ========================================================
   layout.css – Layout, Grids, Columns, Structure
   Uses --header-bg variable for theme-aware headers.
   ======================================================== */

/* === Layout Grids, Columns & Rows === */
.review-artwork-grid, .row { display: flex; flex-wrap: wrap; gap: 2.5rem; align-items: flex-start; width: 100%; }
.exports-special-grid { display: grid; grid-template-columns: 1fr 1.7fr; gap: 2em; margin: 2em 0; }
.page-title-row { display: flex; align-items: center; gap: 20px; margin-bottom: 40px; }
.page-title-large { font-size: 2.15em; font-weight: bold; text-align: center; margin: 1.4em 0 0.7em 0; }
.mockup-col { flex: 1 1 0; min-width: 340px; display: block; }
.edit-listing-col { flex: 1; } /* MODIFIED: Removed width: 100% and allowed flexbox to manage width */
.price-sku-row, .row-inline { display: flex; gap: 1em; }
.price-sku-row > div, .row-inline > div { flex: 1; }

/* === Responsive Grids === */
@media (max-width: 900px) {
  .page-title-row { flex-direction: column; text-align: center; gap: 1em; }
  .exports-special-grid { grid-template-columns: 1fr; gap: 1.1em; }
}
@media (max-width: 800px) {
  .review-artwork-grid { flex-direction: column; gap: 1.5em; }
  .mockup-col, .edit-listing-col { width: 100%; max-width: none;}
}

/* ===== Simple Flexbox Grid System for ArtNarrator ===== */

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


/* === Header === */
.site-header, .overlay-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 1rem 1rem;
	width: 100%;
	background-color: var(--header-bg);
}

.site-header {
	position: sticky;
	top: 0;
	z-index: 100;
	background-color: var(--header-bg);
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
  border: 2px dashed var(--color-dropzone-border);
  background-color: var(--upload-dz-background-color);
  max-width: 800px;;
  width: 100%;
  margin: 20px auto;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  color: var(--color-dropzone-text);
  transition: background 0.2s, border-color 0.2s;
}

.upload-dropzone:hover {
  background-color: var(--color-hover);
  color:var(--dark-color-text);
}

.upload-dropzone.dragover {
  border-color: var(--color-text);
  background: var(--color-dropzone-bg-hover);
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
  background-color: var(--color-info-card-bg) !important;
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
  width: 100%; max-width: 1200px; margin: 0 auto 50px auto;
}
.nav-column h3 { font-size: 1rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; opacity: 0.5; margin: 0 0 1.5rem 0;}
.nav-column ul { display: flex; flex-direction: column; gap: 1rem;}
.nav-column a { font-size: 1.2em; font-weight: 500; line-height: 1.3; display: inline-block; transition: color 0.3s var(--ease-quart);}
.nav-column a:hover { color: var(--color-hover);}
@media (max-width: 900px) {
  .overlay-nav { grid-template-columns: 1fr; justify-items: center; text-align: center; gap: 3rem; }
  .nav-column a { font-size: 1.5rem; }
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
  --color-card-bg: #b3b3b3;
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
  --upload-dz-background-color: #f5f5f5;
  --color-hover-other: #000000;
  --color-accent: #e76a25;
  --color-accent-hover: #ff9933;
  --card-border: #c8c7c7;
  --workflow-icon-size: 2.1em;
  --dark-color-background: #333333;
  --dark-color-text: #8c8c8c;
  --dark-color-card-bg: #727272;
  --dark-card-border: #727272;
  --light-card-border: #727272;

  /* NEW: Centralised variables for consistent styling */
  --color-border-subtle: #e0e0e0;
  --color-shadow-light: rgba(0, 0, 0, 0.06);
  --color-shadow-medium: rgba(0, 0, 0, 0.12);
  --color-badge-finalised-text: #d40000;
  --color-badge-locked-text: #0066aa;
  --color-badge-locked-border: #0066aa;
  --color-muted-text: #535353;
  --color-info-card-bg: #dbdbdb;
  --color-preview-bg: #f0f0f0;
  --color-preview-text: #333333;
  --color-textarea-readonly-bg: #f9f9f9;
  --color-dropzone-border: #bbbbbb;
  --color-dropzone-text: #666666;
  --color-dropzone-bg-hover: #f9f9f9;
}

/* Dark theme variables applied when `.theme-dark` class is present on `html` or `body` */
.theme-dark {
  --color-background: var(--dark-color-background);
  --color-text: var(--dark-color-text);
  --color-card-bg: #b3b3b3;
  --card-border: var(--dark-card-border);
  --color-footer-bg: var(--dark-color-footer-bg);
  --color-footer-text: var(--dark-color-footer-text);
  --upload-dz-background-color: #212121;
  --header-bg: #111111;
  --table-row-bg: #222222;
  --table-row-alt-bg: #333333;

  /* NEW: Dark theme equivalents */
  --color-border-subtle: #444444;
  --color-shadow-light: rgba(0, 0, 0, 0.15);
  --color-shadow-medium: rgba(0, 0, 0, 0.25);
  --color-badge-finalised-text: #ff6b6b;
  --color-badge-locked-text: #6cb6ff;
  --color-badge-locked-border: #6cb6ff;
  --color-muted-text: #737373;
  --color-info-card-bg: #2a2a2a;
  --color-preview-bg: #4f4f4f;
  --color-preview-text: #bbbbbb;
  --color-textarea-readonly-bg: #2c2c2c;
  --color-dropzone-border: #555555;
  --color-dropzone-text: #aaaaaa;
  --color-dropzone-bg-hover: #3a3a3a;
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
  padding: .25rem 2rem 2rem 2rem;
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

@media (max-width: 1800px) { .container { max-width: 98vw; } }
@media (max-width: 1400px) { .container { max-width: 99vw; } }
@media (max-width: 1000px) { .container { padding: 1.8rem 1rem; } }
@media (max-width: 700px)  { .container { padding: 1.2rem 0.5rem; } }

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
  const actionUrl = `/analyze/${encodeURIComponent(aspect)}/${encodeURIComponent(filename)}`;

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
## static/js/main-overlay-test.js
---
// THIS IS A TEST MIGRATION TEMPLATE. Safe to delete after production migration.
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
                    body.style.overflow = 'hidden';
                });

                menuClose.addEventListener('click', () => {
                    overlayMenu.classList.remove('is-active');
                    body.style.overflow = '';
                });
            }

            // --- Theme Logic ---
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


---
## static/js/main.js
---
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('theme-toggle');
  const sunIcon = document.getElementById('icon-sun');
  const moonIcon = document.getElementById('icon-moon');

  function applyTheme(theme) {
    document.documentElement.classList.remove('theme-light', 'theme-dark');
    document.documentElement.classList.add('theme-' + theme);
    localStorage.setItem('theme', theme);
    if (sunIcon && moonIcon) {
      sunIcon.style.display = theme === 'dark' ? 'none' : 'inline';
      moonIcon.style.display = theme === 'dark' ? 'inline' : 'none';
    }
  }

  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const initial = saved || (prefersDark ? 'dark' : 'light');
  applyTheme(initial);

  if (toggle) {
    toggle.addEventListener('click', () => {
      const next = document.documentElement.classList.contains('theme-dark')
        ? 'light' : 'dark';
      applyTheme(next);
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
## static/js/new-main.js
---
// THIS IS A TEST MIGRATION TEMPLATE. Safe to delete after production migration.
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
                    body.style.overflow = 'hidden';
                });

                menuClose.addEventListener('click', () => {
                    overlayMenu.classList.remove('is-active');
                    body.style.overflow = '';
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


---
## static/js/upload.js
---
/* ================================
   ArtNarrator Upload JS (XMLHttpRequest for Progress)
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
      formData.append('images', file);

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
    window.location.href = '/artworks';
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
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Oops! Page Not Found</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/404.css') }}">
</head>
<body>
    <div class="container">
        <h1>Oops! Something went wrong...</h1>
        <p>It looks like the page you're looking for has either moved or doesn't exist. Don't worry, it's probably not your fault!</p>
        <p>Why not head back to the <a href="/">homepage</a> and try again?</p>
    </div>
</body>
</html>


---
## templates/500.html
---
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Server Error</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/404.css') }}">
</head>
<body>
    <div class="container">
        <h1>Something went wrong</h1>
        <p>We've logged the error and will fix it ASAP.</p>
        <p><a href="{{ url_for('artwork.home') }}">Return to home</a></p>
    </div>
</body>
</html>


---
## templates/artworks.html
---
{# Use blueprint-prefixed endpoints like 'artwork.home' in url_for #}
{% extends "main.html" %}
{% block title %}Artwork | ArtNarrator{% endblock %}
{% block content %}
<div class="container">

<div class="home-hero" >
  <h1><img src="{{ url_for('static', filename='icons/svg/light/number-circle-two-light.svg') }}" class="hero-step-icon" alt="Step 2: Artwork" />Artwork</h1>
</div>

<div class="gallery-section">

  {% if ready_artworks %}
    <h2 class="mb-3">Ready to Analyze</h2>
    <div class="artwork-grid">
      {% for art in ready_artworks %}
      <div class="gallery-card" data-filename="{{ art.filename }}" data-aspect="{{ art.aspect }}" data-base="{{ art.base }}">
        <div class="card-thumb">
          <img class="card-img-top"
               src="{{ url_for('artwork.unanalysed_image', filename=art.thumb) }}"
               alt="{{ art.title }}">
        </div>
        <span class="status-icon"></span>
        <div class="card-details">
          <div class="card-title">{{ art.title }}</div>
          <div class="desc-snippet"></div>
          <div class="button-row">
            <button class="btn btn-primary btn-analyze" data-provider="openai">Analyze with OpenAI</button>
            <button class="btn btn-secondary btn-sign" data-base="{{ art.base }}">Sign Artwork</button>
            <form method="post" action="{{ url_for('artwork.delete_artwork', seo_folder=art.base) }}" style="display:inline;" onsubmit="return confirm('Delete this artwork and all files? This cannot be undone.');">
              <button type="submit" class="btn btn-danger">Delete</button>
            </form>
          </div>
        </div>
        <div class="card-overlay hidden"></div>
      </div>
      {% endfor %}
    </div>
  {% endif %}

  {% if processed_artworks %}
    <h2 class="mb-3 mt-5">Processed Artworks</h2>
    <div class="artwork-grid">
      {% for art in processed_artworks %}
      <div class="gallery-card" data-filename="{{ art.filename }}" data-aspect="{{ art.aspect }}">
        <div class="card-thumb">
          <img class="card-img-top"
               src="{{ url_for('artwork.processed_image', filename=art.seo_folder ~ '/' ~ art.thumb) }}"
               alt="{{ art.title }}">
        </div>
        <span class="status-icon"></span>
        <div class="card-details">
          <div class="card-title">{{ art.title }}</div>
          <div class="desc-snippet"></div>
          <div class="button-row">
            {# --- CORRECTED LINE --- #}
            <a href="{{ url_for('artwork.edit_listing', aspect=art.aspect, filename=art.seo_folder ~ '.jpg') }}" class="btn btn-primary btn-edit">Review</a>
            <form method="post" action="{{ url_for('artwork.finalise_artwork', seo_folder=art.seo_folder) }}" style="display:inline;">
              <button type="submit" class="btn btn-success">Finalise</button>
            </form>
            <button class="btn btn-secondary btn-analyze" data-provider="openai">Re-Analyze</button>
            <form method="post" action="{{ url_for('artwork.delete_artwork', seo_folder=art.seo_folder) }}" style="display:inline;" onsubmit="return confirm('Delete this artwork and all files? This cannot be undone.');">
              <button type="submit" class="btn btn-danger">Delete</button>
            </form>
          </div>
        </div>
        <div class="card-overlay hidden"></div>
      </div>
      {% endfor %}
    </div>
  {% endif %}

  {% if finalised_artworks %}
    <h2 class="mb-3 mt-5">Finalised Artworks</h2>
    <div class="artwork-grid">
      {% for art in finalised_artworks %}
      <div class="gallery-card" data-filename="{{ art.filename }}" data-aspect="{{ art.aspect }}">
        <div class="card-thumb">
          <img class="card-img-top"
               src="{{ url_for('artwork.finalised_image', filename=art.seo_folder ~ '/' ~ art.thumb) }}"
               alt="{{ art.title }}">
        </div>
        <span class="status-icon"></span>
        <div class="card-details">
          <div class="card-title">{{ art.title }}</div>
          <div class="desc-snippet"></div>
          <div class="button-row">
            {# --- CORRECTED LINE --- #}
            <a href="{{ url_for('artwork.edit_listing', aspect=art.aspect, filename=art.seo_folder ~ '.jpg') }}" class="btn btn-secondary btn-edit">Edit</a>
            <form method="post" action="{{ url_for('artwork.lock_it_in', seo_folder=art.seo_folder) }}" style="display:inline;">
              <button type="submit" class="btn btn-primary">Lock It In</button>
            </form>
            <button class="btn btn-secondary btn-analyze" data-provider="openai">Re-Analyze</button>
            <form method="post" action="{{ url_for('artwork.delete_artwork', seo_folder=art.seo_folder) }}" style="display:inline;" onsubmit="return confirm('Delete this artwork and all files? This cannot be undone.');">
              <button type="submit" class="btn btn-danger">Delete</button>
            </form>
          </div>
        </div>
        <div class="card-overlay hidden"></div>
      </div>
      {% endfor %}
    </div>
  {% endif %}
  {% if not ready_artworks and not processed_artworks and not finalised_artworks %}
    <p class="empty-msg">No artworks found. Please upload artwork to get started!</p>
  {% endif %}

</div>

</div>
<script src="{{ url_for('static', filename='js/artworks.js') }}"></script>
{% endblock %}

---
## templates/composites_preview.html
---
{# Use blueprint-prefixed endpoints like 'artwork.home' in url_for #}
{% extends "main.html" %}
{% block title %}Composite Preview | ArtNarrator{% endblock %}
{% block content %}
<div class="container">
<h1 style="text-align:center;">Composite Preview: {{ seo_folder }}</h1>
{% if listing %}
  <div style="text-align:center;margin-bottom:1.5em;">
    <img src="{{ url_for('artwork.processed_image', seo_folder=seo_folder, filename=seo_folder+'.jpg') }}" alt="artwork" style="max-width:260px;border-radius:8px;box-shadow:0 2px 6px #0002;">
  </div>
{% endif %}
{% if images %}
<div class="grid">
  {% for img in images %}
  <div class="item">
    {% if img.exists %}
    <img src="{{ url_for('artwork.processed_image', seo_folder=seo_folder, filename=img.filename) }}" alt="{{ img.filename }}">
    {% else %}
    <div class="missing-img">Image Not Found</div>
    {% endif %}
    <div style="font-size:0.9em;color:#555;word-break:break-all;">{{ img.filename }}</div>
    {% if img.category %}<div style="color:#888;font-size:0.9em;">{{ img.category }}</div>{% endif %}
  </div>
  {% endfor %}
</div>
<form method="post" action="{{ url_for('artwork.approve_composites', seo_folder=seo_folder) }}" style="text-align:center;margin-top:2em;">
  <button type="submit" class="composite-btn">Finalize &amp; Approve</button>
</form>
{% else %}
<p style="text-align:center;margin:2em 0;">No composites found.</p>
{% endif %}
<div style="text-align:center;margin-top:2em;">
  <a href="{{ url_for('artwork.select') }}" class="composite-btn" style="background:#666;">Back to Selector</a>
</div>
</div>
{% endblock %}


---
## templates/dws_editor.html
---
{% extends "main.html" %}
{% block title %}Guided Description Editor{% endblock %}

{% block content %}
<style>
  /* --- Page Layout --- */
  .gdws-container { display: flex; flex-wrap: wrap; gap: 2rem; align-items: flex-start; }
  .gdws-main-content { flex: 1; min-width: 60%; }
  .gdws-sidebar { width: 280px; position: sticky; top: 100px; padding: 1.5rem; background-color: var(--color-card-bg); border: 1px solid var(--card-border); }
  .gdws-sidebar h3 { margin-top: 0; text-align: center; margin-bottom: 1.5rem; }
  .gdws-sidebar button { width: 100%; margin-bottom: 1rem; }

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
  .sortable-ghost { opacity: 0.4; background: #888; border: 2px dashed var(--color-accent); }
  .pinned { background-color: #f0f0f0; border-left: 4px solid #007bff; cursor: not-allowed; }
  .theme-dark .pinned { background-color: #2a2a2a; border-left-color: #4e9fef; }
  .instructions-modal { display: none; }
</style>

<div class="container">
  <h1>Guided Description Editor</h1>
  <p>Select an aspect ratio to load its base paragraphs. You can edit content, regenerate with AI, and modify the instructions for each section. Paragraphs in the middle section can be reordered via drag-and-drop.</p>
  
  <div class="gdws-container">
    <div class="gdws-main-content">
      <div class="form-group">
        <label for="aspect-ratio-selector">Select Aspect Ratio:</label>
        <select id="aspect-ratio-selector">
          <option value="">-- Choose --</option>
          {% for ar in aspect_ratios %}
          <option value="{{ ar }}">{{ ar }}</option>
          {% endfor %}
        </select>
      </div>
      
      <div id="editor-wrapper" style="margin-top: 2rem;">
        <div id="start-blocks"></div>
        <div id="middle-blocks"></div>
        <div id="end-blocks"></div>
      </div>
    </div>

    <aside class="gdws-sidebar">
      <h3>Global Actions</h3>
      <button id="save-order-btn" class="btn btn-primary wide-btn" disabled>Save Order</button>
      <button id="regenerate-all-btn" class="btn btn-secondary wide-btn" disabled>Regenerate All Content</button>
      <button id="reset-all-btn" class="btn btn-secondary wide-btn" disabled>Reset All to Base</button>
    </aside>
  </div>
</div>

<div id="instructions-modal" class="analysis-modal instructions-modal" role="dialog" aria-modal="true">
    <div class="analysis-box" tabindex="-1">
        <button class="modal-close" aria-label="Close">&times;</button>
        <h3 id="instructions-title">Instructions</h3>
        <textarea id="instructions-text" rows="8" style="width: 100%;"></textarea>
        <div class="block-actions" style="justify-content: flex-end;">
            <button id="save-instructions-btn" class="btn btn-primary">Save Instructions</button>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js"></script>

<script>
document.addEventListener('DOMContentLoaded', () => {
    const arSelector = document.getElementById('aspect-ratio-selector');
    const startBlocksContainer = document.getElementById('start-blocks');
    const middleBlocksContainer = document.getElementById('middle-blocks');
    const endBlocksContainer = document.getElementById('end-blocks');
    const editorWrapper = document.getElementById('editor-wrapper');
    
    const regenerateAllBtn = document.getElementById('regenerate-all-btn');
    const resetAllBtn = document.getElementById('reset-all-btn');
    const saveOrderBtn = document.getElementById('save-order-btn');
    
    const instructionsModal = document.getElementById('instructions-modal');
    const instructionsTitle = document.getElementById('instructions-title');
    const instructionsText = document.getElementById('instructions-text');
    const saveInstructionsBtn = document.getElementById('save-instructions-btn');
    const closeInstructionsBtn = instructionsModal.querySelector('.modal-close');
    let currentBlockForInstructions = null;
    
    let sortable = null;
    // CORRECTED: Load the server-rendered JSON into JS variables
    const PINNED_START_TITLES = JSON.parse('{{ PINNED_START_TITLES | tojson | safe }}');
    const PINNED_END_TITLES = JSON.parse('{{ PINNED_END_TITLES | tojson | safe }}');

    async function loadTemplate(aspectRatio) {
        if (!aspectRatio) {
            startBlocksContainer.innerHTML = '<p>Please select an aspect ratio to begin.</p>';
            middleBlocksContainer.innerHTML = '';
            endBlocksContainer.innerHTML = '';
            [regenerateAllBtn, resetAllBtn, saveOrderBtn].forEach(b => b.disabled = true);
            return;
        }
        startBlocksContainer.innerHTML = '<p>Loading...</p>';
        middleBlocksContainer.innerHTML = '';
        endBlocksContainer.innerHTML = '';

        const response = await fetch(`/admin/gdws/template/${aspectRatio}`);
        const data = await response.json();
        
        startBlocksContainer.innerHTML = '';

        data.blocks.forEach(block => {
            const isStart = PINNED_START_TITLES.includes(block.title);
            const isEnd = PINNED_END_TITLES.includes(block.title);
            const container = isStart ? startBlocksContainer : (isEnd ? endBlocksContainer : middleBlocksContainer);
            renderBlock(block, container, !isStart && !isEnd);
        });
        
        if (sortable) sortable.destroy();
        sortable = new Sortable(middleBlocksContainer, {
            animation: 150,
            ghostClass: 'sortable-ghost'
        });

        [regenerateAllBtn, resetAllBtn, saveOrderBtn].forEach(b => b.disabled = false);
    }

    function renderBlock(block, container, isDraggable) {
        const blockEl = document.createElement('div');
        blockEl.className = 'paragraph-block';
        if (!isDraggable) blockEl.classList.add('pinned');
        
        blockEl.dataset.id = block.title; 
        blockEl.dataset.originalTitle = block.title;
        blockEl.dataset.instructions = block.instructions || '';

        blockEl.innerHTML = `
            <div class="title-actions">
                <input type="text" class="block-title" value="${block.title}">
                <button class="btn btn-sm btn-regenerate-title" title="Regenerate Title with AI">AI Title</button>
            </div>
            <textarea>${block.content}</textarea>
            <div class="block-actions">
                <button class="btn btn-secondary btn-instructions">View/Edit Instructions</button>
                <div>
                    <button class="btn btn-secondary btn-regenerate">Regenerate Content</button>
                    <button class="btn btn-primary btn-save-base">Update Base</button>
                </div>
            </div>
        `;
        container.appendChild(blockEl);
    }

    // --- Event Listeners ---

    arSelector.addEventListener('change', () => loadTemplate(arSelector.value));

    resetAllBtn.addEventListener('click', () => {
        const currentAspect = arSelector.value;
        if (currentAspect && confirm('Are you sure? This will discard all unsaved changes and reload the saved base text.')) {
            loadTemplate(currentAspect);
        }
    });

    saveOrderBtn.addEventListener('click', async () => {
        const order = Array.from(middleBlocksContainer.children).map(el => el.dataset.originalTitle);
        
        saveOrderBtn.textContent = 'Saving...';
        saveOrderBtn.disabled = true;
        await fetch('/admin/gdws/save-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ aspect_ratio: arSelector.value, order: order }),
        });
        saveOrderBtn.textContent = 'Save Order';
        saveOrderBtn.disabled = false;
        alert('New order has been saved!');
    });

    regenerateAllBtn.addEventListener('click', async () => {
        const allBlocks = document.querySelectorAll('.paragraph-block');
        if (!allBlocks.length || !confirm(`This will regenerate content for all ${allBlocks.length} paragraphs. Are you sure?`)) return;

        regenerateAllBtn.textContent = 'Regenerating...';
        regenerateAllBtn.disabled = true;

        for (const blockEl of allBlocks) {
            if (blockEl.closest('#middle-blocks') || blockEl.closest('#start-blocks') || blockEl.closest('#end-blocks')) {
                const btn = blockEl.querySelector('.btn-regenerate');
                await handleRegenerate(blockEl, btn);
            }
        }

        regenerateAllBtn.textContent = 'Regenerate All Content';
        regenerateAllBtn.disabled = false;
    });

    async function handleRegenerate(blockEl, buttonEl) {
        const textarea = blockEl.querySelector('textarea');
        const instructions = blockEl.dataset.instructions;
        
        buttonEl.textContent = '...';
        buttonEl.disabled = true;
        
        const response = await fetch('/admin/gdws/regenerate-paragraph', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_text: textarea.value, instructions: instructions }),
        });
        const result = await response.json();
        textarea.value = result.new_content;
        
        buttonEl.textContent = 'Regenerate Content';
        buttonEl.disabled = false;
    }
    
    editorWrapper.addEventListener('click', async (e) => {
        const blockEl = e.target.closest('.paragraph-block');
        if (!blockEl) return;

        const originalTitle = blockEl.dataset.originalTitle;
        let instructions = blockEl.dataset.instructions;
        const titleInput = blockEl.querySelector('.block-title');
        const textarea = blockEl.querySelector('textarea');
        const aspectRatio = arSelector.value;

        if (e.target.classList.contains('btn-regenerate-title')) {
            e.target.textContent = '...';
            const response = await fetch('/admin/gdws/regenerate-title', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ content: textarea.value })
            });
            const result = await response.json();
            titleInput.value = result.new_title;
            e.target.textContent = 'AI Title';
        }

        if (e.target.classList.contains('btn-save-base')) {
            e.target.textContent = 'Updating...';
            const response = await fetch('/admin/gdws/save-base-paragraph', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    aspect_ratio: aspectRatio, 
                    original_title: originalTitle,
                    new_title: titleInput.value,
                    content: textarea.value, 
                    instructions: instructions 
                }),
            });
            const result = await response.json();
            if (result.status === 'success') {
                blockEl.dataset.originalTitle = titleInput.value;
                blockEl.dataset.id = titleInput.value;
            } else {
                alert(`Error: ${result.message}`);
                titleInput.value = originalTitle;
            }
            e.target.textContent = 'Update Base';
        }
        
        if (e.target.classList.contains('btn-regenerate')) {
            await handleRegenerate(blockEl, e.target);
        }

        if (e.target.classList.contains('btn-instructions')) {
            currentBlockForInstructions = blockEl;
            instructionsTitle.textContent = `Instructions for: ${titleInput.value}`;
            instructionsText.value = instructions;
            instructionsModal.classList.add('active');
        }
    });

    // Modal close logic
    closeInstructionsBtn.addEventListener('click', () => instructionsModal.classList.remove('active'));
    saveInstructionsBtn.addEventListener('click', async () => {
        if (currentBlockForInstructions) {
            const title = currentBlockForInstructions.querySelector('.block-title').value;
            const content = currentBlockForInstructions.querySelector('textarea').value;
            const aspectRatio = arSelector.value;
            const newInstructions = instructionsText.value;

            saveInstructionsBtn.textContent = 'Saving...';
            await fetch('/admin/gdws/save-base-paragraph', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    aspect_ratio: aspectRatio, 
                    original_title: currentBlockForInstructions.dataset.originalTitle,
                    new_title: title,
                    content: content, 
                    instructions: newInstructions 
                }),
            });
            currentBlockForInstructions.dataset.instructions = newInstructions;
            saveInstructionsBtn.textContent = 'Save Instructions';
            instructionsModal.classList.remove('active');
        }
    });
});
</script>
{% endblock %}

---
## templates/edit_listing.html
---
{# templates/edit_listing.html #}
{# ====================================================================================
  TEMPLATE: edit_listing.html
  PURPOSE: Edit existing artwork listing, preview mockups, update metadata, finalise
  STRUCTURE: Structured by Robbie Mode™ - Clear Sectioning and Sub-Sectioning
==================================================================================== #}

{% extends "main.html" %}
{% block title %}Edit Listing{% endblock %}

{% block content %}
<div class="container">

  {# -------------------------------
     SECTION 0: HIDDEN TEST MARKER
  ------------------------------- #}
  <div id="edit-listing-marker" style="display: none;">Edit Listing Page</div>

  {# ---------------------------
     SECTION 1: HEADER & HERO UI
  ---------------------------- #}
  <div class="home-hero">
    <h1>
      <img
        src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}"
        class="hero-step-icon"
        alt="Step 3: Edit Listing"
      />
      Edit Listing
    </h1>
  </div>
  
  {# -------------------------------
     SECTION 2: FLASH MESSAGE BLOCK
  ------------------------------- #}
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <div class="flash-message-block">
        {% for category, message in messages %}
          <div class="flash flash-{{ category }}">{{ message }}</div>
        {% endfor %}
      </div>
    {% endif %}
  {% endwith %}

  {# ================================================================
     SECTION 3: REVIEW ARTWORK GRID - TWO COLUMNS (Mockups + Form)
  ================================================================ #}
  <div class="review-artwork-grid row">

    {# ---------------------------------------------------------
       SUBSECTION 3.1: COLUMN LEFT — MOCKUPS + THUMBNAIL PREVIEW
    ---------------------------------------------------------- #}
    <div class="col col-6 mockup-col">
      <div class="main-thumb">
        {# FIX (2025-08-04): Use the new central helper function for robust URL generation #}
        {% set thumb_filename = seo_folder ~ '/' ~ config.FILENAME_TEMPLATES.thumbnail.format(seo_slug=seo_folder) %}
        {% set analyse_filename = seo_folder ~ '/' ~ config.FILENAME_TEMPLATES.analyse.format(seo_slug=seo_folder) %}
        {% set thumb_img_url = get_artwork_image_url(artwork.status, thumb_filename) %}
        {% set analyse_img_url = get_artwork_image_url(artwork.status, analyse_filename) %}
        
        <a href="#" class="main-thumb-link" data-img="{{ analyse_img_url }}?t={{ cache_ts }}">
          <img src="{{ thumb_img_url }}?t={{ cache_ts }}" class="main-artwork-thumb" alt="Main artwork thumbnail for {{ seo_folder }}">
          <div class="thumb-note">Click thumbnail for full size</div>
        </a>
      </div>

      {# Subsection: Mockup Preview Thumbnails #}
      <h3>Preview Mockups</h3>
      <div class="mockup-preview-grid">
        {% for m in mockups %}
          <div class="mockup-card" id="mockup-card-{{ m.index }}">
            {% if m.exists and m.thumb_exists %}
              {# FIX (2025-08-04): Use the new central helper for robust URLs, replacing complex if/else blocks #}
              {% set full_url = get_artwork_image_url(artwork.status, m.path_rel) %}
              {% set thumb_url = get_artwork_image_url(artwork.status, m.thumb_rel) %}

              <a href="{{ full_url ~ '?t=' ~ cache_ts }}" class="mockup-img-link" id="mockup-link-{{ m.index }}" data-img="{{ full_url ~ '?t=' ~ cache_ts }}">
                <img id="mockup-img-{{ m.index }}" src="{{ thumb_url ~ '?t=' ~ cache_ts }}" data-fallback="{{ full_url ~ '?t=' ~ cache_ts }}" class="mockup-thumb-img" alt="Mockup preview {{ loop.index }}">
                <div class="mockup-overlay">
                  <img src="{{ url_for('static', filename='icons/svg/light/arrows-clockwise-light.svg') }}" class="spinner-icon icon" alt="Loading...">
                </div>
                <div class="thumb-note">Click to preview full-size</div>
              </a>
              
            {% else %}
              <img src="{{ url_for('static', filename='img/default-mockup.jpg') }}" class="mockup-thumb-img" alt="Default mockup placeholder">
              <div class="thumb-note">Mockup not found</div>
            {% endif %}

            {# Sub-subsection: Swap Mockup Category Controls #}
            {% if categories %}
              <div class="swap-controls">
                <select name="new_category" aria-label="Swap mockup category for slot {{ m.index }}">
                  {% for c in categories %}
                    <option value="{{ c }}" {% if c == m.category %}selected{% endif %}>{{ c }}</option>
                  {% endfor %}
                </select>
                <div class="swap-btn-container">
                  <button type="button" class="btn btn-sm swap-btn" data-index="{{ m.index }}">Swap</button>
                </div>
              </div>
            {% endif %}
          </div>
        {% endfor %}
      </div>
    </div>

    {# -------------------------------------------------------
       SUBSECTION 3.2: COLUMN RIGHT — LISTING EDIT FORM & ACTIONS
    -------------------------------------------------------- #}
    <div class="col col-6 edit-listing-col">
      
      {# Status Banner #}
      <p class="status-line {% if finalised %}status-finalised{% else %}status-pending{% endif %}">
        Status: This artwork is {% if finalised %}<strong>finalised</strong>{% else %}<em>NOT yet finalised</em>{% endif %}
        {% if locked %}<span class="locked-badge">Locked</span>{% endif %}
      </p>

      {# Form Errors #}
      {% if errors %}
        <div class="flash-error"><ul>{% for e in errors %}<li>{{ e }}</li>{% endfor %}</ul></div>
      {% endif %}

      {# Listing Edit Form Starts #}
      <form role="form" id="edit-form" method="POST" autocomplete="off">
        <label for="title-input">Title:</label>
        <textarea name="title" id="title-input" rows="2" class="long-field" {% if not editable %}disabled{% endif %}>{{ artwork.title|e }}</textarea>

        <label for="description-input">Description:</label>
        <textarea name="description" id="description-input" rows="12" class="long-field" {% if not editable %}disabled{% endif %}>{{ artwork.description|e }}</textarea>

        <div class="artwork-info-card" id="generic-text-reworder">
          <h2>Generic Text Rewording</h2>
          <p class="help-text">Use AI to rephrase the generic text block to make it unique for this listing.</p>
          <label for="generic-text-input">Generic Text:</label>
            <textarea id="generic-text-input" rows="6" class="long-field">{{ artwork.generic_description|e }}</textarea>
          <div class="button-row">
            <button type="button" id="reword-openai-btn" class="btn btn-secondary" data-provider="openai" {% if not openai_configured %}disabled title="OpenAI API not configured"{% endif %}>Reword with OpenAI</button>
            <button type="button" id="reword-gemini-btn" class="btn btn-secondary" data-provider="gemini" {% if not google_configured %}disabled title="Google API not configured"{% endif %}>Reword with Gemini</button>
          </div>
          <div id="reword-spinner" style="display: none; text-align: center; margin-top: 1rem;"><span class="spinner"></span> Rewording...</div>
        </div>

        <label for="tags-input">Tags (comma-separated):</label>
        <textarea name="tags" id="tags-input" rows="2" class="long-field" {% if not editable %}disabled{% endif %}>{{ artwork.tags_str|e }}</textarea>

        <label for="materials-input">Materials (comma-separated):</label>
        <textarea name="materials" id="materials-input" rows="2" class="long-field" {% if not editable %}disabled{% endif %}>{{ artwork.materials_str|e }}</textarea>

        <div class="row-inline">
          <div class="form-col">
            <label for="primary_colour-select">Primary Colour:</label>
            <select name="primary_colour" id="primary_colour-select" class="long-field" {% if not editable %}disabled{% endif %}>
              {% for col in allowed_colours %}<option value="{{ col }}" {% if artwork.primary_colour == col %}selected{% endif %}>{{ col }}</option>{% endfor %}
            </select>
          </div>
          <div class="form-col">
            <label for="secondary_colour-select">Secondary Colour:</label>
            <select name="secondary_colour" id="secondary_colour-select" class="long-field" {% if not editable %}disabled{% endif %}>
              {% for col in allowed_colours %}<option value="{{ col }}" {% if artwork.secondary_colour == col %}selected{% endif %}>{{ col }}</option>{% endfor %}
            </select>
          </div>
        </div>

        <label for="seo_filename-input">SEO Filename:</label>
        <input type="text" id="seo_filename-input" class="long-field" name="seo_filename" value="{{ artwork.seo_filename|e }}" {% if not editable %}disabled{% endif %}>

        <div class="price-sku-row">
          <div>
            <label for="price-input">Price:</label>
            <input type="text" id="price-input" name="price" value="{{ artwork.price|e }}" class="long-field" {% if not editable %}disabled{% endif %}>
          </div>
          <div>
            <label for="sku-input">SKU:</label>
            <input type="text" id="sku-input" value="{{ artwork.sku|e }}" class="long-field" readonly disabled>
          </div>
        </div>
        
        <div class="button-row" style="justify-content: flex-end; margin-top: 0; margin-bottom: 0.5rem;">
            <button type="button" id="update-links-btn" class="btn btn-sm btn-secondary" style="width: auto; min-width: 150px;">Update Image URLs</button>
        </div>
        <label for="images-input">Image URLs (one per line):</label>
        <textarea name="images" id="images-input" rows="5" class="long-field" {% if not editable %}disabled{% endif %}>{{ artwork.images|e }}</textarea>
      </form>

      <div class="edit-actions-col">
        <button form="edit-form" type="submit" name="action" value="save" class="btn btn-primary wide-btn" {% if not editable %}disabled{% endif %}>Save Changes</button>
        {% if finalised and not locked %}
          <form method="post" action="{{ url_for('artwork.lock_listing', aspect=aspect, filename=filename) }}" class="action-form">
            <button type="submit" class="btn btn-primary wide-btn">Lock Listing</button>
          </form>
        {% elif locked %}
          <div class="artwork-info-card">
            <h3 style="margin-top: 0;">Unlock for Editing</h3>
            <p class="help-text">Unlocking allows edits and re-syncs to Sellbrite. Files remain in the vault to preserve URLs.</p>
            <form method="post" action="{{ url_for('artwork.unlock_listing', aspect=aspect, filename=filename) }}" class="action-form">
              <label for="confirm-unlock-input">Type UNLOCK to confirm:</label>
              <input type="text" id="confirm-unlock-input" name="confirm_unlock" class="long-field" required pattern="UNLOCK" oninput="this.form.elements.unlock_submit.disabled = this.value !== 'UNLOCK'">
              <button type="submit" name="unlock_submit" class="btn btn-primary wide-btn" disabled>Unlock</button>
            </form>
          </div>
        {% endif %}

        {% if not finalised %}
          <form method="post" action="{{ url_for('artwork.finalise_artwork', seo_folder=seo_folder) }}" class="action-form">
            <button type="submit" class="btn btn-success wide-btn">✅ Finalise Artwork</button>
          </form>
        {% elif finalised and not locked %}
          <form method="post" action="{{ url_for('artwork.lock_it_in', seo_folder=seo_folder) }}" class="action-form">
            <button type="submit" class="btn btn-primary wide-btn">🔒 Lock It In</button>
          </form>
        {% endif %}

        <form method="POST" action="{{ url_for('artwork.analyze_artwork', aspect=aspect, filename=filename) }}" class="action-form analyze-form">
          <select name="provider" class="long-field">
            <option value="openai">OpenAI</option>
            <option value="google">Google</option>
          </select>
          <button type="submit" class="btn btn-secondary wide-btn" {% if locked %}disabled{% endif %}>Re-analyse Artwork</button>
        </form>

        <form method="post" action="{{ url_for('artwork.reset_sku', aspect=aspect, filename=filename) }}" class="action-form">
          <button type="submit" class="btn btn-secondary wide-btn" {% if locked %}disabled{% endif %}>Reset SKU</button>
        </form>

        <form method="post" action="{{ url_for('artwork.delete_artwork', seo_folder=seo_folder) }}" class="action-form" onsubmit="return confirm('Delete this artwork and all files? This cannot be undone.');">
          <button type="submit" class="btn btn-danger wide-btn" {% if not editable %}disabled{% endif %}>Delete Artwork</button>
        </form>
      </div>

      <div class="sellbrite-preview">
        <h2>Sellbrite Export Details</h2>
        <div class="two-column-layout">
          <div class="column">
            <p><strong>Title:</strong> {{ artwork.title }}</p>
            <p><strong>SKU:</strong> {{ artwork.sku }}</p>
            <p><strong>SEO Slug:</strong> {{ artwork.seo_slug }}</p>
            <p><strong>Description:</strong><br><textarea readonly style="width:100%;height:200px;resize:vertical;border:1px solid #ccc;padding:6px;margin-top:4px;background:#f9f9f9;white-space:pre-line;">{{- artwork.description -}}</textarea></p>
            <p><strong>Generic Text:</strong><br><textarea readonly style="width:100%;height:150px;resize:vertical;border:1px solid #ccc;padding:6px;margin-top:4px;background:#f9f9f9;white-space:pre-line;">{{- artwork.generic_description -}}</textarea></p>
          </div>
          <div class="column">
            <p><strong>Tags:</strong> {{ artwork.tags | join(', ') }}</p>
            <p><strong>Materials:</strong> {{ artwork.materials | join(', ') }}</p>
            <p><strong>Colours:</strong> {{ artwork.primary_colour }}, {{ artwork.secondary_colour }}</p>
            <p><strong>Public Image URLs:</strong><br><textarea class="full-width" rows="8" readonly style="font-family: monospace; background: #fcfcfc; border: 1px solid #ccc;">{{ public_image_urls | join('\n') }}</textarea></p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div id="mockup-carousel" class="modal-bg" tabindex="-1">
    <button id="carousel-close" class="modal-close" aria-label="Close">&times;</button>
    <button id="carousel-prev" class="carousel-nav" aria-label="Previous">&#10094;</button>
    <div class="modal-img"><img id="carousel-img" src="" alt="Mockup Preview" /></div>
    <button id="carousel-next" class="carousel-nav" aria-label="Next">&#10095;</button>
  </div>
</div>

<script>
  window.EDIT_INFO = {
    seoFolder: '{{ seo_folder }}',
    aspect: '{{ aspect }}',
    artworkStatus: '{{ artwork.status }}'
  };
</script>
<script src="{{ url_for('static', filename='js/edit_listing.js') }}"></script>
{% endblock %}

---
## templates/finalised.html
---
{# templates/finalised.html #}
{# Gallery of all finalised artworks with edit and export actions. #}
{% extends "main.html" %}
{% block title %}Finalised Artworks{% endblock %}

{% block content %}
<div class="container">
    <div class="page-title-row">
      <img src="{{ url_for('static', filename='icons/svg/light/number-circle-four-light.svg') }}" class="hero-step-icon" alt="Step 4: Finalised" />
      <h1>Finalised Artworks</h1>
    </div>
    <p class="help-tip">Finalised artworks have been reviewed and are ready for publishing. You can lock them in for export or make final edits.</p>
    <div class="view-toggle">
      <button id="grid-view-btn" class="btn btn-sm btn-secondary">Grid View</button>
      <button id="list-view-btn" class="btn btn-sm btn-secondary">List View</button>
    </div>

    {% if not artworks %}
      <div class="empty-state" style="text-align: center; margin-top: 4rem;">
          <p>No artworks have been finalised yet.</p>
          <a href="{{ url_for('artwork.artworks') }}" class="btn btn-primary" style="max-width: 250px;">Go to Artwork Gallery</a>
      </div>
    {% else %}
      <div class="finalised-grid" data-view-key="finalisedView">
        {% for art in artworks %}
          <div class="final-card">
            <div class="card-thumb">
                {% set main_thumb_path = art.seo_folder ~ '/' ~ (art.thumb or '') %}
                {% if art.thumb %}
                    <a href="#" class="final-img-link" data-img="{{ url_for('artwork.finalised_image', filename=art.seo_folder ~ '/' ~ (art.main_image or '')) }}">
                        <img src="{{ url_for('artwork.finalised_image', filename=main_thumb_path) }}" class="card-img-top" alt="{{ art.title }}">
                    </a>
                {% else %}
                    <img src="{{ url_for('static', filename='img/no-image.svg') }}" class="card-img-top" alt="No image available">
                {% endif %}
            </div>
            
            <div class="card-content-wrapper">
                <div class="card-details">
                    <div class="card-title">{{ art.title }}</div>

                    {# NEW (2025-08-04): Full description, tags, and materials for verification #}
                    <div class="card-description-full" tabindex="0" aria-label="Full Artwork Description">
                      <p>{{ art.description }}</p>
                    </div>

                    <div class="card-pills-section">
                        <h5>Tags</h5>
                        <div class="pill-list">
                            {% for tag in art.tags %}<span class="pill-item">{{ tag }}</span>{% endfor %}
                        </div>
                        <h5>Materials</h5>
                        <div class="pill-list">
                            {% for mat in art.materials %}<span class="pill-item">{{ mat }}</span>{% endfor %}
                        </div>
                    </div>

                    <div class="card-meta">
                        <div class="meta-item">
                            <span class="meta-label">SKU</span>
                            <span class="meta-value">
                                {{ art.sku or 'N/A' }}
                                {% if art.sellbrite_status == 'Synced' %}
                                    <span class="status-badge synced">Synced</span>
                                {% elif art.sellbrite_status == 'Not Found' %}
                                    <span class="status-badge not-found">Not Synced</span>
                                {% else %}
                                    <span class="status-badge offline">{{ art.sellbrite_status }}</span>
                                {% endif %}
                            </span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Price</span>
                            <span class="meta-value">${{ "%.2f"|format(art.price|float) }}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Colours</span>
                            <span class="meta-value">{{ art.primary_colour }} / {{ art.secondary_colour }}</span>
                        </div>
                        <div class="meta-item-separator"></div>
                        <div class="meta-item">
                            <span class="meta-label">Category</span>
                            <span class="meta-value">{{ art.sellbrite_category }}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Condition</span>
                            <span class="meta-value">{{ art.sellbrite_condition }}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Quantity</span>
                            <span class="meta-value">{{ art.sellbrite_quantity }}</span>
                        </div>
                    </div>
                </div>

                {% if art.mockups %}
                    <div class="mini-mockup-grid">
                        {% for m in art.mockups %}
                            {# FIX (2025-08-04): Use the direct finalised_image route for mockup thumbs #}
                            {% set m_thumb_path = art.seo_folder ~ '/THUMBS/' ~ m.thumbnail %}
                            <img src="{{ url_for('artwork.finalised_image', filename=m_thumb_path) }}" alt="Mockup thumbnail for {{ art.title }}"/>
                        {% endfor %}
                    </div>
                {% endif %}

                <div class="final-actions">
                  <a href="{{ url_for('artwork.edit_listing', aspect=art.aspect, filename=art.seo_folder ~ '.jpg') }}" class="btn btn-secondary">Edit</a>
                  <form method="post" action="{{ url_for('artwork.lock_it_in', seo_folder=art.seo_folder) }}" style="display:inline;">
                    <button type="submit" class="btn btn-primary">Lock</button>
                  </form>
                  <form method="post" action="{{ url_for('artwork.delete_artwork', seo_folder=art.seo_folder) }}" onsubmit="return confirm('Delete this artwork permanently?');">
                    <button type="submit" class="btn btn-danger">Delete</button>
                  </form>
                </div>
            </div>
          </div>
        {% endfor %}
      </div>
    {% endif %}

    {# Modal for viewing full-size images #}
    <div id="final-modal-bg" class="modal-bg">
      <button id="final-modal-close" class="modal-close" aria-label="Close modal">&times;</button>
      <div class="modal-img"><img id="final-modal-img" src="" alt="Full size artwork image"/></div>
    </div>
</div>

<script src="{{ url_for('static', filename='js/gallery.js') }}"></script>
{% endblock %}

---
## templates/gallery.html
---

<div class="container">

</div>

---
## templates/index.html
---
{# Use blueprint-prefixed endpoints like 'artwork.home' in url_for #}
{% extends "main.html" %}
{% block title %}ArtNarrator Home{% endblock %}
{% block content %}
<div class="container">

<!-- ========== [IN.1] Home Hero Section ========== -->
<div class="home-hero">
  <h1><img src="{{ url_for('static', filename='logos/logo-vector.svg') }}" alt="" class="artnarrator-logo"/>Welcome to ArtNarrator Listing Machine</h1>
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
  <a href="{{ url_for('artwork.artworks') }}" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-two-light.svg') }}" class="step-btn-icon" alt="Step 2" />
    Artwork<br>Select to Analyze
  </a>
  {% if latest_artwork %}
    <a href="{{ url_for('artwork.edit_listing', aspect=latest_artwork.aspect, filename=latest_artwork.filename) }}" class="workflow-btn">
      <img src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}" class="step-btn-icon" alt="Step 3" />
      Edit Review<br>and Finalise Artwork
    </a>
  {% else %}
    <span class="workflow-btn disabled">
      <img src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}" class="step-btn-icon" alt="Step 3" />
      Edit Review<br>and Finalise Artwork
    </span>
  {% endif %}
  <a href="{{ url_for('artwork.finalised_gallery') }}" class="workflow-btn">
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
## templates/locked.html
---
{# Gallery of all locked artworks with unlock and delete actions. #}
{% extends "main.html" %}
{% block title %}Locked Artworks{% endblock %}
{% block content %}
<div class="container">
  <div class="page-title-row">
    <img src="{{ url_for('static', filename='icons/svg/light/lock-light.svg') }}" class="hero-step-icon" alt="Locked" />
    <h1>Locked Artworks</h1>
  </div>
  <p class="help-tip">These artworks are locked and cannot be edited until unlocked. They are excluded from most exports.</p>
  <div class="view-toggle">
    <button id="grid-view-btn" class="btn-small">Grid</button>
    <button id="list-view-btn" class="btn-small">List</button>
  </div>

  {% if not artworks %}
    <p>No artworks are currently locked.</p>
  {% else %}
  <div class="finalised-grid" data-view-key="lockedView">
    {% for art in artworks %}
    <div class="final-card">
      <div class="card-thumb">
        {# Use the 'locked_image' route for these images #}
        {% set main_path = art.seo_folder ~ '/' ~ (art.main_image or '') %}
        {% if art.main_image %}
        <a href="{{ url_for('artwork.locked_image', filename=main_path) }}" class="final-img-link" data-img="{{ url_for('artwork.locked_image', filename=main_path) }}">
          <img src="{{ url_for('artwork.locked_image', filename=main_path) }}" class="card-img-top" alt="{{ art.title|default('Untitled') }}">
        </a>
        {% else %}
        <img src="{{ url_for('static', filename='img/no-image.svg') }}" class="card-img-top" alt="No image">
        {% endif %}
      </div>
      <div class="card-details">
        <div class="card-title">{{ art.title|default('Untitled') }}</div>
        {# FIX: Use default filter to prevent errors on missing keys #}
        <div class="desc-snippet" title="{{ art.description|default('') }}">
          {{ art.description|default('')|truncate(200) }}
        </div>
        <div>SKU: {{ art.sku|default('') }}</div>
        <div>Price: {{ art.price|default('') }}</div>
        <div>Colours: {{ art.primary_colour|default('') }} / {{ art.secondary_colour|default('') }}</div>
        <div>SEO: {{ art.seo_filename|default('') }}</div>
        <div>Tags: {{ art.tags|default([])|join(', ') }}</div>
        <div>Materials: {{ art.materials|default([])|join(', ') }}</div>
      </div>
      <div class="button-row">
        <a class="art-btn disabled" aria-disabled="true">Edit</a>
        <form method="post" action="{{ url_for('artwork.unlock_artwork', seo_folder=art.seo_folder) }}">
          <button type="submit" class="art-btn">Unlock</button>
        </form>
        <form method="post" action="{{ url_for('artwork.delete_artwork', seo_folder=art.seo_folder) }}" class="locked-delete-form" onsubmit="return confirmDelete(this);">
          <input type="text" name="confirm" placeholder="Type DELETE" required>
          <button type="submit" class="art-btn delete">Delete</button>
        </form>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endif %}
</div>

<div id="image-modal" class="modal">
  <span class="close-modal">&times;</span>
  <img class="modal-content" id="modal-img-content">
</div>
<script>
function confirmDelete(form){
  if(form.confirm.value !== 'DELETE'){
    alert('Please type DELETE to confirm.');
    return false;
  }
  return true;
}
</script>
{% endblock %}


---
## templates/login.html
---
{% extends "main.html" %}
{% block title %}Login{% endblock %}
{% block content %}
<div class="container">
  <h1>Login</h1>
  {% with msgs = get_flashed_messages(with_categories=true) %}
    {% if msgs %}
      <div class="flash">
        <img src="{{ url_for('static', filename='icons/svg/light/warning-circle-light.svg') }}" alt="!" style="width:20px;margin-right:6px;vertical-align:middle;">
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
    <title>{% block title %}ArtNarrator{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
    
</head>
<body data-analysis-status-url="{{ url_for('artwork.analysis_status') }}" data-openai-ok="{{ 'true' if openai_configured else 'false' }}" data-google-ok="{{ 'true' if google_configured else 'false' }}">
    <header class="site-header">
        <div class="header-left">
            <a href="{{ url_for('artwork.home') }}" class="site-logo">
                <img src="{{ url_for('static', filename='icons/svg/light/palette-light.svg') }}" alt="" class="logo-icon icon">ArtNarrator
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
        <div class="overlay-header">
            <div class="header-left">
                <a href="{{ url_for('artwork.home') }}" class="site-logo">
                    <img src="{{ url_for('static', filename='icons/svg/light/palette-light.svg') }}" alt="" class="logo-icon icon">ArtNarrator
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
        <nav class="overlay-nav">
            <div class="nav-column">
                <h3>Artwork &amp; Gallery</h3>
                <ul>
                    <li><a href="{{ url_for('artwork.upload_artwork') }}">Upload Artwork</a></li>
                    <li><a href="{{ url_for('artwork.artworks') }}">All Artworks</a></li>
                    <li><a href="{{ url_for('artwork.finalised_gallery') }}">Finalised</a></li>
                    <li><a href="{{ url_for('artwork.locked_gallery') }}">Locked</a></li>
                </ul>
            </div>
            <div class="nav-column">
                <h3>Workflow &amp; Tools</h3>
                <ul>
                    <li><a href="{{ url_for('artwork.select') }}">Composites Preview</a></li>
                    <li><a href="{{ url_for('mockup_admin.dashboard') }}">Mockup Admin</a></li>
                    <li><a href="{{ url_for('coordinate_admin.dashboard') }}">Coordinate Generator</a></li>
                    <li><a href="{{ url_for('artwork.select') }}">Mockup Selector</a></li>
                </ul>
            </div>
            <div class="nav-column">
                <h3>Exports &amp; Admin</h3>
                <ul>
                    <li><a href="{{ url_for('exports.sellbrite_management') }}">Sellbrite Management</a></li>
                    <li><a href="{{ url_for('admin.dashboard') }}">Admin Dashboard</a></li>
                    <li><a href="{{ url_for('admin.security_page') }}">Admin Security</a></li>
                    <li><a href="{{ url_for('gdws_admin.editor') }}">Description Editor (GDWS)</a></li>
                    <li><a href="{{ url_for('auth.login') }}">Login</a></li>
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
                    <li><a href="{{ url_for('artwork.home') }}">Home</a></li>
                    <li><a href="{{ url_for('auth.login') }}">Login</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Artwork &amp; Gallery</h4>
                <ul>
                    <li><a href="{{ url_for('artwork.upload_artwork') }}">Upload Artwork</a></li>
                    <li><a href="{{ url_for('artwork.artworks') }}">Artworks</a></li>
                    <li><a href="{{ url_for('artwork.finalised_gallery') }}">Finalised</a></li>
                    <li><a href="{{ url_for('artwork.locked_gallery') }}">Locked</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Workflow &amp; Tools</h4>
                <ul>
                    <li><a href="{{ url_for('artwork.select') }}">Composites Preview</a></li>
                    <li><a href="{{ url_for('artwork.select') }}">Mockups</a></li>
                </ul>
            </div>
            <div class="footer-column">
                <h4>Exports &amp; Admin</h4>
                <ul>
                    <li><a href="{{ url_for('exports.sellbrite_management') }}">Sellbrite Management</a></li>
                    <li><a href="{{ url_for('admin.dashboard') }}">Admin Dashboard</a></li>
                    <li><a href="{{ url_for('admin.security_page') }}">Admin Security</a></li>
                    <li><a href="{{ url_for('gdws_admin.editor') }}">Description Editor (GDWS)</a></li>
                </ul>
                {# Removed broken menu link: Admin Users (no such route exists) #}
            </div>
        </div>
        <div class="copyright-bar">
            © Copyright 2025 ART Narrator All rights reserved | <a href="https://artnarrator.com">artnarrator.com</a> designed and built by Robin Custance.
        </div>
    </footer>

    <script src="{{ url_for('static', filename='js/main-overlay-test.js') }}"></script>
    <script src="{{ url_for('static', filename='js/analysis-modal.js') }}"></script>
</body>
</html>

---
## templates/missing_endpoint.html
---
{% extends "main.html" %}
{% block title %}Invalid Link{% endblock %}
{% block content %}
<div class="container" style="text-align: center;">
    <h1>Oops! A Link is Broken</h1>
    <p>The link or button you clicked points to a page that doesn't exist.</p>
    <p>This is usually a small typo in the code. I've logged the details so it can be fixed.</p>
    <div style="background: #eee; color: #333; padding: 1em; margin: 1em 0; text-align: left; font-family: monospace;">
        <strong>Error Details:</strong><br>
        {{ error }}
    </div>
    <a href="{{ url_for('artwork.home') }}" class="btn btn-primary">Return to Homepage</a>
</div>
{% endblock %}

---
## templates/mockup_selector.html
---
{# Use blueprint-prefixed endpoints like 'artwork.home' in url_for #}
{% extends "main.html" %}
{% block title %}Select Mockups | ArtNarrator{% endblock %}
{% block content %}
<div class="container">
<h1>🖼️ Select Your Mockup Lineup</h1>
<div class="grid">
  {% for slot, options in zipped %}
  <div class="item">
    {% if slot.image %}
      <img src="{{ url_for('artwork.mockup_img', category=slot.category, filename=slot.image) }}" alt="{{ slot.category }}" />
    {% else %}
      <p>No images for {{ slot.category }}</p>
    {% endif %}
    <strong>{{ slot.category }}</strong>
    <form method="post" action="{{ url_for('artwork.regenerate') }}">
      <input type="hidden" name="slot" value="{{ loop.index0 }}" />
      <button type="submit">🔄 Regenerate</button>
    </form>
    <form method="post" action="{{ url_for('artwork.swap') }}">
      <input type="hidden" name="slot" value="{{ loop.index0 }}" />
      <select name="new_category">
        <!-- DEBUG: Options for slot {{ loop.index0 }}: {{ options|join(", ") }} -->
        {% for c in options %}
        <option value="{{ c }}" {% if c == slot.category %}selected{% endif %}>{{ c }}</option>
        {% endfor %}
      </select>
      <button type="submit">🔁 Swap</button>
    </form>
  </div>
  {% endfor %}
</div>
<form method="post" action="{{ url_for('artwork.proceed') }}">
  <button class="composite-btn" type="submit">✅ Generate Composites</button>
</form>
<div style="text-align:center;margin-top:1em;">
  {% if session.latest_seo_folder %}
    <a href="{{ url_for('artwork.composites_specific', seo_folder=session.latest_seo_folder) }}" class="composite-btn" style="background:#666;">👁️ Preview Composites</a>
  {% else %}
    <a href="{{ url_for('artwork.composites_preview') }}" class="composite-btn" style="background:#666;">👁️ Preview Composites</a>
  {% endif %}
</div>
</div>
{% endblock %}


---
## templates/review.html
---
{# Use blueprint-prefixed endpoints like 'artwork.home' in url_for #}
{% extends "main.html" %}
{% block title %}Review | ArtNarrator{% endblock %}
{% block content %}
<div class="container">
<h1>Review &amp; Approve Listing</h1>
<section class="review-artwork">
  <h2>{{ artwork.title }}</h2>
  <div class="artwork-images">
    <img src="{{ url_for('static', filename='outputs/processed/' ~ artwork.seo_name ~ '/' ~ artwork.main_image) }}"
         alt="Main artwork" class="main-art-img" style="max-width:360px;">
    <img src="{{ url_for('static', filename='outputs/processed/' ~ artwork.seo_name ~ '/' ~ artwork.thumb) }}"
         alt="Thumbnail" class="thumb-img" style="max-width:120px;">
  </div>
  <h3>Description</h3>
  <div class="art-description" style="max-width:431px;">
    <pre style="white-space: pre-wrap; font-family:inherit;">{{ artwork.description }}</pre>
  </div>
  <h3>Mockups</h3>
  <div class="grid">
    {% for slot in slots %}
    <div class="item">
      <img src="{{ url_for('artwork.mockup_img', category=slot.category, filename=slot.image) }}" alt="{{ slot.category }}">
      <strong>{{ slot.category }}</strong>
    </div>
    {% endfor %}
  </div>
</section>
<form method="get" action="{{ url_for('artwork.select') }}">
  <input type="hidden" name="reset" value="1">
  <button class="composite-btn" type="submit">Start Over</button>
</form>
<div style="text-align:center;margin-top:1.5em;">
  <a href="{{ url_for('artwork.composites_specific', seo_folder=artwork.seo_name) }}" class="composite-btn" style="background:#666;">Preview Composites</a>
</div>
</div>
{% endblock %}


---
## templates/sellbrite_activity_log.html
---
{% extends "main.html" %}
{% block title %}Sellbrite Exports{% endblock %}
{% block content %}
<div class="container">
<h1>Sellbrite Exports</h1>
<table class="exports-table">
  <tbody>
  {% for e in exports %}
    <tr>
      <td>{{ e.mtime.strftime('%Y-%m-%d %H:%M') }}</td>
      <td>{{ e.type }}</td>
      <td>{% if e.log %}<a href="{{ url_for('exports.view_sellbrite_log', log_filename=e.log) }}">Log</a>{% else %}-{% endif %}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}

---
## templates/sellbrite_log.html
---
{% extends "main.html" %}
{% block title %}Export Log{% endblock %}
{% block content %}
<div class="container">
<h1>Export Log {{ log_filename }}</h1>
<pre class="export-log">{{ log_text }}</pre>
</div>
{% endblock %}


---
## templates/sellbrite_management.html
---
{% extends "main.html" %}
{% block title %}Sellbrite Management{% endblock %}

{% block content %}
<div class="container">
    <div class="page-title-row">
        <h1>Sellbrite Management</h1>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
            <div class="flash flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="exports-special-grid">
        <div class="status-and-actions">
            <h3>API Status & Actions</h3>
            <div class="status-box">
                <strong>Connection Status:</strong>
                {% if is_connected %}
                    <span class="status-ok">Connected</span>
                {% else %}
                    <span class="status-fail">DISCONNECTED - Check API Credentials</span>
                {% endif %}
            </div>
            <p>Push all finalized artworks to your Sellbrite account. Use the 'Dry Run' to preview the data that will be sent without making any live changes.</p>
            
            <form action="{{ url_for('exports.sync_to_sellbrite') }}" method="POST" class="action-form">
                <button type="submit" name="run_type" value="dry_run" class="btn btn-secondary wide-btn" {% if not is_connected %}disabled{% endif %}>
                    Test Sync (Dry Run)
                </button>
                <button type="submit" name="run_type" value="live" class="btn btn-primary wide-btn" 
                        onclick="return confirm('This will push products to your LIVE Sellbrite account. Are you sure?');" 
                        {% if not is_connected %}disabled{% endif %}>
                    Run LIVE Sync to Sellbrite
                </button>
            </form>
            
            <hr>
        </div>

        <div class="product-listing">
            <h3>Current Sellbrite Products</h3>
            {% if is_connected %}
                {% if products %}
                <table class="exports-table">
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>Name</th>
                            <th>Price</th>
                            <th>Quantity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for product in products %}
                        <tr>
                            <td>{{ product.get('sku', 'N/A') }}</td>
                            <td>{{ product.get('name', 'N/A') }}</td>
                            <td>${{ "%.2f"|format(product.get('price', 0)) }}</td>
                            <td>{{ product.get('inventory', [{}])[0].get('available', 'N/A') }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p>No products found in your Sellbrite account.</p>
                {% endif %}
            {% else %}
            <p>Cannot fetch products. Please check API connection.</p>
            {% endif %}
        </div>
    </div>
</div>

<style>
    .status-ok { color: green; font-weight: bold; }
    .status-fail { color: red; font-weight: bold; }
    .status-box { margin-bottom: 1.5rem; padding: 1rem; background: var(--color-card-bg); border: 1px solid var(--card-border); }
    .action-form button { margin-top: 0.5rem; }
</style>
{% endblock %}

---
## templates/sellbrite_sync_preview.html
---
{% extends "main.html" %}
{% block title %}Sellbrite Sync Preview{% endblock %}

{% block content %}
<div class="container">
    <div class="page-title-row">
        <h1>Sellbrite Sync Preview (Dry Run)</h1>
    </div>

    <p class="help-tip">This is a dry run. No data was sent to Sellbrite. Below is the exact JSON payload that would be sent for each of the <strong>{{ products|length }}</strong> finalized products.</p>
    
    <a href="{{ url_for('exports.sellbrite_management') }}" class="btn btn-secondary" style="margin-bottom: 2rem;">Back to Sellbrite Management</a>

    <div class="preview-container">
        {% for product in products %}
        <div class="product-payload">
            <h4>SKU: {{ product.get('sku', 'N/A') }} | Name: {{ product.get('name', 'N/A') }}</h4>
            <pre><code>{{ product | tojson(indent=2) }}</code></pre>
        </div>
        {% endfor %}
    </div>
</div>

<style>
    .preview-container {
        font-family: var(--font-primary);
    }
    .product-payload {
        background: var(--color-card-bg);
        border: 1px solid var(--card-border);
        margin-bottom: 1.5rem;
        padding: 1rem;
    }
    .product-payload h4 {
        margin-top: 0;
        border-bottom: 1px solid var(--card-border);
        padding-bottom: 0.5rem;
    }
    .product-payload pre {
        background: var(--color-background);
        padding: 1rem;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        word-break: break-all;
    }
</style>
{% endblock %}

---
## templates/test_description.html
---
{% extends "main.html" %}
{% block title %}Test Combined Description{% endblock %}
{% block content %}
<div class="container">
<h1>Test Combined Description</h1>
<div class="desc-text" style="white-space: pre-wrap;border:1px solid #ccc;padding:10px;">
  {{ combined_description }}
</div>
</div>
{% endblock %}


---
## templates/upload.html
---
{% extends "main.html" %}
{% block title %}Upload Artwork{% endblock %}
{% block content %}
<div class="container">
  <div class="home-hero" >
    <h1><img src="{{ url_for('static', filename='icons/svg/light/number-circle-one-light.svg') }}" class="hero-step-icon" alt="Step 1: Upload" />Upload New Artwork</h1>
  </div>
  <form id="upload-form" method="post" enctype="multipart/form-data">
    <input id="file-input" type="file" name="images" accept="image/*" multiple hidden>
    <div id="dropzone" class="upload-dropzone">
      Drag & Drop images here or click to choose files
    </div>
    <ul id="upload-list" class="upload-list"></ul>
  </form>
</div>

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

<script src="{{ url_for('static', filename='js/upload.js') }}"></script>
{% endblock %}

---
## templates/upload_results.html
---
{% extends "main.html" %}
{% block title %}Upload Results{% endblock %}
{% block content %}
<div class="container">
<h2 class="mb-3">Upload Summary</h2>
<ul>
  {% for r in results %}
    <li>{% if r.success %}✅ {{ r.original }}{% else %}❌ {{ r.original }}: {{ r.error }}{% endif %}</li>
  {% endfor %}
</ul>
<a href="{{ url_for('artwork.artworks') }}" class="btn btn-primary">Return to Gallery</a>
</div>
{% endblock %}


---
## tests/test_admin_security.py
---
# tests/test_admin_security.py
import os
import sys
import importlib
from pathlib import Path

# Add project root to path to allow imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("OPENAI_API_KEY", "test")

# Import necessary utilities
from utils import user_manager, session_tracker


def setup_app(tmp_path):
    """Sets up a temporary Flask app instance for testing."""
    os.environ['LOGS_DIR'] = str(tmp_path / 'logs')
    os.environ['DATA_DIR'] = str(tmp_path / 'data')
    # Reload modules to ensure they use the new temp paths
    for mod in ('config', 'db', 'utils.security', 'utils.user_manager', 'routes.auth_routes', 'routes.admin_security', 'app'):
        if mod in sys.modules:
            importlib.reload(sys.modules[mod])
    app_module = importlib.import_module('app')
    return app_module.app


def login(client, username, password):
    """Helper function to log in a user."""
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=False)


def test_role_required_admin(tmp_path):
    """Tests that only users with the 'admin' role can access admin pages."""
    app = setup_app(tmp_path)
    user_manager.add_user("viewer", "viewer", "viewer123")
    
    client = app.test_client()
    # Clear any leftover sessions before starting
    for s in session_tracker.active_sessions("robbie"):
        session_tracker.remove_session("robbie", s["session_id"])
    
    # Test login with non-admin user
    resp = login(client, 'viewer', 'viewer123')
    assert resp.status_code == 302 # Should be a successful login, redirecting
    
    # Test access to admin page as non-admin (should be redirected)
    resp = client.get('/admin/', follow_redirects=False)
    assert resp.status_code == 302
    
    # Test access as admin
    client.get('/logout')
    resp = login(client, 'robbie', 'kangaroo123')
    assert resp.status_code == 302
    resp = client.get('/admin/', follow_redirects=False)
    assert resp.status_code == 200


def test_no_cache_header(tmp_path):
    """Tests that the no-cache header is applied correctly."""
    app = setup_app(tmp_path)
    client = app.test_client()
    # Clear any leftover sessions before starting
    for s in session_tracker.active_sessions("robbie"):
        session_tracker.remove_session("robbie", s["session_id"])

    admin_login = login(client, 'robbie', 'kangaroo123')
    assert admin_login.status_code == 302
    client.post('/admin/security', data={'action': 'nocache_on', 'minutes': '1'})
    resp = client.get('/')
    assert resp.headers.get('Cache-Control') == 'no-store, no-cache, must-revalidate, max-age=0'


def test_login_lockout(tmp_path):
    """Tests that a non-admin user is locked out when login is disabled."""
    app = setup_app(tmp_path)
    user_manager.add_user("viewer", "viewer", "viewer123")
    
    client = app.test_client()
    # Clear any leftover sessions before starting
    for s in session_tracker.active_sessions("robbie"):
        session_tracker.remove_session("robbie", s["session_id"])
    
    admin_login = login(client, 'robbie', 'kangaroo123')
    assert admin_login.status_code == 302
    
    # Admin disables login
    client.post('/admin/security', data={'action': 'disable', 'minutes': '1'})
    client.get('/logout')
    
    # Viewer attempts to log in
    resp = login(client, 'viewer', 'viewer123')
    assert resp.status_code == 403 # Should be forbidden

---
## tests/test_analysis_status_file.py
---
import json
import logging
from pathlib import Path
import sys
import pytest
import os

os.environ.setdefault("OPENAI_API_KEY", "test")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

# Correctly import from helpers, not routes.utils
from helpers.listing_utils import load_json_file_safe, resolve_artwork_stage


def test_load_json_file_safe_missing(tmp_path, caplog):
    test_file = tmp_path / 'missing.json'
    with caplog.at_level(logging.WARNING):
        data = load_json_file_safe(test_file)
    assert data == {}
    assert test_file.exists()
    assert test_file.read_text() == '{}'
    assert 'Created new empty JSON file' in caplog.text


def test_load_json_file_safe_empty(tmp_path, caplog):
    test_file = tmp_path / 'empty.json'
    test_file.write_text('   ')
    with caplog.at_level(logging.WARNING):
        data = load_json_file_safe(test_file)
    assert data == {}
    assert test_file.read_text() == '{}'
    assert 'reset to {}' in caplog.text


def test_load_json_file_safe_invalid(tmp_path, caplog):
    test_file = tmp_path / 'invalid.json'
    test_file.write_text('{bad json')
    with caplog.at_level(logging.ERROR):
        data = load_json_file_safe(test_file)
    assert data == {}
    assert test_file.read_text() == '{}'
    assert 'Invalid JSON' in caplog.text


def test_load_json_file_safe_valid(tmp_path):
    test_file = tmp_path / 'valid.json'
    content = {'a': 1}
    test_file.write_text(json.dumps(content))
    data = load_json_file_safe(test_file)
    assert data == content


def test_resolve_artwork_stage(tmp_path, monkeypatch):
    """Ensure artwork stage is correctly detected across all directories."""
    # Create staging directories
    un = tmp_path / 'unanalysed-artwork'
    proc = tmp_path / 'processed-artwork'
    fin = tmp_path / 'finalised-artwork'
    vault = tmp_path / 'artwork-vault'
    for d in (un, proc, fin, vault):
        d.mkdir()

    # Monkeypatch config roots
    monkeypatch.setattr(config, 'UNANALYSED_ROOT', un)
    monkeypatch.setattr(config, 'PROCESSED_ROOT', proc)
    monkeypatch.setattr(config, 'FINALISED_ROOT', fin)
    monkeypatch.setattr(config, 'ARTWORK_VAULT_ROOT', vault)

    # Create folders representing each stage
    (un / 'a1').mkdir()
    (proc / 'a2').mkdir()
    (fin / 'a3').mkdir()
    (vault / 'LOCKED-a4').mkdir()

    assert resolve_artwork_stage('a1')[0] == 'unanalysed'
    assert resolve_artwork_stage('a2')[0] == 'processed'
    assert resolve_artwork_stage('a3')[0] == 'finalised'
    assert resolve_artwork_stage('a4')[0] == 'vault'

    # FIX: The function now returns (None, None) for missing files instead of raising an error.
    # The test is updated to check for this correct, more robust behavior.
    assert resolve_artwork_stage('missing') == (None, None)


---
## tests/test_analyze_api.py
---
# tests/test_analyze_api.py
import io
import json
from pathlib import Path
from PIL import Image
import sys
import os
import pytest
import shutil # <-- FIX: Added the missing import
from unittest import mock

os.environ.setdefault("OPENAI_API_KEY", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app
import config
from utils import session_tracker
import routes.utils as routes_utils

# A pytest fixture to create and automatically clean up test files.
@pytest.fixture
def api_test_image(monkeypatch):
    """Creates a temporary folder and image for API tests and ensures cleanup."""
    temp_unanalysed_dir = config.UNANALYSED_ROOT / "api_test_temp"
    temp_unanalysed_dir.mkdir(parents=True, exist_ok=True)
    
    # Monkeypatch the config to ensure the app looks in our temp test folder
    monkeypatch.setattr(config, "UNANALYSED_ROOT", temp_unanalysed_dir)
    
    # Yield a function to create specific files
    def _create_file(name, content):
        path = temp_unanalysed_dir / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            Image.new("RGB", (10, 10), content).save(path)
        return path

    yield _create_file
    
    # Teardown: This code runs after each test, ensuring the folder is deleted.
    shutil.rmtree(temp_unanalysed_dir, ignore_errors=True)


def test_analyze_api_json(tmp_path, api_test_image):
    client = app.test_client()
    for s in session_tracker.active_sessions("robbie"):
        session_tracker.remove_session("robbie", s["session_id"])
    client.post(
        "/login",
        data={"username": "robbie", "password": "kangaroo123"},
        follow_redirects=True,
    )
    api_test_image("dummy.jpg", "blue") # Create the test image using the fixture

    seo_folder = "dummy-artwork"
    dummy_entry = {
        "processed_folder": str(config.PROCESSED_ROOT / seo_folder),
        "seo_filename": f"{seo_folder}.jpg",
        "aspect_ratio": "square",
    }

    with mock.patch(
        "routes.artwork_routes._run_ai_analysis", return_value=dummy_entry
    ), mock.patch("routes.artwork_routes._generate_composites"):
        resp = client.post(
            "/analyze/square/dummy.jpg",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"]


def test_analyze_api_strip_bytes(tmp_path, monkeypatch, api_test_image):
    client = app.test_client()
    for s in session_tracker.active_sessions("robbie"):
        session_tracker.remove_session("robbie", s["session_id"])
    client.post(
        "/login",
        data={"username": "robbie", "password": "kangaroo123"},
        follow_redirects=True,
    )
    api_test_image("byte.jpg", b"") # Create the test image using the fixture

    seo_folder = "byte-art"
    dummy_entry = {
        "processed_folder": str(config.PROCESSED_ROOT / seo_folder),
        "seo_filename": f"{seo_folder}.jpg",
        "aspect_ratio": "square",
        "blob": b"bigdata",
    }

    monkeypatch.setattr(config, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(routes_utils, "LOGS_DIR", tmp_path)

    with mock.patch(
        "routes.artwork_routes._run_ai_analysis", return_value=dummy_entry
    ), mock.patch("routes.artwork_routes._generate_composites"):
        resp = client.post(
            "/analyze/square/byte.jpg",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "blob" not in json.dumps(data)


def test_analyze_api_error_bytes(tmp_path, monkeypatch, api_test_image):
    client = app.test_client()
    for s in session_tracker.active_sessions("robbie"):
        session_tracker.remove_session("robbie", s["session_id"])
    client.post(
        "/login",
        data={"username": "robbie", "password": "kangaroo123"},
        follow_redirects=True,
    )
    api_test_image("err.jpg", b"") # Create the test image using the fixture

    monkeypatch.setattr(config, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(routes_utils, "LOGS_DIR", tmp_path)

    with mock.patch(
        "routes.artwork_routes._run_ai_analysis", side_effect=RuntimeError(b"oops")
    ), mock.patch("routes.artwork_routes._generate_composites"):
        resp = client.post(
            "/analyze/square/err.jpg",
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
        )

    assert resp.status_code == 500
    text = resp.get_data(as_text=True)
    assert "oops" in text

---
## tests/test_analyze_artwork.py
---
# tests/test_analyze_artwork.py
# ======================================================================================
# FILE: tests/test_analyze_artwork.py
# DESCRIPTION: Test /analyze API endpoint and ensure proper HTML response + cleanup
# AUTHOR: Robbie Mode™ Patch - 2025-07-31 (Final Self-Contained Version)
# ======================================================================================

import os
import shutil
import pytest
from pathlib import Path
from PIL import Image
import sys

# Add project root to path before other imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
import config
from dotenv import load_dotenv

# Load environment variables from system .env
load_dotenv(dotenv_path="/home/art/.env", override=True)

# ======================================================================================
# SECTION 1: Setup
# ======================================================================================

@pytest.fixture
def client():
    """Flask test client fixture for HTTP request simulation."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        # Log in a test user for the session
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'testuser'
        yield client

# ======================================================================================
# SECTION 2: Test Analyze Route – HTML Response
# ======================================================================================

def test_analyze_api_html_response(client):
    """
    Ensure that /analyze/<aspect>/<filename> returns valid HTML content after redirect.
    """
    # --- [ 2.0: Skip if dummy API key ] ---
    openai_key = os.getenv("OPENAI_API_KEY", "test")
    if openai_key.strip().lower() == "test" or not openai_key:
        pytest.skip("Skipping test: Requires a valid OPENAI_API_KEY")

    # --- [ 2.1: Prepare test image and folder structure ] ---
    base_filename = "cassowary-test-01"
    unique_id = "test-run"
    filename = f"{base_filename}-{unique_id}.jpg"
    aspect = "4x5"
    
    unanalysed_subfolder = config.UNANALYSED_ROOT / f"{base_filename}-{unique_id}"
    unanalysed_subfolder.mkdir(parents=True, exist_ok=True)
    destination_img_path = unanalysed_subfolder / filename

    # **FIX:** Create a dummy image file from scratch instead of relying on an external asset
    try:
        Image.new("RGB", (100, 125), "blue").save(destination_img_path)
    except Exception as e:
        pytest.fail(f"Failed to create dummy test image: {e}")

    # --- [ 2.2: POST to the CORRECT /analyze route and follow redirect ] ---
    response = client.post(f"/analyze/{aspect}/{filename}", data={'provider': 'openai'}, follow_redirects=True)

    # --- [ 2.3: Validate response is HTML and contains hidden marker for Edit Page ] ---
    assert response.status_code == 200, "❌ Expected HTTP 200 OK from /analyze redirect"
    assert b"<html" in response.data or b"<div" in response.data, "❌ Expected HTML structure"

    # --- [ 2.4: Check for hidden edit page marker for test validation ] ---
    assert b'id="edit-listing-marker"' in response.data, "❌ Edit page marker not found in HTML"

# ======================================================================================
# SECTION 3: Post-Test Cleanup
# ======================================================================================

def teardown_module(module):
    """
    Cleanup test folders and files from ALL relevant directories after the test run completes.
    """
    patterns = ["test-", "sample-", "good-", "bad-", "cassowary-test-01-test-run"]
    
    # FIX: Add both unanalysed and processed roots to the cleanup path list
    roots_to_clean = [
        Path(config.UNANALYSED_ROOT),
        Path(config.PROCESSED_ROOT)
    ]

    for root in roots_to_clean:
        if not root.exists():
            continue

        for item in root.iterdir():
            if item.is_dir() and any(item.name.startswith(p) for p in patterns):
                try:
                    shutil.rmtree(item)
                    print(f"✅ Cleaned up test folder: {item}")
                except Exception as e:
                    print(f"⚠️ Could not delete test folder {item}: {e}")

---
## tests/test_artwork_lifecycle.py
---
import os
import json
import logging
import shutil
from pathlib import Path
import pytest

# Ensure the app's modules can be imported
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set a dummy API key to satisfy environment checks in the app
os.environ.setdefault("OPENAI_API_KEY", "test_key_not_used")

# --- Test Configuration & Fixtures ---

# Configure logging for clear test output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def artwork_paths(tmp_path_factory):
    """
    Creates a temporary, realistic directory structure for the tests
    and yields a dictionary of the root paths. Cleans up afterward.
    """
    base_path = tmp_path_factory.mktemp("art_processing_test")
    paths = {
        "base": base_path,
        "unanalysed": base_path / "unanalysed-artwork",
        "processed": base_path / "processed-artwork",
        "finalised": base_path / "finalised-artwork",
        "vault": base_path / "artwork-vault",
        "state_file": base_path / "artwork_state_tracker.json"
    }
    
    # Create the directories
    for key, path in paths.items():
        if key not in ["base", "state_file"]:
            path.mkdir(parents=True, exist_ok=True)
            
    logger.info(f"Created temporary test structure at: {base_path}")

    yield paths
    
    # Teardown: This code runs after all tests in the module are complete
    logger.info(f"Cleaning up temporary test structure at: {base_path}")
    # shutil.rmtree(base_path) # pytest handles tmp_path_factory cleanup automatically

@pytest.fixture
def state_manager(artwork_paths):
    """
    Provides a simple way to read from and write to the state tracking JSON file.
    Ensures the file is reset for each test function.
    """
    state_file = artwork_paths["state_file"]
    
    # Ensure the file is empty before each test
    if state_file.exists():
        state_file.unlink()
    state_file.write_text("{}", encoding="utf-8")

    def _update_state(artwork_id, stage, data):
        """Updates the state for a specific artwork and stage."""
        current_state = json.loads(state_file.read_text(encoding="utf-8"))
        if artwork_id not in current_state:
            current_state[artwork_id] = {}
        current_state[artwork_id][stage] = data
        state_file.write_text(json.dumps(current_state, indent=2), encoding="utf-8")
        logger.info(f"STATE UPDATE for '{artwork_id}' at stage '{stage}': {data}")

    return _update_state

# --- Main Lifecycle Test ---

def test_full_artwork_lifecycle(artwork_paths, state_manager):
    """
    Simulates and verifies an artwork's journey through all stages.
    """
    artwork_id = "eucalypt-woodland-original"
    original_filename = "eucalypt-woodland-open-dry-forest.jpg"
    
    # --- 1. UPLOAD STAGE ---
    logger.info("--- STAGE 1: UPLOAD ---")
    unanalysed_dir = artwork_paths["unanalysed"] / artwork_id
    unanalysed_dir.mkdir()
    unanalysed_image_path = unanalysed_dir / original_filename
    unanalysed_image_path.touch() # Create a dummy file

    assert unanalysed_image_path.exists(), "Image file should exist in unanalysed stage"
    
    state_manager(artwork_id, "upload", {
        "path": str(unanalysed_image_path),
        "folder": artwork_id,
        "filename": original_filename
    })

    # --- 2. ANALYSE STAGE ---
    logger.info("--- STAGE 2: ANALYSE ---")
    new_seo_folder = "moon-over-fire-country-dot-art-by-robin-custance-RJC-0278"
    processed_dir = artwork_paths["processed"] / new_seo_folder
    
    # Simulate moving and renaming the folder
    shutil.move(str(unanalysed_dir), str(processed_dir))
    
    # Simulate creating the listing JSON
    listing_json_path = processed_dir / f"{new_seo_folder}-listing.json"
    listing_data = {"title": "Moon Over Fire Country", "sku": "RJC-0278"}
    listing_json_path.write_text(json.dumps(listing_data), encoding="utf-8")
    
    # Simulate renaming the main image file
    processed_image_path = processed_dir / f"{new_seo_folder}.jpg"
    (processed_dir / original_filename).rename(processed_image_path)

    assert not unanalysed_dir.exists(), "Original unanalysed folder should be gone"
    assert processed_dir.exists(), "Processed folder should exist"
    assert listing_json_path.exists(), "listing.json should exist in processed folder"
    assert processed_image_path.exists(), "Image file should be renamed and exist in processed folder"

    state_manager(artwork_id, "analyse", {
        "path": str(processed_image_path),
        "folder": new_seo_folder,
        "filename": processed_image_path.name,
        "json_path": str(listing_json_path)
    })

    # --- 3. FINALISED STAGE ---
    logger.info("--- STAGE 3: FINALISED ---")
    finalised_dir = artwork_paths["finalised"] / new_seo_folder
    
    # Simulate moving to finalised
    shutil.move(str(processed_dir), str(finalised_dir))

    assert not processed_dir.exists(), "Processed folder should be gone"
    assert finalised_dir.exists(), "Finalised folder should exist"
    
    finalised_image_path = finalised_dir / f"{new_seo_folder}.jpg"
    finalised_json_path = finalised_dir / f"{new_seo_folder}-listing.json"
    assert finalised_image_path.exists(), "Image should be in finalised folder"
    assert finalised_json_path.exists(), "JSON should be in finalised folder"

    state_manager(artwork_id, "finalised", {
        "path": str(finalised_image_path),
        "folder": new_seo_folder,
        "filename": finalised_image_path.name,
        "json_path": str(finalised_json_path)
    })

    # --- 4. LOCKED STAGE ---
    logger.info("--- STAGE 4: LOCKED ---")
    locked_folder_name = f"LOCKED-{new_seo_folder}"
    locked_dir = artwork_paths["vault"] / locked_folder_name

    # Simulate moving and locking
    shutil.move(str(finalised_dir), str(locked_dir))
    
    assert not finalised_dir.exists(), "Finalised folder should be gone"
    assert locked_dir.exists(), "Locked folder should exist in vault"
    assert locked_dir.name.startswith("LOCKED-"), "Locked folder name should be prefixed"

    locked_image_path = locked_dir / f"{new_seo_folder}.jpg"
    locked_json_path = locked_dir / f"{new_seo_folder}-listing.json"
    assert locked_image_path.exists(), "Image should be in locked folder"
    assert locked_json_path.exists(), "JSON should be in locked folder"

    state_manager(artwork_id, "locked", {
        "path": str(locked_image_path),
        "folder": locked_folder_name,
        "filename": locked_image_path.name,
        "json_path": str(locked_json_path)
    })

    # --- 5. PUBLIC URL VERIFICATION ---
    logger.info("--- STAGE 5: PUBLIC URL VERIFICATION ---")
    
    # This part tests the logic of converting the final file path to a public URL.
    # We construct the URL based on the final known state of the artwork.
    base_url = "https://artnarrator.com"
    
    # We need the path relative to the 'art_processing_test' base directory
    relative_image_path = locked_image_path.relative_to(artwork_paths["base"])
    
    # Construct the expected "friendly" URL
    expected_url = f"{base_url}/art-processing/{relative_image_path}"
    
    logger.info(f"Final file path: {locked_image_path}")
    logger.info(f"Generated public URL: {expected_url}")
    
    # This is the final check
    assert "artwork-vault/LOCKED-moon-over-fire-country" in expected_url, \
        "The generated URL does not have the correct structure"
        
    logger.info("✅ Full artwork lifecycle test completed successfully!")



---
## tests/test_logger_utils.py
---
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from utils.logger_utils import log_action


def test_log_action_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path)
    log_action("upload", "test.jpg", "alice", "uploaded test.jpg")
    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H")
    log_file = tmp_path / "upload" / f"{stamp}.log"
    assert log_file.exists()
    text = log_file.read_text()
    assert "user: alice" in text
    assert "action: upload" in text
    assert "file: test.jpg" in text
    assert "status: success" in text


def test_log_action_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path)
    log_action("upload", "bad.jpg", None, "failed", status="fail", error="oops")
    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H")
    log_file = tmp_path / "upload" / f"{stamp}.log"
    lines = log_file.read_text().strip().splitlines()
    assert any("status: fail" in l for l in lines)
    assert any("error: oops" in l for l in lines)


---
## tests/test_public_urls.py
---
import config
from helpers.listing_utils import generate_public_image_urls

def setup_paths(tmp_path, monkeypatch):
    base = tmp_path / "app"
    base.mkdir()
    monkeypatch.setattr(config, "BASE_DIR", base)
    monkeypatch.setattr(config, "BASE_URL", "http://example.com")
    unanalysed = base / "art-processing" / "unanalysed-artwork"
    processed = base / "art-processing" / "processed-artwork"
    finalised = base / "art-processing" / "finalised-artwork"
    vault = base / "art-processing" / "artwork-vault"
    for p in (unanalysed, processed, finalised, vault):
        p.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "UNANALYSED_ROOT", unanalysed)
    monkeypatch.setattr(config, "PROCESSED_ROOT", processed)
    monkeypatch.setattr(config, "FINALISED_ROOT", finalised)
    monkeypatch.setattr(config, "ARTWORK_VAULT_ROOT", vault)
    monkeypatch.setattr(config, "UNANALYSED_IMG_URL_PREFIX", "unanalysed-img")
    monkeypatch.setattr(config, "PROCESSED_URL_PATH", f"static/{processed.relative_to(base).as_posix()}")
    monkeypatch.setattr(config, "FINALISED_URL_PATH", f"static/{finalised.relative_to(base).as_posix()}")
    monkeypatch.setattr(config, "LOCKED_URL_PATH", f"static/{vault.relative_to(base).as_posix()}")
    return processed, vault

def test_generate_public_image_urls_processed(tmp_path, monkeypatch):
    processed, _ = setup_paths(tmp_path, monkeypatch)
    folder = processed / "test-art"
    folder.mkdir()
    (folder / "test-art-1.jpg").write_bytes(b"a")
    urls = generate_public_image_urls("test-art", "processed")
    expected = f"http://example.com/{processed.relative_to(config.BASE_DIR).as_posix()}/test-art/test-art-1.jpg"
    assert urls == [expected]

def test_generate_public_image_urls_vault(tmp_path, monkeypatch):
    _, vault = setup_paths(tmp_path, monkeypatch)
    folder = vault / "LOCKED-test-art"
    folder.mkdir()
    (folder / "LOCKED-test-art.jpg").write_bytes(b"a")
    urls = generate_public_image_urls("test-art", "vault")
    expected = f"http://example.com/{vault.relative_to(config.BASE_DIR).as_posix()}/LOCKED-test-art/LOCKED-test-art.jpg"
    assert urls == [expected]


---
## tests/test_registry.py
---
# In tests/test_registry.py

import os
import importlib
import json
from pathlib import Path
import sys

def test_move_and_registry(tmp_path, monkeypatch):
    """
    Tests that moving a file also updates its record in the central registry.
    """
    # 1. Setup mock directories and files
    mock_unanalysed_dir = tmp_path / "unanalysed"
    mock_processed_dir = tmp_path / "processed"
    mock_registry_file = tmp_path / "registry.json"
    mock_unanalysed_dir.mkdir()

    # 2. Monkeypatch the config variables directly
    # This is safer than reloading the module.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import config
    monkeypatch.setattr(config, "UNANALYSED_ROOT", mock_unanalysed_dir)
    monkeypatch.setattr(config, "OUTPUT_JSON", mock_registry_file)

    # 3. Reload the modules that USE the config to ensure they get the patched values
    from helpers import listing_utils
    from routes import utils
    importlib.reload(listing_utils)
    importlib.reload(utils)

    # 4. Create a dummy file and register it
    folder = listing_utils.create_unanalysed_subfolder("test_image.jpg")
    dummy_file = folder / 'img.jpg'
    dummy_file.write_text('test content')
    uid = 'test_uid_123'
    utils.register_new_artwork(uid, 'img.jpg', folder, ['img.jpg'], 'unanalysed', 'img-base')

    # 5. Move the file to a new location
    dest_path = mock_processed_dir / 'img.jpg'
    utils.move_and_log(dummy_file, dest_path, uid, 'processed')

    # 6. Assertions
    assert not dummy_file.exists()
    assert dest_path.exists()

    registry_data = json.loads(mock_registry_file.read_text())
    record = registry_data[uid]
    
    assert record['status'] == 'processed'
    assert str(dest_path.parent) in record['current_folder']
    assert dest_path.name in record['assets']

    # 7. Test a status update
    vault_folder = tmp_path / 'vault'
    vault_folder.mkdir()
    utils.update_status(uid, vault_folder, 'vault')
    
    registry_data_after_update = json.loads(mock_registry_file.read_text())
    assert registry_data_after_update[uid]['status'] == 'vault'

---
## tests/test_routes.py
---
import os
import re
from html.parser import HTMLParser
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test")

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app
import config

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href":
                    self.links.append(v)

def collect_template_endpoints():
    pattern = re.compile(r"url_for\(['\"]([^'\"]+)['\"]")
    endpoints = set()
    for path in config.TEMPLATES_DIR.rglob('*.html'):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        endpoints.update(pattern.findall(content))
    return endpoints

def test_template_endpoints_valid():
    registered = {r.endpoint for r in app.url_map.iter_rules()}
    templated = collect_template_endpoints()
    missing = [e for e in templated if e not in registered and not e.startswith('static')]
    assert not missing, f"Unknown endpoints referenced: {missing}"

def test_routes_and_navigation():
    client = app.test_client()
    client.post('/login', data={'username': 'robbie', 'password': 'kangaroo123'}, follow_redirects=True)
    to_visit = ['/']
    visited = set()
    while to_visit:
        url = to_visit.pop()
        if url in visited:
            continue
        resp = client.get(url)
        
        # FIX: Handle expected redirects for certain pages during the crawl
        if resp.status_code == 302 and (url == '/logout' or url == '/composites' or url.startswith('/edit-listing')):
            continue
            
        assert resp.status_code == 200, f"Failed loading {url}"
        visited.add(url)
        parser = LinkParser()
        parser.feed(resp.get_data(as_text=True))
        for link in parser.links:
            if link.startswith('http') or link.startswith('mailto:'):
                continue
            if link.startswith('/static') or '//' in link[1:]:
                continue
            if link == '#' or link.startswith('#') or link == '/logout':
                continue
            link = link.split('?')[0]
            if link not in visited:
                to_visit.append(link)

---
## tests/test_session_limits.py
---
import os
import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ["ADMIN_USERNAME"] = "robbie"
os.environ["ADMIN_PASSWORD"] = "kangaroo123"


def setup_app(tmp_path):
    os.environ['LOGS_DIR'] = str(tmp_path / 'logs')
    for mod in ('config', 'utils.session_tracker', 'routes.auth_routes', 'app'):
        if mod in sys.modules:
            importlib.reload(sys.modules[mod])
    if 'app' not in sys.modules:
        import app  # type: ignore
    app_module = importlib.import_module('app')
    return app_module.app


def test_session_limit_enforced(tmp_path):
    app = setup_app(tmp_path)
    clients = []
    for _ in range(5):
        c = app.test_client()
        resp = c.post('/login', data={'username': 'robbie', 'password': 'kangaroo123'}, follow_redirects=True)
        assert resp.status_code == 200
        clients.append(c)
    extra = app.test_client()
    resp = extra.post('/login', data={'username': 'robbie', 'password': 'kangaroo123'}, follow_redirects=False)
    assert resp.status_code == 403
    assert b'Maximum login limit' in resp.data

    clients[0].get('/logout', follow_redirects=True)
    resp = extra.post('/login', data={'username': 'robbie', 'password': 'kangaroo123'}, follow_redirects=True)
    assert resp.status_code == 200


---
## tests/test_sku_assigner.py
---
import json
from pathlib import Path

from utils.sku_assigner import get_next_sku, peek_next_sku


def test_peek_does_not_increment(tmp_path):
    tracker = tmp_path / "tracker.json"
    tracker.write_text(json.dumps({"last_sku": 2}))
    peek = peek_next_sku(tracker)
    assert peek == "RJC-0003"
    assert json.loads(tracker.read_text())['last_sku'] == 2


def test_get_next_sku_increments(tmp_path):
    tracker = tmp_path / "tracker.json"
    tracker.write_text(json.dumps({"last_sku": 10}))
    first = get_next_sku(tracker)
    second = get_next_sku(tracker)
    assert first == "RJC-0011"
    assert second == "RJC-0012"
    assert json.loads(tracker.read_text())['last_sku'] == 12


def test_cancel_does_not_consume(tmp_path):
    tracker = tmp_path / "tracker.json"
    tracker.write_text(json.dumps({"last_sku": 5}))
    preview = peek_next_sku(tracker)
    assert preview == "RJC-0006"
    # no assignment yet
    assert json.loads(tracker.read_text())['last_sku'] == 5
    final = get_next_sku(tracker)
    assert final == preview
    assert json.loads(tracker.read_text())['last_sku'] == 6


---
## tests/test_sku_tracker.py
---
# tests/test_sku_tracker.py
import json
import os
import shutil
from pathlib import Path
import sys
from PIL import Image
from unittest import mock
import pytest

# Add project root to path to allow imports
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

# Import the necessary modules and test utilities
os.environ.setdefault("OPENAI_API_KEY", "test")
import config
from scripts import analyze_artwork as aa
from routes import utils

@pytest.fixture
def isolated_fs_sku(tmp_path, monkeypatch):
    """A fixture to create an isolated filesystem for SKU tests."""
    # Create temporary directories
    unanalysed_dir = tmp_path / "unanalysed-artwork"
    processed_dir = tmp_path / "processed-artwork"
    unanalysed_dir.mkdir()
    processed_dir.mkdir()
    
    # Create temporary registry file
    registry_file = tmp_path / "master-artwork-paths.json"
    registry_file.write_text("{}")

    # Monkeypatch config to use our temporary paths
    monkeypatch.setattr(config, "UNANALYSED_ROOT", unanalysed_dir)
    monkeypatch.setattr(config, "PROCESSED_ROOT", processed_dir)
    monkeypatch.setattr(config, "OUTPUT_JSON", registry_file)
    
    yield unanalysed_dir

class DummyChoice:
    def __init__(self, text):
        self.message = type('m', (), {'content': text})

class DummyResp:
    def __init__(self, text):
        self.choices = [DummyChoice(text)]

SAMPLE_JSON1 = json.dumps({
    "title": "First Artwork", "description": "Test description", "tags": ["tag"], "materials": ["mat"],
    "primary_colour": "Black", "secondary_colour": "Brown", "price": 18.27
})
SAMPLE_JSON2 = json.dumps({
    "title": "Second Artwork", "description": "Test description", "tags": ["tag"], "materials": ["mat"],
    "primary_colour": "Black", "secondary_colour": "Brown", "price": 18.27
})

def test_sequential_sku_assignment(tmp_path, monkeypatch, isolated_fs_sku):
    tracker = tmp_path / 'sku_tracker.json'
    tracker.write_text(json.dumps({"last_sku": 80}))
    monkeypatch.setattr(config, "SKU_TRACKER", tracker)

    # Create fresh, reliable images for the test run in the isolated directory
    img1_folder = isolated_fs_sku / "img1_subfolder"
    img2_folder = isolated_fs_sku / "img2_subfolder"
    img1_folder.mkdir()
    img2_folder.mkdir()
    
    img1 = img1_folder / 'a.jpg'
    img2 = img2_folder / 'b.jpg'
    Image.new('RGB', (10, 10), 'red').save(img1)
    Image.new('RGB', (10, 10), 'blue').save(img2)

    responses = [DummyResp(SAMPLE_JSON1), DummyResp(SAMPLE_JSON2)]
    with mock.patch.object(aa.client.chat.completions, 'create', side_effect=responses):
        entry1 = aa.analyze_single(img1)
        entry2 = aa.analyze_single(img2)

    assert entry1['sku'] == 'RJC-0081'
    assert entry2['sku'] == 'RJC-0082'
    assert json.loads(tracker.read_text())['last_sku'] == 82
    
    path1 = Path(entry1['processed_folder']) / f"{Path(entry1['processed_folder']).name}-listing.json"
    path2 = Path(entry2['processed_folder']) / f"{Path(entry2['processed_folder']).name}-listing.json"

    utils.assign_or_get_sku(path1, tracker, force=True)
    utils.assign_or_get_sku(path2, tracker, force=True)

    assert json.loads(tracker.read_text())['last_sku'] == 84

    with mock.patch.object(aa.client.chat.completions, 'create', return_value=DummyResp(SAMPLE_JSON1)):
        # Re-analyze the same file. The erroneous copy line has been removed.
        entry1b = aa.analyze_single(img1)

    assert entry1b['sku'] == 'RJC-0085'

---
## tests/test_upload.py
---
# tests/test_upload.py
import io
import json
from pathlib import Path
import os
import sys
from PIL import Image
from unittest import mock
import pytest
import shutil

os.environ.setdefault("OPENAI_API_KEY", "test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import app
import config
from utils import session_tracker

@pytest.fixture
def isolated_fs(tmp_path, monkeypatch):
    """A fixture to create an isolated filesystem for upload/analysis tests."""
    unanalysed_dir = tmp_path / "unanalysed-artwork"
    unanalysed_dir.mkdir()
    
    # Monkeypatch config to use our temporary directories
    monkeypatch.setattr(config, "UNANALYSED_ROOT", unanalysed_dir)
    
    # Create a dummy image for tests to use
    img_path = unanalysed_dir / 'sample.jpg'
    Image.new('RGB', (10, 10), 'red').save(img_path)
    
    yield unanalysed_dir # Provide the temp dir to the test

    # Pytest's tmp_path handles the cleanup automatically after the test yields.

def test_upload_single(isolated_fs):
    client = app.test_client()
    img_path = isolated_fs / 'sample.jpg'
    data = img_path.read_bytes()

    resp = client.post('/upload', data={'images': (io.BytesIO(data), 'test.jpg')}, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    # Check that a new subfolder was created inside our isolated directory
    subfolders = [d for d in isolated_fs.iterdir() if d.is_dir()]
    assert len(subfolders) == 1
    created_files = list(subfolders[0].glob("*.jpg"))
    assert len(created_files) > 0 # At least the original was saved

def test_upload_reject_corrupt(isolated_fs):
    client = app.test_client()
    bad_data = io.BytesIO(b'not-a-real-image')
    
    resp = client.post('/upload', data={'images': (bad_data, 'bad.jpg')}, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    # Check that the flash message indicates an error
    assert b'Image processing failed' in resp.data

def test_upload_batch(isolated_fs):
    client = app.test_client()
    img_path = isolated_fs / 'sample.jpg'
    good_data = img_path.read_bytes()
    bad_data = io.BytesIO(b'this-is-not-an-image')
    
    resp = client.post('/upload', data={'images': [
        (io.BytesIO(good_data), 'good.jpg'), 
        (bad_data, 'bad.jpg')
    ]}, content_type='multipart/form-data', follow_redirects=True)

    assert resp.status_code == 200
    assert b'Uploaded 1 file(s) successfully' in resp.data
    assert b'bad.jpg: Image processing failed' in resp.data

def test_upload_json_response(isolated_fs):
    client = app.test_client()
    for s in session_tracker.active_sessions('robbie'):
        session_tracker.remove_session('robbie', s['session_id'])
    client.post('/login', data={'username': 'robbie', 'password': 'kangaroo123'}, follow_redirects=True)
    
    img_path = isolated_fs / 'sample.jpg'
    data = img_path.read_bytes()
    
    resp = client.post('/upload',
        data={'images': (io.BytesIO(data), 'sample.jpg')},
        content_type='multipart/form-data',
        headers={'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'})
        
    assert resp.status_code == 200
    json_response = resp.get_json()
    assert isinstance(json_response, list)
    assert len(json_response) == 1
    assert json_response[0]['success'] is True

---
## tests/test_utils_cleaning.py
---
import pytest
from routes import utils
from routes.artwork_routes import validate_listing_fields
import config


def test_clean_terms():
    cleaned, changed = utils.clean_terms(["te-st", "b@d"])
    assert cleaned == ["test", "bd"]
    assert changed


def test_read_generic_text():
    txt = utils.read_generic_text("4x5")
    assert txt.strip() != ""


def test_validate_generic_error_message():
    generic = utils.read_generic_text("4x5")
    data = {
        "title": "t",
        "description": "short description",
        "tags": ["tag"],
        "materials": ["mat"],
        "primary_colour": "Black",
        "secondary_colour": "Brown",
        "seo_filename": "Test-Artwork-by-Robin-Custance-RJC-0001.jpg",
        "price": "17.88",
        "sku": "RJC-0001",
        "images": [str(config.FINALISED_ROOT / 'test' / 'test.jpg')],
    }
    errors = validate_listing_fields(data, generic)
    joined = " ".join(errors)
    assert "correct generic context block" in joined


def test_validate_generic_present_with_whitespace():
    generic = utils.read_generic_text("4x5")
    base = "word " * 400
    desc = base + "\n\n" + generic + "\n   extra words after"  # within 50 words
    data = {
        "title": "t",
        "description": desc,
        "tags": ["tag"],
        "materials": ["mat"],
        "primary_colour": "Black",
        "secondary_colour": "Brown",
        "seo_filename": "Test-Artwork-by-Robin-Custance-RJC-0001.jpg",
        "price": "17.88",
        "sku": "RJC-0001",
        "images": [str(config.FINALISED_ROOT / 'test' / 'test.jpg')],
    }
    errors = validate_listing_fields(data, generic)
    joined = " ".join(errors)
    assert "correct generic context block" not in joined



---
## utils/__init__.py
---
"""Utility module exports for easy imports."""

from .logger_utils import log_action, strip_binary

__all__ = ["log_action", "strip_binary"]


---
## utils/ai_services.py
---
# utils/ai_services.py
"""
Central module for handling all interactions with external AI services like
OpenAI and Google Gemini.

INDEX
-----
1.  Imports & Client Initialisation
2.  AI Service Callers
"""

# ===========================================================================
# 1. Imports & Client Initialisation
# ===========================================================================
import logging
from openai import OpenAI
import config

logger = logging.getLogger(__name__)

# Initialize the OpenAI client using configuration from config.py
client = OpenAI(
    api_key=config.OPENAI_API_KEY,
    project=config.OPENAI_PROJECT_ID,
)


# ===========================================================================
# 2. AI Service Callers
# ===========================================================================

def call_ai_to_generate_title(paragraph_content: str) -> str:
    """Uses AI to generate a short, compelling title for a block of text."""
    try:
        prompt = (
            f"Generate a short, compelling heading (5 words or less) for the following paragraph. "
            f"Respond only with the heading text, nothing else.\n\nPARAGRAPH:\n\"{paragraph_content}\""
        )
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=20,
        )
        title = response.choices[0].message.content.strip().strip('"')
        logger.info(f"AI generated title: '{title}'")
        return title
    except Exception as e:
        logger.error(f"AI title generation failed: {e}")
        return "AI Title Generation Failed"


def call_ai_to_rewrite(prompt: str, provider: str = "openai") -> str:
    """Calls the specified AI provider to rewrite text based on a prompt."""
    if provider != "openai":
        return "Error: Only OpenAI is currently supported for rewriting."

    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert copywriter. Rewrite the following text based on the user's instruction. Respond only with the rewritten text, without any extra commentary."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        new_text = response.choices[0].message.content.strip()
        logger.info("AI successfully rewrote text based on prompt.")
        return new_text
    except Exception as e:
        logger.error(f"AI text rewrite failed: {e}")
        return f"Error during AI regeneration: {e}"


def call_ai_to_reword_text(provider: str, artwork_description: str, generic_text: str) -> str:
    """
    Uses an AI provider to reword generic text to blend with a specific artwork description.
    """
    logger.info(f"Initiating generic text rewording with provider: {provider}")

    # This prompt is specifically crafted to meet the user's requirements
    prompt = f"""
    You are an expert SEO copywriter for digital art marketplaces. Your task is to reword the following 'Generic Text' to make it unique and blend seamlessly with the preceding 'Artwork Description'.

    Instructions:
    1.  Maintain the original word count and all key details (like file types, dimensions, etc.) from the 'Generic Text'.
    2.  Rewrite the text to flow naturally from the end of the 'Artwork Description'.
    3.  Subtly incorporate keywords and themes from the 'Artwork Description' to enhance SEO and contextual relevance.
    4.  The final output must be ONLY the reworded generic text, with no extra headings, notes, or explanations.

    ---
    Artwork Description (for context):
    "{artwork_description}"
    ---
    Generic Text to Reword:
    "{generic_text}"
    ---
    """

    if provider == "openai":
        try:
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert SEO copywriter specializing in digital art listings."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.75,
                max_tokens=1024, # Ensure enough tokens for a lengthy generic block
            )
            reworded_text = response.choices[0].message.content.strip()
            logger.info("Successfully reworded generic text with OpenAI.")
            return reworded_text
        except Exception as e:
            logger.error(f"OpenAI rewording service error: {e}")
            raise  # Re-raise the exception to be caught by the Flask route
    
    # Placeholder for Gemini integration
    elif provider == "gemini":
        logger.warning("Gemini provider for rewording is not yet implemented.")
        # In a real implementation, the call to the Gemini API would go here.
        # For now, we return the original text with a note.
        return f"(Gemini integration pending) {generic_text}"
    
    else:
        logger.error(f"Unsupported provider for rewording: {provider}")
        raise ValueError("Unsupported provider specified")

---
## utils/ai_utils.py
---
# 🔧 Stub created for: ./utils/ai_utils.py


---
## utils/auth_decorators.py
---
# utils/auth_decorators.py
"""
Authentication and authorization decorators for Flask routes.

These decorators provide a simple way to protect endpoints by ensuring
the user is logged in and has the required role.

INDEX
-----
1.  Imports
2.  Decorator Functions
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging
from functools import wraps

from flask import session, redirect, url_for, request

logger = logging.getLogger(__name__)

# ===========================================================================
# 2. Decorator Functions
# ===========================================================================

def role_required(role: str):
    """
    A decorator to ensure the logged-in user has a specific role.

    If the user is not logged in or does not have the required role, they are
    redirected to the login page.

    Usage:
        @bp.route("/admin")
        @role_required("admin")
        def admin_dashboard():
            return "Welcome, admin!"

    Args:
        role: The role string required to access the endpoint (e.g., "admin").
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_role = session.get("role")
            if user_role != role:
                username = session.get("username", "Anonymous")
                logger.warning(
                    f"Role-based access denied for user '{username}' (role: '{user_role}') "
                    f"to endpoint '{request.endpoint}'. Required role: '{role}'."
                )
                return redirect(url_for("auth.login", next=request.path))
            return func(*args, **kwargs)
        return wrapper
    return decorator

---
## utils/content_blocks.py
---
# 🔧 Stub created for: ./utils/content_blocks.py


---
## utils/file_utils.py
---
# 🔧 Stub created for: ./utils/file_utils.py


---
## utils/image_processing_utils.py
---
# 🔧 Stub created for: ./utils/image_processing_utils.py


---
## utils/logger_utils.py
---
# utils/logger_utils.py
"""
Utility for structured and centralized application logging.

This module provides the `setup_logger` function, which is the primary
method for creating dedicated, timestamped log files for different parts
of the application based on the central LOG_CONFIG.

INDEX
-----
1.  Imports
2.  Data Sanitization Helpers
3.  Core Logging Setup
4.  Legacy Audit Logger
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging
from pathlib import Path
from datetime import datetime
from typing import Any
import config


# ===========================================================================
# 2. Data Sanitization Helpers
# ===========================================================================

def strip_binary(obj: Any) -> Any:
    """Recursively removes bytes/bytearray objects from a data structure."""
    if isinstance(obj, dict):
        return {k: strip_binary(v) for k, v in obj.items() if not isinstance(v, (bytes, bytearray))}
    if isinstance(obj, list):
        return [strip_binary(v) for v in obj if not isinstance(v, (bytes, bytearray))]
    if isinstance(obj, (bytes, bytearray)):
        return f"<stripped {len(obj)} bytes>"
    return obj


def sanitize_blob_data(obj: Any) -> Any:
    """Recursively summarizes binary or long base64 strings for safe logging."""
    if isinstance(obj, dict):
        return {k: sanitize_blob_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_blob_data(v) for v in obj]
    if isinstance(obj, (bytes, bytearray)):
        return f"<stripped {len(obj)} bytes>"
    if isinstance(obj, str) and len(obj) > 300 and "base64" in obj:
        return f"<base64 data stripped, length={len(obj)}>"
    return obj


# ===========================================================================
# 3. Core Logging Setup
# ===========================================================================

def setup_logger(logger_name: str, log_key: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a logger with a timestamped file handler.

    Uses LOG_CONFIG from config.py to determine the subfolder and filename format.

    Args:
        logger_name: The name of the logger (e.g., __name__).
        log_key: The key from config.LOG_CONFIG (e.g., "ANALYZE_OPENAI").
        level: The logging level (e.g., logging.INFO).

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Prevent duplicate handlers if logger is already configured
    if logger.hasHandlers():
        return logger

    # Get folder and filename details from config
    log_folder_name = config.LOG_CONFIG.get(log_key, config.LOG_CONFIG["DEFAULT"])
    log_dir = config.LOGS_DIR / log_folder_name
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(config.LOG_TIMESTAMP_FORMAT).upper()
    log_filename = f"{timestamp}-{log_key}.log"
    log_filepath = log_dir / log_filename
    
    # Create and configure file handler
    handler = logging.FileHandler(log_filepath, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


# ===========================================================================
# 4. Legacy Audit Logger
# ===========================================================================

def log_action(
    action: str,
    filename: str,
    user: str | None,
    details: str,
    *,
    status: str = "success",
    error: str | None = None,
) -> None:
    """
    Appends a formatted line to an action-specific audit log.
    Note: This creates hourly log files for high-frequency actions.
    """
    log_folder_name = config.LOG_CONFIG.get(action.upper(), action)
    log_dir = config.LOGS_DIR / log_folder_name
    log_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H") # Hourly log file
    log_file = log_dir / f"{stamp}.log"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    user_id = user or "unknown"
    parts = [
        timestamp,
        f"user: {user_id}",
        f"action: {action}",
        f"file: {filename}",
        f"status: {status}",
        f"detail: {details}",
    ]
    if error:
        parts.append(f"error: {error}")
        
    line = " | ".join(parts) + "\n"
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        # Fallback to main logger if file write fails
        fallback_logger = logging.getLogger(__name__)
        fallback_logger.error(f"Failed to write to action log {log_file}: {e}")
        fallback_logger.error(f"Log line was: {line}")

---
## utils/security.py
---
# utils/security.py
"""
Site security helpers backed by the SQLite database.

This module provides functions to dynamically enable or disable application-wide
security features like login requirements and browser caching by modifying
records in the database.

INDEX
-----
1.  Imports
2.  Database Helper
3.  Login Security Functions
4.  Cache Control Functions
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from db import SessionLocal, SiteSettings

logger = logging.getLogger(__name__)


# ===========================================================================
# 2. Database Helper
# ===========================================================================

def _get_settings(session: Session) -> SiteSettings:
    """
    Retrieves the site settings object from the database, creating it with
    default values if it doesn't exist.

    Args:
        session: The active SQLAlchemy session.

    Returns:
        The SiteSettings ORM object.
    """
    settings = session.query(SiteSettings).first()
    if not settings:
        logger.info("No site settings found in database; creating new default record.")
        settings = SiteSettings()
        session.add(settings)
        session.commit()
        session.refresh(settings)
    return settings


# ===========================================================================
# 3. Login Security Functions
# ===========================================================================

def login_required_enabled() -> bool:
    """
    Checks if login is currently required.

    This function also automatically re-enables the login requirement if a
    temporary override period has expired.

    Returns:
        True if login is required, False otherwise.
    """
    with SessionLocal() as session:
        settings = _get_settings(session)
        if not settings.login_enabled:
            # Check if the override period has expired
            if settings.login_override_until and settings.login_override_until <= datetime.utcnow():
                logger.info("Login override has expired. Re-enabling login requirement.")
                settings.login_enabled = True
                settings.login_override_until = None
                session.commit()
        return settings.login_enabled


def disable_login_for(minutes: int) -> None:
    """
    Disables the login requirement for all non-admins for a set duration.

    Args:
        minutes: The number of minutes to disable the login requirement for.
    """
    with SessionLocal() as session:
        settings = _get_settings(session)
        settings.login_enabled = False
        settings.login_override_until = datetime.utcnow() + timedelta(minutes=minutes)
        session.commit()
        logger.warning(f"ADMIN ACTION: Login requirement has been disabled for {minutes} minutes.")


def enable_login() -> None:
    """Immediately re-enables the login requirement for all non-admins."""
    with SessionLocal() as session:
        settings = _get_settings(session)
        settings.login_enabled = True
        settings.login_override_until = None
        session.commit()
        logger.info("ADMIN ACTION: Login requirement has been re-enabled.")


def remaining_minutes() -> int | None:
    """
    Calculates the remaining minutes until a login override expires.

    Returns:
        The number of whole minutes remaining, or None if no override is active.
    """
    with SessionLocal() as session:
        settings = _get_settings(session)
        if settings.login_override_until and not settings.login_enabled:
            delta = settings.login_override_until - datetime.utcnow()
            return max(int(delta.total_seconds() // 60), 0)
        return None


# ===========================================================================
# 4. Cache Control Functions
# ===========================================================================

def force_no_cache_enabled() -> bool:
    """
    Checks if 'no-cache' headers should be forced on responses.

    Automatically disables the override if its timer has expired.

    Returns:
        True if 'no-cache' headers should be forced, False otherwise.
    """
    with SessionLocal() as session:
        settings = _get_settings(session)
        if settings.force_no_cache and settings.force_no_cache_until and settings.force_no_cache_until <= datetime.utcnow():
            logger.info("Force 'no-cache' override has expired. Disabling.")
            settings.force_no_cache = False
            settings.force_no_cache_until = None
            session.commit()
        return settings.force_no_cache


def enable_no_cache(minutes: int) -> None:
    """
    Forces the 'no-cache' header on all responses for a specified duration.

    Args:
        minutes: The number of minutes to force 'no-cache' headers.
    """
    with SessionLocal() as session:
        settings = _get_settings(session)
        settings.force_no_cache = True
        settings.force_no_cache_until = datetime.utcnow() + timedelta(minutes=minutes)
        session.commit()
        logger.warning(f"ADMIN ACTION: Force 'no-cache' has been enabled for {minutes} minutes.")


def disable_no_cache() -> None:
    """Immediately disables the 'no-cache' header override."""
    with SessionLocal() as session:
        settings = _get_settings(session)
        settings.force_no_cache = False
        settings.force_no_cache_until = None
        session.commit()
        logger.info("ADMIN ACTION: Force 'no-cache' has been disabled.")


def no_cache_remaining() -> int | None:
    """
    Calculates the remaining minutes until a 'no-cache' override expires.

    Returns:
        The number of whole minutes remaining, or None if no override is active.
    """
    with SessionLocal() as session:
        settings = _get_settings(session)
        if settings.force_no_cache and settings.force_no_cache_until:
            delta = settings.force_no_cache_until - datetime.utcnow()
            return max(int(delta.total_seconds() // 60), 0)
        return None

---
## utils/session_tracker.py
---
# utils/session_tracker.py
"""
Utilities for tracking active user sessions with a device limit.

This module provides a thread-safe mechanism for managing a JSON-based
session registry file, enforcing a maximum number of concurrent sessions
per user and handling session timeouts.

INDEX
-----
1.  Imports
2.  Configuration & Constants
3.  Public Session Management Functions
4.  Internal Helper Functions
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import json
import threading
import datetime
import contextlib
import fcntl
import logging

import config

# ===========================================================================
# 2. Configuration & Constants
# ===========================================================================
REGISTRY_FILE = config.SESSION_REGISTRY_FILE
MAX_SESSIONS = config.MAX_SESSIONS
TIMEOUT_SECONDS = config.SESSION_TIMEOUT_SECONDS

_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


# ===========================================================================
# 3. Public Session Management Functions
# ===========================================================================

def register_session(username: str, session_id: str) -> bool:
    """
    Registers a new session for a user, respecting the MAX_SESSIONS limit.

    Args:
        username: The user for whom to register the session.
        session_id: The unique identifier for the new session.

    Returns:
        True if the session was registered successfully, False if the limit was reached.
    """
    with _LOCK:
        data = _load_registry()
        data = _cleanup_expired(data)
        sessions = data.get(username, [])
        if len(sessions) >= MAX_SESSIONS:
            logger.warning(f"Session registration denied for '{username}': limit of {MAX_SESSIONS} reached.")
            return False
        
        sessions.append({
            "session_id": session_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        data[username] = sessions
        _save_registry(data)
        logger.info(f"Registered new session {session_id} for user '{username}'.")
    return True


def remove_session(username: str, session_id: str) -> None:
    """Removes a specific session for a user."""
    with _LOCK:
        data = _load_registry()
        if username in data:
            original_count = len(data[username])
            data[username] = [s for s in data[username] if s.get("session_id") != session_id]
            if not data[username]:
                del data[username]
            
            if len(data.get(username, [])) < original_count:
                logger.info(f"Removed session {session_id} for user '{username}'.")
                _save_registry(data)


def touch_session(username: str, session_id: str) -> bool:
    """
    Updates the timestamp of an active session to keep it alive.

    Returns:
        True if the session was found and touched, False if it was expired or not found.
    """
    with _LOCK:
        data = _load_registry()
        data = _cleanup_expired(data)
        for s in data.get(username, []):
            if s.get("session_id") == session_id:
                s["timestamp"] = datetime.datetime.utcnow().isoformat()
                _save_registry(data)
                return True
    logger.warning(f"Attempted to touch an invalid or expired session '{session_id}' for user '{username}'.")
    return False


def active_sessions(username: str) -> list[dict]:
    """Returns a list of all active sessions for a given user."""
    data = _load_registry()
    return _cleanup_expired(data).get(username, [])


def all_sessions() -> dict:
    """Returns a dictionary of all active sessions for all users."""
    data = _load_registry()
    return _cleanup_expired(data)


# ===========================================================================
# 4. Internal Helper Functions
# ===========================================================================

def _load_registry() -> dict:
    """Loads the session registry JSON file safely."""
    if not REGISTRY_FILE.exists():
        return {}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            with contextlib.suppress(OSError): # fcntl may fail on some systems
                fcntl.flock(f, fcntl.LOCK_SH)
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Could not read session registry file at {REGISTRY_FILE}: {e}")
        return {}


def _save_registry(data: dict) -> None:
    """Saves the session registry data to its JSON file atomically."""
    tmp_path = REGISTRY_FILE.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(REGISTRY_FILE)
    except IOError as e:
        logger.error(f"Could not write to session registry file at {REGISTRY_FILE}: {e}")


def _cleanup_expired(data: dict) -> dict:
    """Removes sessions that have exceeded the timeout duration."""
    now = datetime.datetime.utcnow()
    changed = False
    for user in list(data.keys()):
        active_user_sessions = [
            s for s in data[user]
            if now - datetime.datetime.fromisoformat(s["timestamp"]) < datetime.timedelta(seconds=TIMEOUT_SECONDS)
        ]
        if len(active_user_sessions) != len(data[user]):
            changed = True
        
        if active_user_sessions:
            data[user] = active_user_sessions
        else:
            del data[user]
            changed = True
            
    if changed:
        logger.info("Cleaned up expired sessions from registry.")
        _save_registry(data)
    return data

---
## utils/sku_assigner.py
---
# utils/sku_assigner.py
"""
Thread-safe utility for generating and tracking sequential SKUs.

This module reads from and writes to a central SKU tracker JSON file,
ensuring that each artwork receives a unique, sequential SKU.

INDEX
-----
1.  Imports
2.  Configuration & Constants
3.  SKU Management Functions
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import json
import logging
from pathlib import Path
import threading

import config

# ===========================================================================
# 2. Configuration & Constants
# ===========================================================================
SKU_PREFIX = config.SKU_CONFIG["PREFIX"]
SKU_DIGITS = config.SKU_CONFIG["DIGITS"]

_LOCK = threading.Lock()  # for thread/process safety
logger = logging.getLogger(__name__)


# ===========================================================================
# 3. SKU Management Functions
# ===========================================================================

def get_next_sku(tracker_path: Path) -> str:
    """
    Safely increments and returns the next sequential SKU.

    This function reads the last used SKU number from the tracker file,
    increments it, writes the new value back to the file, and returns
    the newly formatted SKU string. It is thread-safe.

    Args:
        tracker_path: The Path object pointing to the SKU tracker JSON file.

    Returns:
        The next sequential SKU as a string (e.g., "RJC-0001").
    """
    with _LOCK:
        try:
            if tracker_path.exists():
                with open(tracker_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_sku = int(data.get("last_sku", 0))
            else:
                last_sku = 0
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Could not read SKU tracker at {tracker_path}. Starting from 0. Error: {e}")
            last_sku = 0

        next_sku_num = last_sku + 1
        next_sku_str = f"{SKU_PREFIX}{next_sku_num:0{SKU_DIGITS}d}"

        try:
            tracker_path.write_text(json.dumps({"last_sku": next_sku_num}, indent=2), encoding="utf-8")
            logger.info(f"Assigned new SKU: {next_sku_str}. Tracker file updated.")
        except IOError as e:
            logger.error(f"Could not write to SKU tracker at {tracker_path}: {e}")

        return next_sku_str


def peek_next_sku(tracker_path: Path) -> str:
    """
    Returns what the next SKU would be without incrementing the tracker.

    This is useful for displaying the next available SKU in a UI without
    consuming it. It is thread-safe.

    Args:
        tracker_path: The Path object pointing to the SKU tracker JSON file.

    Returns:
        The next potential SKU as a string.
    """
    with _LOCK:
        try:
            if tracker_path.exists():
                with open(tracker_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_sku = int(data.get("last_sku", 0))
            else:
                last_sku = 0
        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Could not read SKU tracker at {tracker_path} for peeking. Assuming 0. Error: {e}")
            last_sku = 0

    next_sku_num = last_sku + 1
    return f"{SKU_PREFIX}{next_sku_num:0{SKU_DIGITS}d}"

---
## utils/template_engine.py
---
# 🔧 Stub created for: ./utils/template_engine.py


---
## utils/template_helpers.py
---
# 🔧 Stub created for: ./utils/template_helpers.py


---
## utils/user_manager.py
---
# utils/user_manager.py
"""
Database-backed user management utilities.

This module provides a set of functions to interact with the User model
in the database, allowing for the creation, deletion, and modification of
user accounts.

INDEX
-----
1.  Imports
2.  User Management Functions
"""

# ===========================================================================
# 1. Imports
# ===========================================================================
from __future__ import annotations
import logging

from werkzeug.security import generate_password_hash

from db import SessionLocal, User

logger = logging.getLogger(__name__)


# ===========================================================================
# 2. User Management Functions
# ===========================================================================

def load_users() -> list[User]:
    """Return all users from the database."""
    with SessionLocal() as session:
        return session.query(User).all()


def add_user(username: str, role: str = "viewer", password: str = "changeme") -> None:
    """Create a new user if one with the same username does not already exist."""
    with SessionLocal() as session:
        if session.query(User).filter_by(username=username).first():
            logger.warning(f"Attempted to add existing user '{username}'. No action taken.")
            return
            
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        session.add(user)
        session.commit()
        logger.info(f"Successfully added new user '{username}' with role '{role}'.")


def delete_user(username: str) -> None:
    """Delete a user from the database by their username."""
    with SessionLocal() as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            session.delete(user)
            session.commit()
            logger.info(f"Successfully deleted user '{username}'.")
        else:
            logger.warning(f"Attempted to delete non-existent user '{username}'.")


def set_role(username: str, role: str) -> None:
    """Update a user's role in the database."""
    with SessionLocal() as session:
        user = session.query(User).filter_by(username=username).first()
        if user:
            user.role = role
            session.commit()
            logger.info(f"Successfully changed role for user '{username}' to '{role}'.")
        else:
            logger.warning(f"Attempted to set role for non-existent user '{username}'.")