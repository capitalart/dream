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
