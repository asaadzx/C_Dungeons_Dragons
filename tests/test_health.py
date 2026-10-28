from sqlalchemy.exc import OperationalError

from app.extensions import db


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
