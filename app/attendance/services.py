import csv
import io

from ..extensions import db
from ..models import AttendanceRecord, AttendanceSession, Student

# The only attendance states the app accepts. "late" counts as attended later.
ALLOWED_STATUSES = {"present", "absent", "late"}


def active_students():
    """Return the active roster, sorted by English name."""
    return Student.query.filter_by(active=True).order_by(Student.name_en).all()


def get_session(day):
    """Return the saved attendance session for a date, or None."""
    return AttendanceSession.query.filter_by(date=day).first()


def save_attendance(day, statuses, notes, user_id):
    """Create or replace the attendance session for one day.

    statuses is a {student_id: "present"|"late"|"absent"} mapping. Any student
    missing from the mapping defaults to present. Re-saving the same date
    updates the existing session instead of creating a duplicate.

    We delete and recreate the records so the saved row set always matches the
    current active roster (students added later are not silently missing).
    """
    session = get_session(day)
    if session is None:
        session = AttendanceSession(date=day, created_by=user_id)
        db.session.add(session)
        db.session.flush()
    else:
        session.created_by = user_id

    # Update the rows we already have instead of deleting and recreating them.
    # Re-saving is common (fixing one absent student), so this keeps writes
    # small and avoids a full delete/insert round trip on every save.
    existing = {record.student_id: record for record in session.records}
    seen = set()

    for student in active_students():
        status = statuses.get(student.id, "present")
        if status not in ALLOWED_STATUSES:
            status = "present"
        note = (notes.get(student.id) or "").strip()[:500]
        record = existing.get(student.id)
        if record is None:
            db.session.add(
                AttendanceRecord(
                    session_id=session.id,
                    student_id=student.id,
                    status=status,
                    note=note,
                )
            )
        else:
            record.status = status
            record.note = note
        seen.add(student.id)

    # Drop rows for students who are no longer active.
    for student_id, record in existing.items():
        if student_id not in seen:
            db.session.delete(record)

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
