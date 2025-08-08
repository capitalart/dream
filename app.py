"""Flask application for DreamArtMachine with database-backed authentication."""

from __future__ import annotations

import os

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    url_for,
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


from db import init_db
from routes.auth_routes import bp as auth_bp
from utils.security import is_authenticated
from utils.user_manager import ensure_default_users


def create_app() -> Flask:
    """Application factory with security settings and login enforcement."""
    configure_logging()
    init_db()
    ensure_default_users()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=True,
        PREFERRED_URL_SCHEME="https",
    )

    @app.before_request
    def require_login() -> None:
        """Redirect users to login page if not authenticated."""
        exempt = {"auth.login", "static"}
        if request.endpoint in exempt or request.path == "/favicon.ico":
            return
        if not is_authenticated():
            return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("500.html"), 500

    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(artwork_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(finalise_bp)
    app.register_blueprint(exports_bp)
    app.register_blueprint(analyze_bp)
    return app


app = create_app()
