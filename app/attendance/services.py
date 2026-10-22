import csv
import io

from ..extensions import db
from ..models import AttendanceRecord, AttendanceSession, Student


def active_students():
    return Student.query.filter_by(active=True).order_by(Student.name_en).all()


def get_session(day):
    return AttendanceSession.query.filter_by(date=day).first()


def save_attendance(day, present_ids, notes, user_id):
    session = get_session(day)
    if session is None:
        session = AttendanceSession(date=day, created_by=user_id)
        db.session.add(session)
        db.session.flush()
    else:
        session.created_by = user_id

    for record in list(session.records):
        db.session.delete(record)
    db.session.flush()

    for student in active_students():
        db.session.add(
            AttendanceRecord(
                session_id=session.id,
                student_id=student.id,
                status="present" if student.id in present_ids else "absent",
                note=(notes.get(student.id) or "").strip()[:500],
            )
        )
    db.session.commit()
    return session


def daily_csv(day):
    session = get_session(day)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "student_id", "name_en", "name_ar", "status", "note"])
    if session is None:
        return output.getvalue()

    records = sorted(session.records, key=lambda r: r.student.name_en)
    for record in records:
        writer.writerow(
            [
                session.date.isoformat(),
                record.student_id,
                record.student.name_en,
                record.student.name_ar,
                record.status,
                record.note,
            ]
        )
    return output.getvalue()
