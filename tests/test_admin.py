import re

from app.extensions import db
from app.models import Announcement, LhrGame, Meme, TedTalk, User


def _login(client, app):
    with app.app_context():
        user = User(username="staff", role="admin")
        user.set_password("pw")
        db.session.add(user)
        db.session.commit()
    page = client.get("/auth/login").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    client.post(
        "/auth/login",
        data={"username": "staff", "password": "pw", "csrf_token": token},
    )
    return token


def test_admin_requires_login(client):
    assert client.get("/admin").status_code == 302


def test_add_youtube_video_fills_thumbnail(client, app):
    token = _login(client, app)
    client.post(
        "/admin/ted",
        data={
            "csrf_token": token,
            "title": "Games",
            "url": "https://www.youtube.com/watch?v=ZL6QfJU5VeQ&t=170s",
            "description": "Ideas",
        },
    )
    with app.app_context():
        video = TedTalk.query.one()
        assert video.thumbnail == "https://img.youtube.com/vi/ZL6QfJU5VeQ/hqdefault.jpg"


def test_add_youtube_short_url(client, app):
    token = _login(client, app)
    client.post(
        "/admin/ted",
        data={"csrf_token": token, "title": "Short", "url": "https://youtu.be/ZL6QfJU5VeQ"},
    )
    with app.app_context():
        assert "ZL6QfJU5VeQ" in TedTalk.query.one().thumbnail


def test_delete_each_content_type(client, app):
    token = _login(client, app)
    with app.app_context():
        announcement = Announcement(title="A", content="B")
        game = LhrGame(title="G", rules="R")
        meme = Meme(image_url="images/x.png", caption="c")
        video = TedTalk(
            title="V", url="https://youtu.be/ZL6QfJU5VeQ", thumbnail="t", description=""
        )
        db.session.add_all([announcement, game, meme, video])
        db.session.commit()
        ids = {
            "announcement": announcement.id,
            "lhr": game.id,
            "meme": meme.id,
            "ted": video.id,
        }

    for kind, item_id in ids.items():
        client.post(f"/admin/{kind}/{item_id}/delete", data={"csrf_token": token})

    with app.app_context():
        assert Announcement.query.count() == 0
        assert LhrGame.query.count() == 0
        assert Meme.query.count() == 0
        assert TedTalk.query.count() == 0


def test_home_shows_external_thumbnail(client, app):
    token = _login(client, app)
    client.post(
        "/admin/ted",
        data={"csrf_token": token, "title": "V", "url": "https://youtu.be/ZL6QfJU5VeQ"},
    )
    page = client.get("/").data.decode()
    assert "VIDEO FOR KNOWLEDGE" in page
    assert "img.youtube.com/vi/ZL6QfJU5VeQ" in page


def test_news_source_add_edit_delete(client, app):
    token = _login(client, app)

    # Add a source from the staff panel.
    client.post(
        "/admin/news-source",
        data={"csrf_token": token, "label": "Example", "url": "https://example.com/rss"},
    )
    with app.app_context():
        from app.models import NewsSource

        source = NewsSource.query.filter_by(label="Example").one()
        source_id = source.id

    # Edit the label and temporarily disable it.
    client.post(
        f"/admin/news-source/{source_id}/edit",
        data={"csrf_token": token, "label": "Example 2", "url": "https://example.com/rss"},
    )
    with app.app_context():
        from app.models import NewsSource

        source = db.session.get(NewsSource, source_id)
        assert source.label == "Example 2"
        assert source.active is False

    # Delete it.
    client.post(f"/admin/news-source/{source_id}/delete", data={"csrf_token": token})
    with app.app_context():
        from app.models import NewsSource

        assert db.session.get(NewsSource, source_id) is None
