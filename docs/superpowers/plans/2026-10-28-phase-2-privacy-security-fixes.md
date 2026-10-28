# Phase 2 Privacy, Security, and Small Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide student phone numbers from anonymous visitors, prevent unsafe event links and forms from being exposed, fix saved-week CSV export, add friendly 503 handling, and publish a student-facing README.

**Architecture:** Keep the existing Flask blueprint structure. Add small template conditions and route validations, reuse `safe_url`, extend the existing weekly export route, register a `SQLAlchemyError` handler, and track/update documentation. No model or migration changes.

**Tech Stack:** Python 3.13 in production, Flask, SQLAlchemy, Flask-Login, Flask-WTF, pytest, Jinja, NES.css, Railway/Railpack.

## Global Constraints

- No model changes and no database migrations.
- Email stays public; phone is visible only to logged-in staff.
- Join requests and requester names/messages stay public.
- Event links must be absolute `http` or `https` URLs.
- Keep existing 404 and 500 behavior unchanged.
- Weekly CSV responses must include `Cache-Control: no-store`.
- Do not add JavaScript dependencies.
- `COMMANDS.md` stays local-only and ignored.
- Run tests with `.venv/bin/python -m pytest -q`.
- Run JavaScript lint with `npm run lint:js`.
- All existing tests must keep passing.

---

### Task 1: Staff-only phone numbers

**Files:**
- Modify: `tests/test_hub.py`
- Modify: `app/templates/directory.html`
- Modify: `app/templates/profile.html`

