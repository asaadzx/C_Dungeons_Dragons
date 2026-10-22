from datetime import date, timedelta

from app.extensions import db
from app.models import Student, User


def _seed(app):
    with app.app_context():
        user = User(username="t", role="teacher")
        user.set_password("x")
        student = Student(name_en="A", name_ar="ا")
        db.session.add_all([user, student])
        db.session.commit()
        return user.id, student.id


def test_saved_week_aggregates(app):
    user_id, student_id = _seed(app)
    with app.app_context():
        from app.attendance.dbweekly import aggregate_saved_week
        from app.attendance.services import save_attendance

        start = date(2026, 10, 18)  # a Sunday
        for offset in range(5):
            statuses = {student_id: "absent" if offset == 0 else "present"}
            save_attendance(start + timedelta(days=offset), statuses, {}, user_id)

        result = aggregate_saved_week(start)
        assert result["students"][0]["present"] == 4
        assert result["students"][0]["absent"] == 1
        assert result["missing_days"] == []


def test_saved_week_reports_missing_days(app):
    user_id, student_id = _seed(app)
    with app.app_context():
        from app.attendance.dbweekly import aggregate_saved_week
        from app.attendance.services import save_attendance

        start = date(2026, 10, 18)
        save_attendance(start, {student_id: "present"}, {}, user_id)

        result = aggregate_saved_week(start)
        assert len(result["missing_days"]) == 4
        assert result["students"][0]["present"] == 1


def test_saved_week_counts_late_as_present(app):
    user_id, student_id = _seed(app)
    with app.app_context():
        from app.attendance.dbweekly import aggregate_saved_week
        from app.attendance.services import save_attendance

        start = date(2026, 10, 18)
        for offset in range(5):
            save_attendance(
                start + timedelta(days=offset), {student_id: "late"}, {}, user_id
            )

        result = aggregate_saved_week(start)
        student = result["students"][0]
        assert student["present"] == 5
        assert student["late"] == 5
        assert student["percentage"] == 100.0


def test_most_recent_sunday():
    from app.attendance.dbweekly import most_recent_sunday

    # 2026-10-22 is a Thursday, so the most recent Sunday is 2026-10-18.
    assert most_recent_sunday(date(2026, 10, 22)) == date(2026, 10, 18)
    # A Sunday maps to itself.
    assert most_recent_sunday(date(2026, 10, 18)) == date(2026, 10, 18)
