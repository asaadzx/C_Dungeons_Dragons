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
    assert page.index("29 Oct 2026") < page.index("01 Oct 2026")
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


def test_assignments_unknown_date_falls_back_to_newest(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Lecture(date=date(2026, 10, 1), title="Old lecture"),
                Lecture(date=date(2026, 10, 29), title="New lecture"),
            ]
        )
        db.session.commit()

    page = client.get("/assignments?date=1999-01-01").data.decode()
    assert "New lecture" in page
    assert "Old lecture" not in page


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
                    position=2,
                ),
                Project(title="Game", description="Make a game", position=1),
            ]
        )
        db.session.commit()

    page = client.get("/projects").data.decode()
    assert "Robot" in page
    assert "Build a robot" in page
    assert 'href="https://example.com/robot"' in page
    assert "Make a game" in page
    assert page.index("Game") < page.index("Robot")


def test_projects_do_not_render_unsafe_links(client, app):
    with app.app_context():
        db.session.add(Project(title="Bad", url="javascript:alert(1)"))
        db.session.commit()

    page = client.get("/projects").data.decode()
    assert "Bad" in page
    assert "javascript:" not in page


import re

from app.models import User


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


def test_assignment_admin_requires_login(client):
    assert client.get("/admin/assignments").status_code == 302
    assert client.get("/admin/projects").status_code == 302


def test_assignment_admin_crud(client, app):
    token = _login(client, app)
    client.post(
        "/admin/assignments/lecture",
        data={
            "csrf_token": token,
            "date": "2026-10-29",
            "title": "Databases",
            "position": "1",
        },
    )
    with app.app_context():
        lecture = Lecture.query.one()
        lecture_id = lecture.id
        assert lecture.title == "Databases"

    client.post(
        "/admin/assignments/item",
        data={
            "csrf_token": token,
            "lecture_id": str(lecture_id),
            "text": "Read chapter 1",
            "url": "https://example.com/ch1",
            "position": "0",
        },
    )
    with app.app_context():
        item = LectureItem.query.one()
        item_id = item.id
        assert item.url == "https://example.com/ch1"

    client.post(
        f"/admin/assignments/item/{item_id}/edit",
        data={"csrf_token": token, "text": "Read chapter 2", "url": "", "position": "2"},
    )
    client.post(
        f"/admin/assignments/lecture/{lecture_id}/edit",
        data={
            "csrf_token": token,
            "date": "2026-10-30",
            "title": "Databases II",
            "position": "0",
        },
    )
    with app.app_context():
        lecture = db.session.get(Lecture, lecture_id)
        item = db.session.get(LectureItem, item_id)
        assert lecture.title == "Databases II"
        assert lecture.date == date(2026, 10, 30)
        assert item.text == "Read chapter 2"
        assert item.url == ""
        assert item.position == 2

    client.post(
        f"/admin/assignments/item/{item_id}/delete", data={"csrf_token": token}
    )
    client.post(
        f"/admin/assignments/lecture/{lecture_id}/delete", data={"csrf_token": token}
    )
    with app.app_context():
        assert Lecture.query.count() == 0
        assert LectureItem.query.count() == 0


def test_assignment_item_edit_keeps_url_when_link_is_unsafe(client, app):
    token = _login(client, app)
    with app.app_context():
        lecture = Lecture(date=date(2026, 10, 29), title="Databases")
        item = LectureItem(text="Reading", url="https://example.com/safe")
        lecture.items = [item]
        db.session.add(lecture)
        db.session.commit()
        item_id = item.id

    client.post(
        f"/admin/assignments/item/{item_id}/edit",
        data={
            "csrf_token": token,
            "text": "Reading",
            "url": "javascript:alert(1)",
            "position": "0",
        },
    )
    with app.app_context():
        assert db.session.get(LectureItem, item_id).url == "https://example.com/safe"


def test_assignment_item_rejects_huge_lecture_id(client, app):
    token = _login(client, app)
    response = client.post(
        "/admin/assignments/item",
        data={
            "csrf_token": token,
            "lecture_id": "9" * 5000,
            "text": "Bad",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        assert LectureItem.query.count() == 0


def test_project_admin_crud(client, app):
    token = _login(client, app)
    client.post(
        "/admin/project",
        data={
            "csrf_token": token,
            "title": "Robot",
            "description": "Build a robot",
            "url": "https://example.com/robot",
            "position": "1",
        },
    )
    with app.app_context():
        project = Project.query.one()
        project_id = project.id

    client.post(
        f"/admin/project/{project_id}/edit",
        data={
            "csrf_token": token,
            "title": "Robot 2",
            "description": "Build a better robot",
            "url": "",
            "position": "0",
        },
    )
    with app.app_context():
        project = db.session.get(Project, project_id)
        assert project.title == "Robot 2"
        assert project.description == "Build a better robot"
        assert project.url == ""

    client.post(f"/admin/project/{project_id}/delete", data={"csrf_token": token})
    with app.app_context():
        assert Project.query.count() == 0


def test_admin_rejects_invalid_date_and_links(client, app):
    token = _login(client, app)
    client.post(
        "/admin/assignments/lecture",
        data={"csrf_token": token, "date": "not-a-date", "title": "Bad"},
    )
    client.post(
        "/admin/project",
        data={"csrf_token": token, "title": "Bad", "url": "javascript:alert(1)"},
    )
    with app.app_context():
        assert Lecture.query.count() == 0
        assert Project.query.count() == 0
        lecture = Lecture(date=date(2026, 10, 29), title="Valid")
        db.session.add(lecture)
        db.session.commit()
        lecture_id = lecture.id

    client.post(
        "/admin/assignments/item",
        data={
            "csrf_token": token,
            "lecture_id": str(lecture_id),
            "text": "Bad",
            "url": "javascript:alert(1)",
        },
    )
    with app.app_context():
        assert LectureItem.query.count() == 0
