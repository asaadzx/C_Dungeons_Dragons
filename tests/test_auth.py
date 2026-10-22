from app.extensions import db
from app.models import User


def test_login_rejects_bad_password(client, app):
    with app.app_context():
        user = User(username="teacher", role="teacher")
        user.set_password("correct")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"username": "teacher", "password": "wrong"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data


def test_login_accepts_valid_user(client, app):
    with app.app_context():
        user = User(username="teacher", role="teacher")
        user.set_password("correct")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"username": "teacher", "password": "correct"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Log out" in response.data
