# Attendance Exports, LATE Status and Weekly-from-DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `late` status, server-side Excel/PNG exports, weekly-from-DB reporting, and finish deploy docs.

**Architecture:** Extend the existing attendance service so status is a three-value mapping, add export modules (openpyxl, Pillow), and add a DB-backed weekly route that reuses the same aggregation logic as the CSV upload path.

**Tech Stack:** Flask, SQLAlchemy, openpyxl, Pillow, pytest.

## Global Constraints

- Status values are exactly `present`, `absent`, `late`.
- `late` counts as present for the weekly percentage but is tracked separately.
- Staff-only routes use `@login_required`.
- All POST forms use CSRF (existing WTF setup).
- Keep the CSV export and upload flows working and unchanged in format.
- Do not commit unless the user explicitly asks.

---

### Task 1: LATE status in the service and daily checklist

**Files:**
- Modify: `app/attendance/services.py`
- Modify: `app/attendance/routes.py`
- Modify: `app/templates/attendance/daily.html`
- Modify: `tests/test_attendance.py`

**Interfaces:**
- Produces: `save_attendance(day, statuses: dict[int, str], notes, user_id)`
- Produces: `ALLOWED_STATUSES = {"present", "absent", "late"}`

- [ ] **Step 1: Update the service to take a status mapping**

```python
ALLOWED_STATUSES = {"present", "absent", "late"}


def save_attendance(day, statuses, notes, user_id):
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
        status = statuses.get(student.id, "present")
        if status not in ALLOWED_STATUSES:
            status = "present"
        db.session.add(
            AttendanceRecord(
                session_id=session.id,
                student_id=student.id,
                status=status,
                note=(notes.get(student.id) or "").strip()[:500],
            )
        )
    db.session.commit()
    return session
```

- [ ] **Step 2: Update the daily route to read a status per student**

In `daily()`, replace the present-id set with a status dict built from a
`status_<id>` form field (`present`/`late`/`absent`, default `present`).

- [ ] **Step 3: Update the template**

Replace the checkbox with a three-option control per student, e.g. a small
select named `status_<id>` with Present/Late/Absent. Keep "Check all" setting
everything to Present and add a "Mark all present" reset.

- [ ] **Step 4: Update tests**

```python
def test_late_status_is_saved(client, app):
    user_id, student_id = _seed(app)
    with app.app_context():
        from app.attendance.services import save_attendance

        save_attendance(date(2026, 10, 22), {student_id: "late"}, {}, user_id)
        assert AttendanceRecord.query.one().status == "late"
```

Call `save_attendance(day, {student_id: "present"}, {}, user_id)` in the other
tests.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_attendance.py -v`
Expected: PASS.

---

### Task 2: Excel export

**Files:**
- Modify: `requirements.txt` (add openpyxl)
- Create: `app/attendance/exports.py`
- Modify: `app/attendance/routes.py`
- Test: `tests/test_exports.py` (new)

**Interfaces:**
- Produces: `day_records(day) -> dict[str, list[AttendanceRecord]]` grouped by status
- Produces: `build_excel(day) -> bytes`
- Produces: `GET /attendance/export.xlsx?date=YYYY-MM-DD`

- [ ] **Step 1: Write the failing Excel test**

```python
def test_excel_has_sections(app):
    with app.app_context():
        from datetime import date

        from app.attendance.exports import build_excel
        from app.attendance.services import save_attendance
        from app.extensions import db
        from app.models import Student, User

        user = User(username="t", role="teacher")
        user.set_password("x")
        s1 = Student(name_en="Present P", name_ar="ح")
        s2 = Student(name_en="Late L", name_ar="خ")
        s3 = Student(name_en="Absent A", name_ar="ط")
        db.session.add_all([user, s1, s2, s3])
        db.session.commit()
        save_attendance(
            date(2026, 10, 22),
            {s1.id: "present", s2.id: "late", s3.id: "absent"},
            {},
            user.id,
        )

        data = build_excel(date(2026, 10, 22))
        import io

        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(data))
        text = " ".join(
            str(c.value) for row in wb.active.iter_rows() for c in row if c.value
        )
        assert "ATTENDED" in text
        assert "LATE" in text
        assert "ABSENT" in text
```

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_exports.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement the export helpers**

Create `app/attendance/exports.py` with:
- `day_records(day)`: returns `{"present": [...], "late": [...], "absent": [...]}` using the session records, sorted by `student.name_en`.
- `build_excel(day)`: builds the workbook with a title, then the three
  sections. Absent rows get a yellow fill and bold font; late rows get an
  amber fill and bold font. Use the palette RGBs.
- `build_png(day)`: renders a poster with Pillow (background `#BE1A1A`,
  title text `#F8EBAB`, absent/late names in big bold). Use
  `ImageFont.load_default()` if no bundled font, never raising.

