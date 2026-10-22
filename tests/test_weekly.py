import io
from datetime import date

import pytest

from app.attendance.weekly import aggregate_weekly, parse_daily_csv


class FakeUpload:
    def __init__(self, content, filename="day.csv"):
        self._content = content.encode("utf-8")
        self.filename = filename

    def read(self):
        return self._content


class FakeStudent:
    def __init__(self, student_id, name_en="Student", name_ar=""):
        self.id = student_id
        self.name_en = name_en
        self.name_ar = name_ar


def _csv(day, statuses):
    lines = ["date,student_id,name_en,name_ar,status,note"]
    for student_id, status in statuses.items():
        lines.append(f"{day},{student_id},Student,طالب,{status},")
    return "\n".join(lines)


def test_parse_daily_csv():
    day, rows = parse_daily_csv(FakeUpload(_csv("2026-10-19", {1: "present", 2: "absent"})))
    assert day == date(2026, 10, 19)
    assert len(rows) == 2


def test_aggregate_weekly_counts_days():
    students = [FakeStudent(1), FakeStudent(2)]
    days = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
    files = []
    for index, day in enumerate(days):
        statuses = {1: "present", 2: "absent" if index == 0 else "present"}
        files.append(FakeUpload(_csv(day, statuses), filename=f"{day}.csv"))

    result = aggregate_weekly(files, students)
    first = result["students"][0]
    assert first["present"] == 5
    assert first["absent"] == 0
    second = result["students"][1]
    assert second["present"] == 4
    assert second["absent"] == 1
    assert second["absent_dates"] == ["2026-10-19"]


def test_aggregate_rejects_duplicate_dates():
    students = [FakeStudent(1)]
    content = _csv("2026-10-19", {1: "present"})
    files = [FakeUpload(content) for _ in range(5)]
    with pytest.raises(ValueError, match="duplicate date"):
        aggregate_weekly(files, students)


def test_aggregate_rejects_unknown_students():
    students = [FakeStudent(1)]
    files = [
        FakeUpload(_csv(day, {1: "present", 99: "present"}))
        for day in ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
    ]
    with pytest.raises(ValueError, match="unknown student_id"):
        aggregate_weekly(files, students)


def test_aggregate_rejects_bad_status():
    students = [FakeStudent(1)]
    with pytest.raises(ValueError, match="bad status"):
        parse_daily_csv(FakeUpload(_csv("2026-10-19", {1: "maybe"})))


def test_aggregate_requires_five_files():
    with pytest.raises(ValueError, match="exactly 5"):
        aggregate_weekly([], [FakeStudent(1)])
