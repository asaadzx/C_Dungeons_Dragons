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


def test_contact_phone_is_staff_only_and_email_is_public(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Student

        db.session.add(
            Student(
                name_en="Contact Student",
                name_ar="طالب",
                phone="01001234567",
                email="student@example.com",
            )
        )
        db.session.commit()

    directory = client.get("/directory").data.decode()
    profile = client.get("/student/1").data.decode()

    assert "student@example.com" in directory
    assert "student@example.com" in profile
    assert "01001234567" not in directory
    assert "01001234567" not in profile

    _login_as_staff(client, app)

    staff_profile = client.get("/student/1").data.decode()
    assert "student@example.com" in staff_profile
    assert "01001234567" in staff_profile


def test_anonymous_profile_with_only_phone_shows_empty_contact_state(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Student

        db.session.add(Student(name_en="Phone Only", name_ar="", phone="0100"))
        db.session.commit()

    profile = client.get("/student/1").data.decode()
    assert "0100" not in profile
    assert "No contact details added yet." in profile


def test_anonymous_schedule_hides_event_form(client):
    page = client.get("/schedule").data.decode()
    assert "Post an event" not in page
    assert "Staff login is required to post an event." in page


def test_staff_schedule_shows_event_form(client, app):
    _login_as_staff(client, app)
    page = client.get("/schedule").data.decode()
    assert "Post an event" in page


def test_create_event_rejects_unsafe_link(client, app):
    _login_as_staff(client, app)
    with app.app_context():
        from app.extensions import db
        from app.models import Event, Student

        student = Student(name_en="Organizer", name_ar="منظم")
        db.session.add(student)
        db.session.commit()
        student_id = student.id

    response = client.post(
        "/schedule/add",
        data={
            "organizer_id": str(student_id),
            "title": "Unsafe Event",
            "link": "javascript:alert(1)",
        },
        follow_redirects=True,
    )

    assert "Event link must be a full http:// or https:// URL." in response.data.decode()
    with app.app_context():
        assert Event.query.count() == 0


def test_edit_event_rejects_unsafe_link(client, app):
    _login_as_staff(client, app)
    with app.app_context():
        from app.extensions import db
        from app.models import Event, Student

        student = Student(name_en="Organizer", name_ar="منظم")
        db.session.add(student)
        db.session.commit()
        event = Event(
            organizer_id=student.id,
            title="Safe Event",
            link="https://example.com/event",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.post(
        f"/admin/event/{event_id}/edit",
        data={"title": "Changed", "link": "javascript:alert(1)"},
        follow_redirects=True,
    )

    assert "Event link must be a full http:// or https:// URL." in response.data.decode()
    with app.app_context():
        from app.extensions import db
        from app.models import Event

        event = db.session.get(Event, event_id)
        assert event.link == "https://example.com/event"
        assert event.title == "Safe Event"


def test_existing_unsafe_event_link_is_not_rendered(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Event, Student

        student = Student(name_en="Organizer", name_ar="منظم")
        db.session.add(student)
        db.session.commit()
        db.session.add(
            Event(
                organizer_id=student.id,
                title="Legacy Unsafe",
                link="javascript:alert(1)",
            )
        )
        db.session.commit()

    page = client.get("/schedule").data.decode()
    assert "javascript:alert(1)" not in page


def _login_as_staff(client, app):
    import re

    from app.extensions import db
    from app.models import User

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
