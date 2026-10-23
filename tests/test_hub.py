def test_public_hub_pages(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Announcement, Student

        db.session.add(Announcement(title="Hello", content="World", category="News"))
        db.session.add(Student(name_en="Student One", name_ar="طالب"))
        db.session.commit()

    for path in ["/", "/lhr", "/directory", "/schedule"]:
        response = client.get(path)
        assert response.status_code == 200, path


def test_directory_hides_public_add_form(client):
    response = client.get("/directory")
    assert b"Add yourself" not in response.data


def test_student_profile_shows_names(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Student

        db.session.add(Student(name_en="Student One", name_ar="طالب واحد"))
        db.session.commit()

    response = client.get("/student/1")
    assert response.status_code == 200
    assert "Student One".encode() in response.data
    assert "طالب واحد".encode() in response.data



def test_add_event_form_has_csrf_token(client, app):
    """Posting an event must work from the schedule page (regression)."""
    import re

    with app.app_context():
        from app.extensions import db
        from app.models import Student, User

        student = Student(name_en="Organizer", name_ar="منظم")
        user = User(username="staff", role="admin")
        user.set_password("pw")
        db.session.add_all([student, user])
        db.session.commit()
        student_id = student.id

    login_page = client.get("/auth/login").data.decode()
    login_token = re.search(r'name="csrf_token" value="([^"]+)"', login_page).group(1)
    client.post(
        "/auth/login",
        data={"username": "staff", "password": "pw", "csrf_token": login_token},
    )

    page = client.get("/schedule").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    response = client.post(
        "/schedule/add",
        data={
            "csrf_token": token,
            "organizer_id": str(student_id),
            "title": "Study Night",
            "event_date_actual": "2026-11-21",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        from app.models import Event

        assert Event.query.filter_by(title="Study Night").one_or_none() is not None
