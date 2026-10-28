from flask import g
from flask_login import current_user
from sqlalchemy.exc import OperationalError

from app.extensions import db
from app.models import User


def _database_down(*args, **kwargs):
    raise OperationalError("SELECT 1", {}, Exception("database is down"))


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_health_returns_503_when_database_fails(client, monkeypatch):
    monkeypatch.setattr(db.session, "execute", _database_down)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "error"}


def test_database_error_renders_503_page(client, app):
    @app.get("/_database_down")
    def database_down():
        raise OperationalError("SELECT 1", {}, Exception("database is down"))

    response = client.get("/_database_down")

    assert response.status_code == 503
    assert "Database unavailable" in response.data.decode()


def test_database_error_renders_503_page_for_logged_in_user(client, app, monkeypatch):
    @app.get("/_load_logged_in_user")
    def load_logged_in_user():
        return str(current_user.is_authenticated)

    with app.app_context():
        user = User(username="teacher", role="teacher")
        user.set_password("correct")
        db.session.add(user)
        db.session.commit()

    client.post(
        "/auth/login",
        data={"username": "teacher", "password": "correct"},
    )
    # The fixture keeps one app context for the whole test, so drop the user
    # cached on g to force the next request through Flask-Login's user loader.
    g.pop("_login_user", None)

    monkeypatch.setattr(db.session, "get", _database_down)

    response = client.get("/_load_logged_in_user")

    assert response.status_code == 503
    assert "Database unavailable" in response.data.decode()