**Interfaces:**
- Consumes: Flask-Login's `current_user` in Jinja templates.
- Produces: Public directory/profile HTML that contains email but not phone; staff HTML containing both.

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_hub.py`:

```python
def test_contact_phone_is_staff_only_and_email_is_public(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Student

        db.session.add(
            Student(
                name_en="Contact Student",
                name_ar="طالب",
                phone="01001234567",
                email="student@example.com",
            )
        )
        db.session.commit()

    directory = client.get("/directory").data.decode()
    profile = client.get("/student/1").data.decode()

    assert "student@example.com" in directory
    assert "student@example.com" in profile
    assert "01001234567" not in directory
    assert "01001234567" not in profile

    _login_as_staff(client, app)

    staff_profile = client.get("/student/1").data.decode()
    assert "student@example.com" in staff_profile
    assert "01001234567" in staff_profile


def test_anonymous_profile_with_only_phone_shows_empty_contact_state(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Student

        db.session.add(Student(name_en="Phone Only", name_ar="", phone="0100"))
        db.session.commit()

    profile = client.get("/student/1").data.decode()
    assert "0100" not in profile
    assert "No contact details added yet." in profile


def _login_as_staff(client, app):
    import re

    from app.extensions import db
    from app.models import User

    with app.app_context():
        user = User(username="staff", role="admin")
        user.set_password("pw")
        db.session.add(user)
        db.session.commit()

    page = client.get("/auth/login").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    client.post(
        "/auth/login",
        data={"username": "staff", "password": "pw", "csrf_token": token},
    )
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_hub.py::test_contact_phone_is_staff_only_and_email_is_public tests/test_hub.py::test_anonymous_profile_with_only_phone_shows_empty_contact_state -q`

Expected: FAIL because anonymous HTML contains the phone number and the empty state is not shown.

- [ ] **Step 3: Hide phone numbers in the directory**

In `app/templates/directory.html`, replace the phone block:

```jinja
                    {% if student.phone %}
                        <!-- tel: opens the phone dialer on mobile. -->
                        <a class="contact-link" href="tel:{{ student.phone }}">&#128222; {{ student.phone }}</a>
                    {% endif %}
```

with:

```jinja
                    {% if current_user.is_authenticated and student.phone %}
                        <!-- tel: opens the phone dialer on mobile. Phone is staff-only. -->
                        <a class="contact-link" href="tel:{{ student.phone }}">&#128222; {{ student.phone }}</a>
                    {% endif %}
```

- [ ] **Step 4: Hide phone numbers and fix the empty state on profiles**

In `app/templates/profile.html`, replace the phone block:

```jinja
            {% if student.phone %}
                <a class="contact-link" href="tel:{{ student.phone }}">&#128222; {{ student.phone }}</a>
            {% endif %}
```

with:

```jinja
            {% if current_user.is_authenticated and student.phone %}
                <a class="contact-link" href="tel:{{ student.phone }}">&#128222; {{ student.phone }}</a>
            {% endif %}
```

Then replace:

```jinja
        {% if not (website or facebook or instagram or student.phone or student.email) %}
            <p class="page-subtitle">No contact details added yet.</p>
        {% endif %}
```

with:

```jinja
        {% if not (website or facebook or instagram or (current_user.is_authenticated and student.phone) or student.email) %}
            <p class="page-subtitle">No contact details added yet.</p>
        {% endif %}
```

- [ ] **Step 5: Run the tests and verify they pass**

Run: `.venv/bin/python -m pytest tests/test_hub.py -q`

Expected: all tests in `tests/test_hub.py` pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_hub.py app/templates/directory.html app/templates/profile.html
git commit -m "fix: show student phone numbers only to staff"
```

---

### Task 2: Staff-only event form and safe event links

**Files:**
- Modify: `tests/test_hub.py`
- Modify: `app/hub/routes.py`
- Modify: `app/admin/routes.py`
- Modify: `app/templates/schedule.html`

**Interfaces:**
- Consumes: `app.security.safe_url(value) -> str`, which returns `""` for unsafe or empty URLs.
- Produces: Event create/edit routes reject unsafe links; schedule HTML hides the form for anonymous users and renders only safe links.

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_hub.py`:

```python
def test_anonymous_schedule_hides_event_form(client):
    page = client.get("/schedule").data.decode()
    assert "Post an event" not in page
    assert "Staff login is required to post an event." in page


def test_staff_schedule_shows_event_form(client, app):
    _login_as_staff(client, app)
    page = client.get("/schedule").data.decode()
    assert "Post an event" in page


def test_create_event_rejects_unsafe_link(client, app):
    _login_as_staff(client, app)
    with app.app_context():
        from app.extensions import db
        from app.models import Event, Student

        student = Student(name_en="Organizer", name_ar="منظم")
        db.session.add(student)
        db.session.commit()
        student_id = student.id

    response = client.post(
        "/schedule/add",
        data={
            "organizer_id": str(student_id),
            "title": "Unsafe Event",
            "link": "javascript:alert(1)",
        },
        follow_redirects=True,
    )

    assert "Event link must be a full http:// or https:// URL." in response.data.decode()
    with app.app_context():
        assert Event.query.count() == 0


def test_edit_event_rejects_unsafe_link(client, app):
    _login_as_staff(client, app)
    with app.app_context():
        from app.extensions import db
        from app.models import Event, Student

        student = Student(name_en="Organizer", name_ar="منظم")
        db.session.add(student)
        db.session.commit()
        event = Event(
            organizer_id=student.id,
            title="Safe Event",
            link="https://example.com/event",
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.post(
        f"/admin/event/{event_id}/edit",
        data={"title": "Changed", "link": "javascript:alert(1)"},
        follow_redirects=True,
    )

    assert "Event link must be a full http:// or https:// URL." in response.data.decode()
    with app.app_context():
        from app.extensions import db
        from app.models import Event

        event = db.session.get(Event, event_id)
        assert event.link == "https://example.com/event"
        assert event.title == "Safe Event"


def test_existing_unsafe_event_link_is_not_rendered(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Event, Student

        student = Student(name_en="Organizer", name_ar="منظم")
        db.session.add(student)
        db.session.commit()
        db.session.add(
            Event(
                organizer_id=student.id,
                title="Legacy Unsafe",
                link="javascript:alert(1)",
            )
        )
        db.session.commit()

    page = client.get("/schedule").data.decode()
    assert "javascript:alert(1)" not in page
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_hub.py::test_anonymous_schedule_hides_event_form tests/test_hub.py::test_staff_schedule_shows_event_form tests/test_hub.py::test_create_event_rejects_unsafe_link tests/test_hub.py::test_edit_event_rejects_unsafe_link tests/test_hub.py::test_existing_unsafe_event_link_is_not_rendered -q`

Expected: FAIL because the form is visible to everyone, unsafe links are stored, and the legacy link is rendered.

- [ ] **Step 3: Validate links in the public event route**

In `app/hub/routes.py`, add this import near the other app imports:

```python
from ..security import safe_url
```

In `add_event`, replace:

```python
    db.session.add(
        Event(
            organizer_id=int(organizer_id),
            title=title[:200],
            link=request.form.get("link", "").strip()[:500],
            description=request.form.get("description", "").strip(),
            event_date=event_date_display,
            event_date_actual=event_date_actual,
            location=request.form.get("location", "").strip()[:200],
        )
    )
```

with:

```python
    link = request.form.get("link", "").strip()
    if link and not safe_url(link):
        flash("Event link must be a full http:// or https:// URL.", "error")
        return redirect(url_for("hub.schedule"))

    db.session.add(
        Event(
            organizer_id=int(organizer_id),
            title=title[:200],
            link=link[:500],
            description=request.form.get("description", "").strip(),
            event_date=event_date_display,
            event_date_actual=event_date_actual,
            location=request.form.get("location", "").strip()[:200],
        )
    )
```

- [ ] **Step 4: Validate links in the admin edit route**

In `app/admin/routes.py`, add this import near the other app imports:

```python
from ..security import safe_url
```

In `edit_event`, replace:

```python
    item.title = title[:200]
    item.link = request.form.get("link", "").strip()[:500]
```

with:

```python
    link = request.form.get("link", "").strip()
    if link and not safe_url(link):
        flash("Event link must be a full http:// or https:// URL.", "error")
        return redirect(url_for("admin.index"))

    item.title = title[:200]
    item.link = link[:500]
```

- [ ] **Step 5: Hide the form and filter the link in the schedule template**

In `app/templates/schedule.html`, wrap the entire “Post an event” section in this condition:

```jinja
{% if current_user.is_authenticated %}
<section class="nes-container with-title is-rounded events-form">
    <!-- existing form markup stays unchanged -->
</section>
{% else %}
<section class="nes-container is-rounded events-form">
    <p class="title">Staff only</p>
    <p>Staff login is required to post an event.</p>
    <a class="nes-btn is-primary mt-1" href="{{ url_for('auth.login') }}">Log in</a>
</section>
{% endif %}
```

Keep the existing form markup inside the authenticated branch.

Then replace:

```jinja
                {% if ev.link %}<a class="nes-btn is-success" href="{{ ev.link }}" target="_blank" rel="noopener">&#128279; Open link</a>{% endif %}
```

with:

```jinja
                {% set event_link = ev.link|safe_url %}
                {% if event_link %}<a class="nes-btn is-success" href="{{ event_link }}" target="_blank" rel="noopener">&#128279; Open link</a>{% endif %}
```

- [ ] **Step 6: Run the tests and verify they pass**

Run: `.venv/bin/python -m pytest tests/test_hub.py -q`

Expected: all tests in `tests/test_hub.py` pass.

- [ ] **Step 7: Commit**

```bash
git add tests/test_hub.py app/hub/routes.py app/admin/routes.py app/templates/schedule.html
git commit -m "fix: protect event form and reject unsafe event links"
```

---

### Task 3: Saved-week CSV export

**Files:**
- Modify: `tests/test_dbweekly.py`
- Modify: `app/attendance/routes.py`
- Modify: `app/templates/attendance/week_saved.html`

**Interfaces:**
- Consumes: `aggregate_saved_week(start: date) -> dict` and existing `_download` helper.
- Produces: `GET /attendance/week/export.csv?start=YYYY-MM-DD` returns the saved-week CSV with `Cache-Control: no-store`.

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_dbweekly.py`:

```python
def test_saved_week_csv_export(client, app):
    user_id, student_id = _seed(app)
    with app.app_context():
        from app.attendance.services import save_attendance

        start = date(2026, 10, 18)
        for offset in range(5):
            save_attendance(
                start + timedelta(days=offset),
                {student_id: "present"},
                {},
                user_id,
            )

    _login(client)
    response = client.get("/attendance/week/export.csv?start=2026-10-18")

    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "no-store" in response.headers["Cache-Control"]
    text = response.data.decode()
    assert text.splitlines()[0] == (
        "student_id,name_en,name_ar,present,late,absent,percentage,absent_dates"
    )
    assert "A" in text


def test_saved_week_csv_rejects_invalid_start(client):
    _login(client)
    response = client.get(
        "/attendance/week/export.csv?start=not-a-date",
        follow_redirects=True,
    )
    assert "Invalid week start date." in response.data.decode()


def _login(client):
    import re

    page = client.get("/auth/login").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    client.post(
        "/auth/login",
        data={"username": "t", "password": "x", "csrf_token": token},
    )
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_dbweekly.py::test_saved_week_csv_export tests/test_dbweekly.py::test_saved_week_csv_rejects_invalid_start -q`

Expected: FAIL because the route ignores `start` and redirects to the upload page.

- [ ] **Step 3: Add the saved-week branch to the export route**

In `app/attendance/routes.py`, replace the entire `weekly_export` function:

```python
@bp.get("/attendance/week/export.csv")
@login_required
def weekly_export():
    summary = session.get("weekly_summary")
    if not summary:
        flash("Upload five daily files first.", "error")
        return redirect(url_for("attendance.weekly"))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["student_id", "name_en", "name_ar", "present", "late", "absent", "percentage", "absent_dates"]
    )
    for item in summary["students"]:
        writer.writerow(
            [
                item["student_id"],
                item["name_en"],
                item["name_ar"],
                item["present"],
                item.get("late", 0),
                item["absent"],
                item["percentage"],
                " ".join(item["absent_dates"]),
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=c1-weekly-attendance.csv"},
    )
```

with:

```python
@bp.get("/attendance/week/export.csv")
@login_required
def weekly_export():
    start_raw = request.args.get("start")
    if start_raw is not None:
        try:
            start = date.fromisoformat(start_raw)
        except (TypeError, ValueError):
            flash("Invalid week start date.", "error")
            return redirect(url_for("attendance.week_saved"))
        summary = aggregate_saved_week(start)
    else:
        summary = session.get("weekly_summary")
        if not summary:
            flash("Upload five daily files first.", "error")
            return redirect(url_for("attendance.weekly"))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["student_id", "name_en", "name_ar", "present", "late", "absent", "percentage", "absent_dates"]
    )
    for item in summary["students"]:
        writer.writerow(
            [
                item["student_id"],
                item["name_en"],
                item["name_ar"],
                item["present"],
                item.get("late", 0),
                item["absent"],
                item["percentage"],
                " ".join(item["absent_dates"]),
            ]
        )
    return _download(
        output.getvalue(),
        "text/csv",
        "c1-weekly-attendance.csv",
    )
```

- [ ] **Step 4: Pass the week start from the saved-week page**

In `app/templates/attendance/week_saved.html`, replace:

```jinja
        <a class="nes-btn is-success"
           href="{{ url_for('attendance.weekly_export') }}">Export weekly CSV</a>
```

with:

```jinja
        <a class="nes-btn is-success"
           href="{{ url_for('attendance.weekly_export', start=summary.start) }}">Export weekly CSV</a>
```

- [ ] **Step 5: Run the tests and verify they pass**

Run: `.venv/bin/python -m pytest tests/test_dbweekly.py tests/test_attendance.py -q`

Expected: all tests in both files pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_dbweekly.py app/attendance/routes.py app/templates/attendance/week_saved.html
git commit -m "fix: export saved weekly attendance from database"
```

---

### Task 4: Friendly database 503 handling

**Files:**
- Modify: `tests/test_health.py`
- Modify: `app/__init__.py`
- Create: `app/templates/errors/503.html`

**Interfaces:**
- Consumes: `sqlalchemy.exc.SQLAlchemyError`.
- Produces: HTML routes return `errors/503.html` with status 503; `/health` returns `{"status": "error", "database": "error"}` with status 503.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_health.py` with:

```python
from sqlalchemy.exc import OperationalError

from app.extensions import db


def _database_down(*args, **kwargs):
    raise OperationalError("SELECT 1", {}, Exception("database is down"))


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_health_returns_503_when_database_fails(client, monkeypatch):
    monkeypatch.setattr(db.session, "execute", _database_down)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "error"}


def test_database_error_renders_503_page(client, app):
    @app.get("/_database_down")
    def database_down():
        raise OperationalError("SELECT 1", {}, Exception("database is down"))

    response = client.get("/_database_down")

    assert response.status_code == 503
    assert "Database unavailable" in response.data.decode()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_health.py -q`

Expected: FAIL because `/health` raises and the database error page does not exist.

- [ ] **Step 3: Add the 503 template**

Create `app/templates/errors/503.html`:

```jinja
{% extends "base.html" %}
{% block content %}
<h2 class="page-title">Database unavailable</h2>
<p>The database is temporarily unavailable. Please try again in a moment.</p>
<a class="nes-btn is-primary" href="{{ url_for('hub.index') }}">Back home</a>
{% endblock %}
```

- [ ] **Step 4: Add the health check and global handler**

In `app/__init__.py`, add this import:

```python
from sqlalchemy.exc import SQLAlchemyError
```

Replace the health route with:

```python
    # Lightweight health check used by Railway and uptime monitors.
    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Health check database failure")
            return jsonify(status="error", database="error"), 503
        return jsonify(status="ok", database="ok")
```

Add this handler after the existing 500 handler:

```python
    @app.errorhandler(SQLAlchemyError)
    def database_unavailable(error):
        # Roll back any half-finished database work before showing the page.
        db.session.rollback()
        app.logger.exception("Database unavailable")
        return render_template("errors/503.html"), 503
```

- [ ] **Step 5: Run the tests and verify they pass**

Run: `.venv/bin/python -m pytest tests/test_health.py -q`

Expected: all tests in `tests/test_health.py` pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_health.py app/__init__.py app/templates/errors/503.html
git commit -m "fix: return friendly 503 responses when the database is unavailable"
```

---

### Task 5: Student-facing README and deployment docs cleanup

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Delete: `render.yaml`
- Add: `docs/DATABASE_SCHEMA.md`
- Add: `docs/database_schema.png`
- Add: `docs/database_schema_clean`
- Add: `docs/database_schema_clean.png`

**Interfaces:**
- Consumes: existing project docs, CLI commands, Railway settings, and `docs/Logo/Logo.png`.
- Produces: a tracked README for student contributors with the project logo, development rules, setup, tests, privacy constraints, and Railway deployment notes.

- [ ] **Step 1: Stop ignoring README and remove the stale Render config**

In `.gitignore`, remove this line:

```gitignore
README.md
```

Keep this line:

```gitignore
COMMANDS.md
```

Delete `render.yaml`:

```bash
git rm render.yaml
```

- [ ] **Step 2: Replace README with the student contributor guide**

Replace the full contents of `README.md` with:

````markdown
![C1 Hub logo](docs/Logo/Logo.png)

# C1 Hub + Attendance

A Flask + PostgreSQL app for class C1 at Egypt-Japan KOSEN. It combines the
student hub (bulletin, games, directory, events, news) with a staff-only
attendance checklist and bilingual exports.

This README is for students helping with development. Read it before changing
code, and ask before adding a new library or a new public data field.

## Tech stack

- Python / Flask app factory with blueprints
- SQLAlchemy + Flask-Migrate
- Flask-Login for staff login
- Flask-WTF for CSRF protection
- PostgreSQL/Neon in production, SQLite locally
- NES.css pixel UI, vendored locally
- pytest for Python tests, ESLint for JavaScript

## Project map

```text
app/
├── __init__.py        app factory, error pages, health check
├── config.py          environment-driven settings
├── models.py          database models
├── security.py        safe URL and media helpers
├── auth/              staff login/logout
├── hub/               public bulletin, directory, events, calendar
├── attendance/        daily checklist, weekly report, PNG/Excel/CSV exports
├── admin/             staff management panel
├── news/              RSS feeds
├── templates/         Jinja pages
└── static/            CSS, JavaScript, fonts, images
tests/                 pytest suite
docs/                  design specs and implementation plans
scripts/roster.js      the class roster seed data
migrations/            database migrations
wsgi.py                production entry point
```

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app wsgi db upgrade
flask --app wsgi seed-roster
flask --app wsgi create-admin --username teacher
flask --app wsgi run --debug
```

Open <http://127.0.0.1:5000>.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs session cookies and CSRF tokens. Use a long random value. |
| `DATABASE_URL` | PostgreSQL URL, or empty for local SQLite. |
| `FLASK_ENV` | `development` locally, `production` on Railway. |
| `FLASK_APP` | `wsgi.py`. |

Never commit `.env`, passwords, or database dumps.

## Development rules

1. **Read the design before changing behavior.** Specs are in
   `docs/superpowers/specs/`; implementation plans are in
   `docs/superpowers/plans/`.
2. **Make small, focused changes.** One feature or fix per commit.
3. **Test-first for behavior changes.** Add a failing test, make it pass, then
   commit.
4. **Run the whole test suite before you finish:** `.venv/bin/python -m pytest -q`.
5. **Run the JavaScript linter if you touch JS:** `npm run lint:js`.
6. **Use migrations for model changes.** Run `flask --app wsgi db migrate -m "..."`
   and `flask --app wsgi db upgrade`. Never edit the production database by hand.
7. **Follow existing patterns.** Reuse helpers such as `safe_url` and
   `media_url`; do not add a new framework for a small change.
8. **Do not commit secrets.** `.env`, local databases, and local notes are
   ignored.
9. **Preserve privacy.** Student email is public; student phone numbers are
   staff-only. Join requests are public. Do not add public personal data
   without reviewing the privacy impact first.
10. **Treat user-supplied URLs as untrusted.** Only `http`/`https` links may be
    rendered; pass them through `safe_url`.
11. **Keep attendance CSV compatible.** The header and weekly-upload format must
    not change without updating the spec, tests, and documentation.
12. **Keep commits readable.** Explain what changed and why, not just which
    files changed.

## Making a change

```bash
git switch -c your-change-name
# write a failing test
.venv/bin/python -m pytest tests/test_the_feature.py -q
# implement the smallest fix
.venv/bin/python -m pytest -q
npm run lint:js
git add <files>
git commit -m "type: short description"
```

Push the branch and open a pull request. Do not commit `COMMANDS.md`, `.env`,
local database files, or generated caches.

## Tests and lint

```bash
.venv/bin/python -m pytest -q
npm run lint:js
```

## Attendance exports

The daily CSV header is stable:

```csv
date,student_id,name_en,name_ar,status,note
2026-10-22,1,Abdelrahman Khaled Mahdy,عبد الرحمن خالد مهدي,present,
```

PNG and Excel use the bilingual reference design and download as
`YYYY-MM-DD-c1Class-attendance.*`. The CSV name remains
`YYYY-MM-DD-c1-attendance.csv`.

## Deployment

The live app runs on Railway at
<https://cdungeonsdragons-production.up.railway.app>. Pushing `main` deploys
automatically.

- Build: Railpack detects Python and installs `requirements.txt`.
- Start: `gunicorn wsgi:app`
- Health check: `/health`
- Production Python: 3.13
- Runtime system package: `libraqm0` (required for Arabic shaping in PNGs)

Run database commands from the Railway shell:

```bash
flask --app wsgi db upgrade
flask --app wsgi create-admin --username teacher
```

Check the live app:

```bash
curl https://cdungeonsdragons-production.up.railway.app/health
```

Expected: `{"status":"ok","database":"ok"}`

## Backups

```bash
pg_dump "$DATABASE_URL" > backup-$(date +%F).sql
psql "$DATABASE_URL" < backup-2026-10-22.sql
```

Back up regularly. A free database is not a backup.

## More docs

- Attendance MVP design: `docs/superpowers/specs/2026-10-22-c1-hub-attendance-mvp-design.md`
- Export parity design: `docs/superpowers/specs/2026-10-28-attendance-export-parity-design.md`
- Database schema: `docs/DATABASE_SCHEMA.md`
````

- [ ] **Step 3: Stage the schema documentation and verify the README is tracked**

```bash
git add README.md .gitignore
git add docs/DATABASE_SCHEMA.md docs/database_schema.png docs/database_schema_clean docs/database_schema_clean.png
git status --short
```

Expected: `README.md` is staged, `render.yaml` is staged as deleted, and the four schema files are staged. `COMMANDS.md` must not appear.

- [ ] **Step 4: Run the full test suite and lint**

Run: `.venv/bin/python -m pytest -q`

Expected: all tests pass.

Run: `npm run lint:js`

Expected: no lint errors.

- [ ] **Step 5: Commit**

```bash
git commit -m "docs: add student contributor README and clean deployment docs"
```

---

## Self-Review Checklist

- [ ] Every spec behavior maps to a task above.
- [ ] No placeholders or "similar to Task N" references remain.
- [ ] Function names and imports match the existing codebase.
- [ ] Each code-changing task has a failing test, implementation, passing test, and commit.
- [ ] The README is student-facing, includes the logo, and documents privacy rules.
- [ ] `render.yaml` is removed and Railway instructions are accurate.
- [ ] Full test suite and JavaScript lint pass before final completion.

## Execution Notes

- Commit each task separately; do not squash.
- If a test fails for a reason not described here, stop and investigate the root cause before changing production code.
- The final response must include the exact test and lint results.
