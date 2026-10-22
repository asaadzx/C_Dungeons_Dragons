# ---------------------------------------------------------------------------
# app/config.py
# All application settings in one place.
#
# Values come from environment variables so the same code runs locally
# (SQLite file) and in production (Neon PostgreSQL) without changes.
# ---------------------------------------------------------------------------

import os
from pathlib import Path

# Absolute path of the project root (one level above this app/ package).
BASE_DIR = Path(__file__).resolve().parent.parent


def _database_url():
    """Return the SQLAlchemy database URL.

    Falls back to a local SQLite file when DATABASE_URL is not set, which is
    what happens during development and tests.

    Some hosts (Render, Heroku) hand out old-style "postgres://" URLs.
    SQLAlchemy 2 needs the driver to be explicit, so we rewrite the scheme to
    "postgresql+psycopg://" for psycopg 3.
    """
    url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}")
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    """Production and development settings (driven by env vars)."""

    # Signs session cookies and CSRF tokens. MUST be replaced in production.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    SQLALCHEMY_DATABASE_URI = _database_url()
    # We do not use Flask-SQLAlchemy's event system, so turn the warning off.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Reject uploads larger than 2 MB (the weekly CSV files are tiny).
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    # Cookie hardening. SECURE is only on in production because HTTPS is
    # required for it, and local development runs over plain HTTP.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"

    # CSRF tokens live for the whole browser session (None = no expiry).
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    """Settings used only by pytest: in-memory DB and CSRF turned off."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
