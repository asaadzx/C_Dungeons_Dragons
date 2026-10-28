# ---------------------------------------------------------------------------
# app/__init__.py
# Application factory: builds and configures the Flask app.
#
# Everything the app needs is wired up here: config, extensions, blueprints,
# CLI commands, error pages and security headers. Using a factory (instead of
# a module-level app) makes the app easy to create with different settings in
# tests and in production.
# ---------------------------------------------------------------------------

import os

from flask import Flask, jsonify, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config
from .extensions import csrf, db, login_manager, migrate
from .security import add_security_headers, media_url, safe_url


def create_app(config_object=Config):
    """Create, configure and return a ready-to-run Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Safety net: never boot production with the placeholder secret key.
    if os.environ.get("FLASK_ENV") == "production":
        if app.config["SECRET_KEY"] == "dev-only-change-me":
            raise RuntimeError("SECRET_KEY must be set in production")

    # Bind the shared extensions to this app instance.
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Where Flask-Login sends anonymous users who hit a protected page.
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "error"

    # Blueprints group related routes: auth (login), hub (public pages),
    # attendance (checklist + weekly) and admin (staff management).
    from .admin import bp as admin_bp
    from .attendance import bp as attendance_bp
    from .auth import bp as auth_bp
    from .cli import register_cli
    from .hub import bp as hub_bp
    from .i18n import register_i18n
    from .news import bp as news_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(hub_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(news_bp)
    register_cli(app)

    # Language switching + t()/dir helpers for every template.
    register_i18n(app)

    # Importing models registers every table with SQLAlchemy.
    from . import models  # noqa: F401

    # Jinja helper: {{ some_url|safe_url }} returns "" for unsafe schemes.
    app.jinja_env.filters["safe_url"] = safe_url
    # Jinja helper: {{ image|media_url }} handles both external and static paths.
    app.jinja_env.filters["media_url"] = media_url
    app.after_request(add_security_headers)

    # Lightweight health check used by Railway and uptime monitors.
    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Health check database failure")
            return jsonify(status="error", database="error"), 503
        return jsonify(status="ok", database="ok")

    # Error pages are rendered with render_template so Flask-Login injects
    # current_user (the base template reads it for the nav bar).
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        # Roll back any half-finished database work before showing the page.
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(SQLAlchemyError)
    def database_unavailable(error):
        # Roll back any half-finished database work before showing the page.
        db.session.rollback()
        app.logger.exception("Database unavailable")
        return render_template("errors/503.html"), 503

    return app


@login_manager.user_loader
def load_user(user_id):
    """Turn the id stored in the session cookie back into a User object."""
    from .models import User

    return db.session.get(User, int(user_id))
