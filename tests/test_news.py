from app.extensions import db
from app.models import Announcement


def test_news_page_shows_class_news(client, app, monkeypatch):
    # Do not hit real RSS feeds during tests.
    monkeypatch.setattr("app.news.routes.get_global_news", lambda force=False: [])

    with app.app_context():
        db.session.add(
            Announcement(
                title="Field Trip",
                content="We visit the science museum on Sunday.",
                category="Class News",
            )
        )
        db.session.add(
            Announcement(title="Other", content="Not class news", category="News")
        )
        db.session.commit()

    page = client.get("/news").data.decode()
    assert "Class News" in page
    assert "Field Trip" in page
    assert "Not class news" not in page


def test_news_page_renders_global_stories(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.news.routes.get_global_news",
        lambda force=False: [
            {
                "title": "Cool Science Discovery",
                "link": "https://example.com/story",
                "summary": "A short summary.",
                "published": "",
                "source": "ScienceDaily",
            }
        ],
    )

    page = client.get("/news").data.decode()
    assert "Global News" in page
    assert "Cool Science Discovery" in page
    assert "ScienceDaily" in page


def test_news_page_survives_empty_feeds(client, app, monkeypatch):
    monkeypatch.setattr("app.news.routes.get_global_news", lambda force=False: [])
    response = client.get("/news")
    assert response.status_code == 200
