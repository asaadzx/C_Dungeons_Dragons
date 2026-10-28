from datetime import date

from app.extensions import db
from app.models import Lecture, LectureItem, Project


def test_assignments_show_newest_date_and_tabs(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Lecture(date=date(2026, 10, 1), title="Old lecture"),
                Lecture(date=date(2026, 10, 29), title="New lecture"),
            ]
        )
        db.session.commit()

    page = client.get("/assignments").data.decode()
    assert "New lecture" in page
    assert "Old lecture" not in page
    assert "01 Oct 2026" in page
    assert "29 Oct 2026" in page
    assert 'href="/assignments?date=2026-10-01"' in page


def test_assignments_date_query_selects_day(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Lecture(date=date(2026, 10, 1), title="Old lecture"),
                Lecture(date=date(2026, 10, 29), title="New lecture"),
            ]
        )
        db.session.commit()

    page = client.get("/assignments?date=2026-10-01").data.decode()
    assert "Old lecture" in page
    assert "New lecture" not in page


def test_assignments_render_ordered_items_and_safe_links(client, app):
    with app.app_context():
        lecture = Lecture(date=date(2026, 10, 29), title="Databases")
        lecture.items = [
            LectureItem(text="Second", position=2),
            LectureItem(
                text="First",
                url="https://example.com/notes",
                position=1,
            ),
        ]
        db.session.add(lecture)
        db.session.commit()

    page = client.get("/assignments").data.decode()
    assert page.index("First") < page.index("Second")
    assert 'href="https://example.com/notes"' in page
    assert 'target="_blank"' in page


def test_assignments_do_not_render_unsafe_links(client, app):
    with app.app_context():
        lecture = Lecture(date=date(2026, 10, 29), title="Safety")
        lecture.items = [LectureItem(text="Bad link", url="javascript:alert(1)")]
        db.session.add(lecture)
        db.session.commit()

    page = client.get("/assignments").data.decode()
    assert "Bad link" in page
    assert "javascript:" not in page


def test_projects_render_cards_and_safe_links(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Project(
                    title="Robot",
                    description="Build a robot",
                    url="https://example.com/robot",
                    position=1,
                ),
                Project(title="Game", description="Make a game", position=2),
            ]
        )
        db.session.commit()

    page = client.get("/projects").data.decode()
    assert "Robot" in page
    assert "Build a robot" in page
    assert 'href="https://example.com/robot"' in page
    assert "Make a game" in page


def test_projects_do_not_render_unsafe_links(client, app):
    with app.app_context():
        db.session.add(Project(title="Bad", url="javascript:alert(1)"))
        db.session.commit()

    page = client.get("/projects").data.decode()
    assert "Bad" in page
    assert "javascript:" not in page
