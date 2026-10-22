import csv
import io
from datetime import date

REQUIRED_COLUMNS = {"date", "student_id", "name_en", "name_ar", "status", "note"}
ALLOWED_STATUSES = {"present", "absent"}


def parse_daily_csv(file_storage):
    try:
        text = file_storage.read().decode("utf-8-sig")
    except (UnicodeDecodeError, AttributeError) as exc:
        raise ValueError(f"{file_storage.filename}: file must be UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
        raise ValueError(
            f"{file_storage.filename}: expected columns {sorted(REQUIRED_COLUMNS)}"
        )

    rows = list(reader)
    if not rows:
        raise ValueError(f"{file_storage.filename}: file is empty")

    parsed = []
    dates = set()
    seen_students = set()

    for line_number, row in enumerate(rows, start=2):
        try:
            day = date.fromisoformat((row.get("date") or "").strip())
            student_id = int(row.get("student_id") or "")
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{file_storage.filename}: bad date or student_id on line {line_number}"
            ) from exc

        status = (row.get("status") or "").strip().lower()
        if status not in ALLOWED_STATUSES:
            raise ValueError(
                f"{file_storage.filename}: bad status on line {line_number}"
            )
        if student_id in seen_students:
            raise ValueError(
                f"{file_storage.filename}: duplicate student {student_id} on line {line_number}"
            )

        seen_students.add(student_id)
        dates.add(day)
        parsed.append(
            {
                "date": day,
                "student_id": student_id,
                "name_en": (row.get("name_en") or "").strip(),
                "name_ar": (row.get("name_ar") or "").strip(),
                "status": status,
                "note": (row.get("note") or "").strip(),
            }
        )

    if len(dates) != 1:
        raise ValueError(f"{file_storage.filename}: file must contain exactly one date")
    return dates.pop(), parsed


def aggregate_weekly(files, students):
    if len(files) != 5:
        raise ValueError("Upload exactly 5 daily CSV files.")

    by_day = {}
    for file_storage in files:
        day, rows = parse_daily_csv(file_storage)
        if day in by_day:
            raise ValueError(f"duplicate date: {day.isoformat()}")
        by_day[day] = rows

    student_map = {student.id: student for student in students}
    for day, rows in by_day.items():
        for row in rows:
            if row["student_id"] not in student_map:
                raise ValueError(
                    f"unknown student_id {row['student_id']} in {day.isoformat()}"
                )

    summary = []
    for student in students:
        present = 0
        absent = 0
        absent_dates = []
        for day in sorted(by_day):
            row = next(
                (r for r in by_day[day] if r["student_id"] == student.id), None
            )
            if row is None:
                raise ValueError(
                    f"student {student.id} is missing from {day.isoformat()}"
                )
            if row["status"] == "present":
                present += 1
            else:
                absent += 1
                absent_dates.append(day.isoformat())
        summary.append(
            {
                "student_id": student.id,
                "name_en": student.name_en,
                "name_ar": student.name_ar,
                "present": present,
                "absent": absent,
                "percentage": round((present / 5) * 100, 1),
                "absent_dates": absent_dates,
            }
        )

    return {
        "dates": [day.isoformat() for day in sorted(by_day)],
        "students": summary,
        "total_present": sum(item["present"] for item in summary),
        "total_absent": sum(item["absent"] for item in summary),
    }
