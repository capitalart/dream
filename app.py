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
