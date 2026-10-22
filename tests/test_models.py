from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import AttendanceRecord, AttendanceSession, Student, User


def test_user_password_hash_and_attendance_uniqueness(app):
    with app.app_context():
        user = User(username="teacher", role="teacher")
        user.set_password("secret")
        assert user.check_password("secret")
        assert not user.check_password("wrong")

        student = Student(name_en="Test Student", name_ar="طالب")
        db.session.add_all([user, student])
        db.session.commit()

        session = AttendanceSession(date=date(2026, 10, 22), created_by=user.id)
        db.session.add(session)
        db.session.commit()

        db.session.add(
            AttendanceRecord(
                session_id=session.id, student_id=student.id, status="present"
            )
        )
        db.session.commit()

        db.session.add(
            AttendanceRecord(
                session_id=session.id, student_id=student.id, status="absent"
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