- [ ] **Step 4: Add the route**

```python
@bp.get("/attendance/export.xlsx")
@login_required
def export_xlsx():
    day = _parse_day(request.args.get("date", date.today().isoformat()))
    return Response(
        build_excel(day),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={day.isoformat()}-c1-attendance.xlsx"},
    )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_exports.py -v`
Expected: PASS.

---

### Task 3: PNG export

**Files:**
- Modify: `app/attendance/routes.py`
- Modify: `app/templates/attendance/daily.html`
- Test: `tests/test_exports.py`

- [ ] **Step 1: Write the failing PNG test**

```python
def test_png_returns_image(app):
    with app.app_context():
        from datetime import date

        from app.attendance.exports import build_png

        data = build_png(date(2026, 10, 22))
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(data) > 100
```

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_exports.py::test_png_returns_image -v`
Expected: FAIL.

- [ ] **Step 3: Add the route and buttons**

Add `GET /attendance/export.png` returning `build_png(day)` with
`mimetype="image/png"`. Add "Export Excel" and "Export Image" buttons to the
daily template next to the CSV button, linked to the new routes with the day's
date.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_exports.py -v`
Expected: PASS.

---

### Task 4: Weekly from DB

**Files:**
- Create: `app/attendance/dbweekly.py`
- Modify: `app/attendance/routes.py`
- Create: `app/templates/attendance/week_saved.html`
- Test: `tests/test_dbweekly.py` (new)

**Interfaces:**
- Produces: `aggregate_saved_week(start: date) -> dict` in the same shape as
  `aggregate_weekly`
- Produces: `GET /attendance/week/saved?start=YYYY-MM-DD`

- [ ] **Step 1: Write the failing test**

```python
def test_saved_week_aggregates(app):
    with app.app_context():
        from datetime import date, timedelta

        from app.attendance.dbweekly import aggregate_saved_week
        from app.attendance.services import save_attendance
        from app.extensions import db
        from app.models import Student, User

        user = User(username="t", role="teacher")
        user.set_password("x")
        student = Student(name_en="A", name_ar="ا")
        db.session.add_all([user, student])
        db.session.commit()

        start = date(2026, 10, 18)  # a Sunday
        for offset in range(5):
            statuses = {student.id: "absent" if offset == 0 else "present"}
            save_attendance(start + timedelta(days=offset), statuses, {}, user.id)

        result = aggregate_saved_week(start)
        assert result["students"][0]["present"] == 4
        assert result["students"][0]["absent"] == 1
        assert result["missing_days"] == []
```

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_dbweekly.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement aggregation over saved sessions**

`aggregate_saved_week(start)` reads the five days from `start`. For each day it
looks up the session; missing days go into `missing_days`. It builds the same
per-student structure as `aggregate_weekly` (present, late, absent,
percentage with late counted present, absent_dates).

- [ ] **Step 4: Add the route and template**

`GET /attendance/week/saved?start=YYYY-MM-DD` (default: most recent Sunday)
renders `attendance/week_saved.html` with the summary, missing-day warnings, and
the existing weekly CSV download link. Add a link from the weekly page.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_dbweekly.py -v`
Expected: PASS.

---

### Task 5: Documentation and full verification

**Files:**
- Modify: `README.md` (ignored by git, local only)
- Modify: `render.yaml` if needed

- [ ] **Step 1: Update usage docs**

Document the new routes, the LATE rule, and the Excel/PNG/CSV exports in the
README deploy checklist and usage section.

- [ ] **Step 2: Run everything**

Run: `pytest -v`
Expected: all tests PASS.

Run: `npm run lint:js`
Expected: no errors.

- [ ] **Step 3: Final route map check**

Run: `python -c "from app import create_app; app=create_app(); print(sorted(r.rule for r in app.url_map.iter_rules()))"`
Expected: includes `/attendance/export.xlsx`, `/attendance/export.png`, `/attendance/week/saved`.

---

## Self-Review

**Spec coverage:** Late status (Task 1), Excel (Task 2), PNG (Task 3), weekly-from-DB (Task 4), deployment docs (Task 5).

**Placeholder scan:** No TBDs. Export module responsibilities and route signatures are explicit.

**Type consistency:** `save_attendance(day, statuses, notes, user_id)`, `day_records(day)`, `build_excel(day)`, `build_png(day)`, `aggregate_saved_week(start)` are used consistently.
