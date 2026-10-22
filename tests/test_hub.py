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
