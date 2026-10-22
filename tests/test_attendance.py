from datetime import date

from app.extensions import db
from app.models import AttendanceRecord, AttendanceSession, Student, User


def _seed(app):
    with app.app_context():
        user = User(username="teacher", role="teacher")
        user.set_password("correct")
        student = Student(name_en="Student One", name_ar="طالب")
        db.session.add_all([user, student])
        db.session.commit()
        return user.id, student.id


def test_save_attendance_creates_one_session_and_records(client, app):
    user_id, student_id = _seed(app)
    with app.app_context():
        from app.attendance.services import save_attendance

        saved = save_attendance(date(2026, 10, 22), {student_id}, {}, user_id)
        assert saved.id is not None
        assert AttendanceSession.query.count() == 1
        assert AttendanceRecord.query.count() == 1

        save_attendance(date(2026, 10, 22), set(), {}, user_id)
        assert AttendanceSession.query.count() == 1
        assert AttendanceRecord.query.one().status == "absent"


def test_attendance_requires_login(client):
    response = client.get("/attendance")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_daily_csv_contains_header(client, app):
    user_id, student_id = _seed(app)
    with app.app_context():
        from app.attendance.services import daily_csv, save_attendance

        save_attendance(date(2026, 10, 22), {student_id}, {}, user_id)
        content = daily_csv(date(2026, 10, 22))
        assert content.splitlines()[0] == "date,student_id,name_en,name_ar,status,note"
        assert "Student One" in content
