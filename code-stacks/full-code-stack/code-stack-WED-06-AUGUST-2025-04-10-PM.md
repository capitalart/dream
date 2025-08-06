# FULL CODE STACK (WED-06-AUGUST-2025-04-10-PM)


---
## app.py
---
"""Flask application for DreamArtMachine with basic authentication."""
from __future__ import annotations

import os

from flask import (
    Flask,
    redirect,
    render_template_string,
    request,
    url_for,
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


login_manager = LoginManager()
login_manager.login_view = "login"


class User(UserMixin):
    """Minimal user model for authentication."""

    def __init__(self, username: str):
        self.id = username
        self.username = username


USERS = {
    "robbie": {"password": "Kanga123!"},
    "backup": {"password": "DreamArt@2025"}
}


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
        return render_template_string(
            "<form method='post'><input name='username'><input name='password'"
            " type='password'><button type='submit'>Login</button></form>"
        )

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/artworks")
    @login_required
    def artworks():
        return {"artworks": []}, 200

    @app.route("/healthz")
    @login_required
    def health_check() -> tuple[str, int]:
        return "OK", 200

    @app.route("/whoami")
    @login_required
    def whoami() -> tuple[str, int]:
        return f"Logged in as: {current_user.username}", 200

    app.register_blueprint(home_bp)
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
Flask-Login==0.6.3


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
## routes/home_routes.py
---
"""Homepage routes for DreamArtMachine."""
from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import login_required

bp = Blueprint("home", __name__)


@bp.route("/")
@login_required
def root() -> "Response":
    """Redirect the base URL to /home."""
    return redirect(url_for("home.home"))


@bp.route("/home")
@login_required
def home() -> str:
    """Render the application homepage."""
    return render_template("home.html")


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
## static/css/global.css
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
## templates/base.html
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
    <link rel="stylesheet" href="{{ url_for('static', filename='css/global.css') }}">
</head>
<body>
    <header class="site-header">
        <div class="header-left">
            <a href="{{ url_for('home.home') }}" class="site-logo">
                <img src="{{ url_for('static', filename='icons/svg/light/palette-light.svg') }}" alt="" class="logo-icon icon">DreamArtMachine
            </a>
        </div>
        <div class="header-right">
            <button id="theme-toggle" class="theme-toggle-btn" aria-label="Toggle theme">
                <svg id="icon-sun" class="sun-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.106a.75.75 0 011.06-1.06l1.591 1.59a.75.75 0 01-1.06 1.06l-1.59-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.894 17.894a.75.75 0 01-1.06 1.06l-1.59-1.591a.75.75 0 111.06-1.06l1.59 1.59zM12 18.75a.75.75 0 01-.75.75v2.25a.75.75 0 011.5 0V19.5a.75.75 0 01-.75-.75zM6.106 18.894a.75.75 0 01-1.06-1.06l1.59-1.59a.75.75 0 011.06 1.06l-1.59 1.59zM3.75 12a.75.75 0 01.75-.75h2.25a.75.75 0 010 1.5H4.5a.75.75 0 01-.75-.75zM6.106 5.046a.75.75 0 011.06 1.06l-1.59 1.591a.75.75 0 01-1.06-1.06l1.59-1.59z"/></svg>
                <svg id="icon-moon" class="moon-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69a.75.75 0 001.981.981A10.503 10.503 0 0118 18a10.5 10.5 0 01-10.5-10.5c0-1.25.22-2.454.622-3.574a.75.75 0 01.806-.162z" clip-rule="evenodd"/></svg>
            </button>
        </div>
    </header>
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
    <footer class="site-footer">
        <p>© 2025 DreamArtMachine</p>
    </footer>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>


---
## templates/home.html
---
{% extends "base.html" %}
{% block title %}Home | DreamArtMachine{% endblock %}
{% block content %}
<div class="home-hero">
  <h1><img src="{{ url_for('static', filename='logos/logo-vector.svg') }}" alt="" class="artnarrator-logo"/>Welcome to DreamArtMachine</h1>
  <p class="home-intro">Create, analyse and prepare your art for sale with integrated AI tools.</p>
</div>

<div class="workflow-row">
  <a href="#" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-one-light.svg') }}" class="step-btn-icon" alt="Step 1" />
    Upload Artwork
  </a>
  <a href="#" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-two-light.svg') }}" class="step-btn-icon" alt="Step 2" />
    Analyze
  </a>
  <a href="#" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-three-light.svg') }}" class="step-btn-icon" alt="Step 3" />
    Finalise
  </a>
  <a href="#" class="workflow-btn">
    <img src="{{ url_for('static', filename='icons/svg/light/number-circle-four-light.svg') }}" class="step-btn-icon" alt="Step 4" />
    Export
  </a>
</div>

<section class="how-it-works">
  <h2>How It Works</h2>
  <ol>
    <li><b>Upload:</b> Drag and drop your artwork.</li>
    <li><b>Analyze:</b> Let the AI generate titles and descriptions.</li>
    <li><b>Finalise:</b> Review and tweak the details.</li>
    <li><b>Export:</b> Prepare files for marketplace listing.</li>
  </ol>
</section>
{% endblock %}


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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import validate


def test_restore_integrity(tmp_path):
    root = tmp_path
    (root / ".env").write_text("TEST=1")
    unanalysed = root / "art-processing" / "unanalysed-artwork"
    unanalysed.mkdir(parents=True)
    (unanalysed / "img-RJC-1.jpg").write_text("x")
    (unanalysed / "img-RJC-1-THUMB.jpg").write_text("x")
    (unanalysed / "img-RJC-1-ANALYSE.jpg").write_text("x")
    (unanalysed / "img-RJC-1.json").write_text("{}")

    processed = root / "art-processing" / "processed-artwork" / "slug"
    thumbs = processed / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "RJC-1"
    (processed / f"slug-{sku}.jpg").write_text("x")
    (processed / f"slug-{sku}-THUMB.jpg").write_text("x")
    (processed / f"slug-{sku}-ANALYSE.jpg").write_text("x")
    (processed / f"slug-{sku}.json").write_text("{}")
    (processed / f"final-slug-{sku}.json").write_text("{}")
    for i in range(1, 10):
        (processed / f"slug-{sku}-MU-{i:02}.jpg").write_text("x")
        (thumbs / f"slug-{sku}-MU-{i:02}-THUMB.jpg").write_text("x")

    errors = validate(root)
    assert errors == []


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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_sku_integrity import check_unanalysed, check_processed


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


def test_processed_missing_final_json(tmp_path):
    base = tmp_path / "processed-artwork" / "slug"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "RJC-1234"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{slug}-{sku}.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert any("Final JSON" in e for e in errors)


def test_processed_complete(tmp_path):
    base = tmp_path / "processed-artwork" / "slug2"
    thumbs = base / "THUMBS"
    thumbs.mkdir(parents=True)
    sku = "RJC-5678"
    slug = base.name
    (base / f"{slug}-{sku}.jpg").write_text("data")
    (base / f"{slug}-{sku}-THUMB.jpg").write_text("data")
    (base / f"{slug}-{sku}-ANALYSE.jpg").write_text("data")
    (base / f"{slug}-{sku}.json").write_text("{}")
    (base / f"final-{slug}-{sku}.json").write_text("{}")
    for i in range(1, 10):
        (base / f"{slug}-{sku}-MU-{i:02}.jpg").write_text("mu")
        (thumbs / f"{slug}-{sku}-MU-{i:02}-THUMB.jpg").write_text("mu")
    errors = check_processed(tmp_path / "processed-artwork")
    assert errors == []
