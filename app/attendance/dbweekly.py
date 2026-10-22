# ---------------------------------------------------------------------------
# app/attendance/dbweekly.py
# Weekly attendance computed directly from saved daily sessions, so the
# teacher does not have to export and re-upload five CSVs.
#
# The output shape matches app/attendance/weekly.py (aggregate_weekly) so both
# the upload page and this page can share the same summary template.
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from .services import active_students, get_session

# A school week: Sunday through Thursday (five days).
WEEK_LENGTH = 5


def most_recent_sunday(reference=None):
    """Return the most recent Sunday on or before the reference date."""
    reference = reference or date.today()
    # weekday(): Monday=0 ... Sunday=6. Move back to the last Sunday.
    offset = (reference.weekday() + 1) % 7
    return reference - timedelta(days=offset)


def aggregate_saved_week(start):
    """Aggregate the five saved sessions beginning at `start`.

    `start` is normally a Sunday. Days with no saved session are listed in
    `missing_days` instead of raising, so the report still shows what exists.
    `late` counts as present for the percentage, and is tracked separately.
    """
    days = [start + timedelta(days=offset) for offset in range(WEEK_LENGTH)]
    sessions = {day: get_session(day) for day in days}

    missing_days = [day.isoformat() for day, session in sessions.items() if session is None]
    present_days = [day for day, session in sessions.items() if session is not None]

    summary = []
    for student in active_students():
        present = 0
        late = 0
        absent = 0
        absent_dates = []

        for day in present_days:
            session = sessions[day]
            record = next(
                (r for r in session.records if r.student_id == student.id), None
            )
            if record is None or record.status == "absent":
                absent += 1
                absent_dates.append(day.isoformat())
            elif record.status == "late":
                # Late counts as attended, but is shown in its own column.
                present += 1
                late += 1
            else:
                present += 1

        counted = len(present_days)
        percentage = round((present / counted) * 100, 1) if counted else 0.0
        summary.append(
            {
                "student_id": student.id,
                "name_en": student.name_en,
                "name_ar": student.name_ar,
                "present": present,
                "late": late,
                "absent": absent,
                "percentage": percentage,
                "absent_dates": absent_dates,
            }
        )

    return {
        "start": start.isoformat(),
        "dates": [day.isoformat() for day in present_days],
        "missing_days": missing_days,
        "students": summary,
        "total_present": sum(item["present"] for item in summary),
        "total_late": sum(item["late"] for item in summary),
        "total_absent": sum(item["absent"] for item in summary),
    }
