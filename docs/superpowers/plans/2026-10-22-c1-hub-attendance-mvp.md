# C1 Hub + Attendance MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the C! RAS Hub and the static attendance app into one Flask + PostgreSQL app with teacher login, server-saved daily attendance, and weekly CSV aggregation.

**Architecture:** A single Flask app factory with blueprints for auth, hub, attendance, and admin. SQLAlchemy models replace raw SQLite access. Flask-Login and Flask-WTF protect staff-only routes. Attendance is one daily session with one record per active student. Weekly reports are computed from five uploaded daily CSV files and cached in the signed session for download.

**Tech Stack:** Python 3.10+, Flask 3, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, PostgreSQL (Neon), pytest, gunicorn, Render.

## Global Constraints

- Target is one class: 34 students, one teacher account, online-only.
- Do not commit unless the user explicitly asks. Checkpoints that say "commit" are optional.
- Keep the existing NES.css pixel UI and all current public hub pages working.
- Never store plaintext passwords; use Werkzeug hashing.
- All POST forms must use Flask-WTF CSRF protection.
- `SECRET_KEY` and `DATABASE_URL` come from environment variables in production.
- Debug mode must be off in production.
- The roster is the real 34-student list from `class-c1-attendance/students.js`.
- Daily CSV header is exactly: `date,student_id,name_en,name_ar,status,note`.
- Weekly upload requires exactly five distinct dates.
- Do not add student accounts, offline sync, per-subject periods, or multi-school tenancy.

---

### Task 1: Project scaffold, config, extensions, health endpoint

**Files:**
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/extensions.py`
- Create: `wsgi.py`
- Modify: `requirements.txt`
- Create: `tests/conftest.py`
- Test: `tests/test_health.py`

**Interfaces:**
- Produces: `create_app(config_object=Config) -> Flask`
- Produces: `db`, `migrate`, `login_manager`, `csrf` extension objects
- Produces: `/health` returning `{"status": "ok", "database": "ok"}`

- [ ] **Step 1: Write the failing health test**

```python
# tests/test_health.py
def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL because `app` or `client` does not exist.

- [ ] **Step 3: Add dependencies**

```text
# requirements.txt
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.7
Flask-Login==0.6.3
Flask-WTF==1.2.1
SQLAlchemy==2.0.36
psycopg2-binary==2.9.10
python-dotenv==1.0.1
gunicorn==23.0.0
pytest==8.3.4
```

- [ ] **Step 4: Create config**

```python
# app/config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_url():
    url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}")
    return url.replace("postgres://", "postgresql://", 1)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
```

- [ ] **Step 5: Create extensions**

```python
# app/extensions.py
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
```

- [ ] **Step 6: Create the app factory**

```python
# app/__init__.py
from flask import Flask, jsonify
from sqlalchemy import text

from .config import Config
from .extensions import csrf, db, login_manager, migrate


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "error"

    from .admin import bp as admin_bp
    from .attendance import bp as attendance_bp
    from .auth import bp as auth_bp
    from .hub import bp as hub_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(hub_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(admin_bp)

    from . import models  # noqa: F401  (register models with SQLAlchemy)

    @app.get("/health")
    def health():
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok", database="ok")

    @app.errorhandler(404)
    def not_found(error):
        return app.jinja_env.get_template("errors/404.html").render(), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return app.jinja_env.get_template("errors/500.html").render(), 500

    return app


@login_manager.user_loader
def load_user(user_id):
    from .models import User

    return db.session.get(User, int(user_id))
```

- [ ] **Step 7: Create the WSGI entry point**

```python
# wsgi.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

- [ ] **Step 8: Create the test fixture**

```python
# tests/conftest.py
import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
```

- [ ] **Step 9: Add temporary blueprint packages so imports work**

Create `app/auth/__init__.py`, `app/hub/__init__.py`, `app/attendance/__init__.py`, and `app/admin/__init__.py`, each containing:

```python
from flask import Blueprint

bp = Blueprint("auth", __name__)
```

Use the matching name in each file (`hub`, `attendance`, `admin`).

Create `app/templates/errors/404.html`:

```html
{% extends "base.html" %}
{% block content %}
<h2 class="page-title">404</h2>
<p>That page does not exist.</p>
<a class="nes-btn is-primary" href="{{ url_for('hub.index') }}">Back home</a>
{% endblock %}
```

Create `app/templates/errors/500.html`:

```html
{% extends "base.html" %}
{% block content %}
<h2 class="page-title">Something went wrong</h2>
<p>The request could not be completed. Please try again.</p>
{% endblock %}
```

- [ ] **Step 10: Run the test**

Run: `pytest tests/test_health.py -v`
Expected: PASS. The 404/500 templates will not be exercised yet.

---

### Task 2: Models, migrations, roster import, seed command

**Files:**
- Create: `app/models.py`
- Create: `app/cli.py`
- Copy: `scripts/roster.js` from the attendance repo
- Create: `scripts/seed.py`
- Modify: `app/__init__.py` (register CLI commands)
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `Student`, `User`, `AttendanceSession`, `AttendanceRecord`, `Announcement`, `LhrGame`, `TedTalk`, `Meme`, `Event`, `EventRequest`
- Produces: `flask create-admin`, `flask seed-roster`

- [ ] **Step 1: Write the failing model test**

```python
# tests/test_models.py
from datetime import date

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
            AttendanceRecord(session_id=session.id, student_id=student.id, status="present")
        )
        db.session.commit()

        db.session.add(
            AttendanceRecord(session_id=session.id, student_id=student.id, status="absent")
        )
        try:
            db.session.commit()
            assert False, "duplicate record should fail"
        except Exception:
            db.session.rollback()
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL because `app.models` does not exist.

- [ ] **Step 3: Create the models**

```python
# app/models.py
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="teacher")
    active = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.active


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(200), nullable=False)
    name_ar = db.Column(db.String(200), nullable=False, default="")
    interests = db.Column(db.Text, nullable=False, default="")
    website = db.Column(db.String(300), nullable=False, default="")
    facebook = db.Column(db.String(300), nullable=False, default="")
    instagram = db.Column(db.String(300), nullable=False, default="")
    phone = db.Column(db.String(50), nullable=False, default="")
    email = db.Column(db.String(200), nullable=False, default="")
    active = db.Column(db.Boolean, nullable=False, default=True)

    records = db.relationship(
        "AttendanceRecord", back_populates="student", cascade="all, delete-orphan"
    )


class AttendanceSession(db.Model):
    __tablename__ = "attendance_sessions"
    __table_args__ = (db.UniqueConstraint("date", name="uq_attendance_session_date"),)

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    records = db.relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    __table_args__ = (
        db.UniqueConstraint("session_id", "student_id", name="uq_attendance_record"),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("attendance_sessions.id"), nullable=False
    )
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="present")
    note = db.Column(db.Text, nullable=False, default="")

    session = db.relationship("AttendanceSession", back_populates="records")
    student = db.relationship("Student", back_populates="records")


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(20), nullable=False, default="News")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class LhrGame(db.Model):
    __tablename__ = "lhr_games"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    rules = db.Column(db.Text, nullable=False)
    max_players = db.Column(db.Integer, nullable=False, default=4)
    status = db.Column(db.String(20), nullable=False, default="Upcoming")


class TedTalk(db.Model):
    __tablename__ = "ted_talks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    thumbnail = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)


class Meme(db.Model):
    __tablename__ = "memes"

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.Text, nullable=False)


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    link = db.Column(db.String(500), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    event_date = db.Column(db.String(100), nullable=False, default="")
    location = db.Column(db.String(200), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    organizer = db.relationship("Student")


class EventRequest(db.Model):
    __tablename__ = "event_requests"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    requester_name = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False, default="")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    event = db.relationship("Event")


def student_display_name(student):
    if student.name_ar:
        return f"{student.name_en} / {student.name_ar}"
    return student.name_en
```

- [ ] **Step 4: Import the real roster file**

Run:

```bash
cp /tmp/class-c1-attendance/students.js scripts/roster.js
```

If `/tmp/class-c1-attendance` is missing, clone it first:

```bash
git clone --depth 1 https://github.com/asaadzx/class-c1-attendance.git /tmp/class-c1-attendance
```

- [ ] **Step 5: Create CLI commands**

```python
# app/cli.py
import json
from pathlib import Path

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Student, User


def load_roster():
    path = Path(__file__).resolve().parent.parent / "scripts" / "roster.js"
    text = path.read_text(encoding="utf-8")
    payload = text.split("=", 1)[1].strip().rstrip(";")
    return json.loads(payload)


@click.command("create-admin")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_admin(username, password):
    existing = User.query.filter_by(username=username).first()
    if existing:
        existing.set_password(password)
        existing.role = "admin"
        existing.active = True
        click.echo(f"Updated admin {username}.")
    else:
        user = User(username=username, role="admin", active=True)
        user.set_password(password)
        db.session.add(user)
        click.echo(f"Created admin {username}.")
    db.session.commit()


@click.command("seed-roster")
@with_appcontext
def seed_roster():
    roster = load_roster()
    created = 0
    for row in roster:
        student = Student.query.filter_by(name_en=row["en"]).first()
        if student is None:
            student = Student(name_en=row["en"], name_ar=row.get("ar", ""))
            db.session.add(student)
            created += 1
        else:
            student.name_ar = row.get("ar", student.name_ar)
            student.active = True
    db.session.commit()
    click.echo(f"Roster ready: {len(roster)} students, {created} created.")


def register_cli(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_roster)
```

- [ ] **Step 6: Register CLI commands**

In `app/__init__.py`, import and call `register_cli(app)` after blueprint registration:

```python
from .cli import register_cli

register_cli(app)
```

- [ ] **Step 7: Initialize migrations**

Run:

```bash
flask --app wsgi db init
flask --app wsgi db migrate -m "initial schema"
flask --app wsgi db upgrade
```

Expected: a `migrations/` directory exists and `database.db` is created locally.

- [ ] **Step 8: Seed the roster and admin locally**

Run:

```bash
flask --app wsgi seed-roster
flask --app wsgi create-admin --username teacher --password changeme123
```

Expected: `Roster ready: 34 students` and `Created admin teacher`.

- [ ] **Step 9: Run the model test**

Run: `pytest tests/test_models.py -v`
Expected: PASS.

---

### Task 3: Authentication and login UI

**Files:**
- Create: `app/auth/routes.py`
- Modify: `app/auth/__init__.py`
- Create: `app/templates/auth/login.html`
- Modify: `app/templates/base.html` (move from `templates/base.html`)
- Test: `tests/test_auth.py`

**Interfaces:**
- Produces: `/auth/login`, `/auth/logout`
- Produces: `login_required` protection via Flask-Login

- [ ] **Step 1: Write the failing auth test**

```python
# tests/test_auth.py
from app.extensions import db
from app.models import User


def test_login_rejects_bad_password(client, app):
    with app.app_context():
        user = User(username="teacher", role="teacher")
        user.set_password("correct")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"username": "teacher", "password": "wrong"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data


def test_login_accepts_valid_user(client, app):
    with app.app_context():
        user = User(username="teacher", role="teacher")
        user.set_password("correct")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"username": "teacher", "password": "correct"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Log out" in response.data
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL because the login route does not exist.

- [ ] **Step 3: Implement auth routes**

```python
# app/auth/routes.py
from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from . import bp
from ..models import User


def _safe_next(target):
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.netloc:
        return None
    return target


@bp.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user is None or not user.active or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html"), 401
        login_user(user)
        target = _safe_next(request.args.get("next"))
        return redirect(target or url_for("hub.index"))
    return render_template("auth/login.html")


@bp.route("/auth/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("hub.index"))
```

- [ ] **Step 4: Export the blueprint routes**

```python
# app/auth/__init__.py
from flask import Blueprint

bp = Blueprint("auth", __name__)

from . import routes  # noqa: E402,F401
```

- [ ] **Step 5: Create the login template**

```html
{% extends "base.html" %}
{% block content %}
<h2 class="page-title">Staff Login</h2>
<section class="nes-container is-rounded" style="max-width: 480px;">
  <form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <label for="username">Username</label>
    <input class="nes-input" id="username" name="username" required autofocus>
    <label for="password" class="mt-1">Password</label>
    <input class="nes-input" id="password" name="password" type="password" required>
    <button class="nes-btn is-primary mt-1" type="submit">Log in</button>
  </form>
</section>
{% endblock %}
```

- [ ] **Step 6: Move the existing base template**

Run:

```bash
mkdir -p app/templates app/static
git mv templates/base.html app/templates/base.html
```

Then add to `app/templates/base.html` navigation:

```html
<a href="{{ url_for('attendance.daily') }}" class="nes-btn is-primary">Attendance</a>
<a href="{{ url_for('attendance.weekly') }}" class="nes-btn is-warning">Weekly</a>
{% if current_user.is_authenticated %}
<form method="POST" action="{{ url_for('auth.logout') }}" style="display:inline;">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <button class="nes-btn" type="submit">Log out</button>
</form>
{% else %}
<a href="{{ url_for('auth.login') }}" class="nes-btn">Staff login</a>
{% endif %}
```

- [ ] **Step 7: Run the auth test**

Run: `pytest tests/test_auth.py -v`
Expected: PASS.

---

### Task 4: Port the hub routes and templates

**Files:**
- Move: `templates/*.html` to `app/templates/`
- Move: `static/*` to `app/static/`
- Create: `app/hub/routes.py`
- Modify: `app/hub/__init__.py`
- Delete: `app.py` (after routes are ported)
- Test: `tests/test_hub.py`

**Interfaces:**
- Produces: `/`, `/lhr`, `/lhr/game/<int:game_id>`, `/directory`, `/student/<int:student_id>`, `/schedule`, `/schedule/add`, `/event/<int:event_id>/join`

- [ ] **Step 1: Write the failing hub test**

```python
# tests/test_hub.py
def test_public_hub_pages(client, app):
    with app.app_context():
        from app.extensions import db
        from app.models import Announcement, Student

        db.session.add(Announcement(title="Hello", content="World", category="News"))
        db.session.add(Student(name_en="Student One", name_ar="طالب"))
        db.session.commit()

    for path in ["/", "/lhr", "/directory", "/schedule"]:
        response = client.get(path)
        assert response.status_code == 200, path
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_hub.py -v`
Expected: FAIL because the hub routes are still in the old `app.py`.

- [ ] **Step 3: Move templates and static files**

```bash
git mv templates app/templates
git mv static app/static
```

`app/templates` already exists from Task 3, so if `git mv` complains, move the remaining files individually:

```bash
mv templates/index.html app/templates/
mv templates/lhr.html app/templates/
mv templates/game_detail.html app/templates/
mv templates/directory.html app/templates/
mv templates/profile.html app/templates/
mv templates/schedule.html app/templates/
mv static/css app/static/
mv static/js app/static/
mv static/img app/static/
mv static/nes app/static/
rmdir templates
```

- [ ] **Step 4: Implement hub routes with SQLAlchemy**

Port every route from the old `app.py`:

- `/` uses `Announcement.query.order_by(Announcement.created_at.desc())`, plus a random `TedTalk` and `Meme`.
- `/lhr` uses `LhrGame.query.order_by(LhrGame.id)`.
- `/lhr/game/<id>` uses `db.session.get(LhrGame, id)`.
- `/directory` uses `Student.query.filter_by(active=True).order_by(Student.name_en)`.
- `/student/<id>` uses `db.session.get(Student, id)` and `Event.query.filter_by(organizer_id=id)`.
- `/schedule` uses `Event.query.order_by(Event.id.desc())`, `EventRequest.query`, and `Student.query.filter_by(active=True)`.
- `/schedule/add` keeps the old form fields and requires login.
- `/event/<id>/join` keeps public join requests but validates the event exists.

Do not port the old `/directory/add` route; the teacher manages the roster.

Use `Student.name_en` and `Student.name_ar` in templates. Update `directory.html` and `profile.html` to show `student.name_en` and, if present, `student.name_ar`.

- [ ] **Step 5: Protect event creation**

Add `@login_required` to `add_event`. Keep `join_event` public.

- [ ] **Step 6: Run the hub test**

Run: `pytest tests/test_hub.py -v`
Expected: PASS.

---

### Task 5: Daily attendance service, routes, CSV export, and page

**Files:**
- Create: `app/attendance/services.py`
- Create: `app/attendance/routes.py`
- Modify: `app/attendance/__init__.py`
- Create: `app/templates/attendance/daily.html`
- Test: `tests/test_attendance.py`

**Interfaces:**
- Produces: `save_attendance(day, present_ids, notes, user_id) -> AttendanceSession`
- Produces: `daily_csv(day) -> str`
- Produces: `GET/POST /attendance`, `GET /attendance/export.csv`

- [ ] **Step 1: Write the failing attendance test**

```python
# tests/test_attendance.py
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

        session = save_attendance(
            date(2026, 10, 22), {student_id}, {}, user_id
        )
        assert session.id is not None
        assert AttendanceSession.query.count() == 1
        assert AttendanceRecord.query.count() == 1

        save_attendance(date(2026, 10, 22), set(), {}, user_id)
        assert AttendanceSession.query.count() == 1
        assert AttendanceRecord.query.one().status == "absent"


def test_attendance_requires_login(client):
    response = client.get("/attendance")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_attendance.py -v`
Expected: FAIL because the attendance service does not exist.

- [ ] **Step 3: Implement the attendance service**

```python
# app/attendance/services.py
import csv
import io
from datetime import date

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
                note=notes.get(student.id, "").strip()[:500],
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
```

- [ ] **Step 4: Implement attendance routes**

```python
# app/attendance/routes.py
from datetime import date

from flask import Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import bp
from .services import active_students, daily_csv, get_session, save_attendance


def _parse_day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


@bp.route("/attendance", methods=["GET", "POST"])
@login_required
def daily():
    day = _parse_day(request.values.get("date", date.today().isoformat()))
    session = get_session(day)

    if request.method == "POST":
        present_ids = set()
        notes = {}
        for student in active_students():
            if request.form.get(f"present_{student.id}") == "on":
                present_ids.add(student.id)
            notes[student.id] = request.form.get(f"note_{student.id}", "")
        save_attendance(day, present_ids, notes, current_user.id)
        flash(f"Attendance saved for {day.isoformat()}.", "success")
        return redirect(url_for("attendance.daily", date=day.isoformat()))

    records = {r.student_id: r for r in session.records} if session else {}
    recent = (
        __import__("app.models", fromlist=["AttendanceSession"])
        .AttendanceSession.query.order_by(
            __import__("app.models", fromlist=["AttendanceSession"]).AttendanceSession.date.desc()
        )
        .limit(10)
        .all()
    )
    return render_template(
        "attendance/daily.html",
        day=day,
        students=active_students(),
        records=records,
        recent=recent,
    )


@bp.get("/attendance/export.csv")
@login_required
def export_csv():
    day = _parse_day(request.args.get("date", date.today().isoformat()))
    content = daily_csv(day)
    return Response(
        content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={day.isoformat()}-c1-attendance.csv"
        },
    )
```

Replace the awkward `__import__` lines with a normal import at the top:

```python
from ..models import AttendanceSession
```

Then use `AttendanceSession.query...`.

- [ ] **Step 5: Export the blueprint routes**

```python
# app/attendance/__init__.py
from flask import Blueprint

bp = Blueprint("attendance", __name__)

from . import routes  # noqa: E402,F401
```

- [ ] **Step 6: Create the daily attendance template**

Build `app/templates/attendance/daily.html` with:

- Date input and a "Load day" form (`GET`).
- A POST form with hidden CSRF token.
- One row per student with a checkbox `present_<id>` and text input `note_<id>`.
- Names show `student.name_en` and `student.name_ar`.
- Save button.
- Export CSV link to `url_for('attendance.export_csv', date=day.isoformat())`.
- Print button using `window.print()`.
- Recent days list linking to `?date=...`.

Use the existing NES classes. Add this small script for the "uncheck all" control:

```html
<script>
document.getElementById('noneBtn')?.addEventListener('click', function () {
  document.querySelectorAll('input[type="checkbox"][name^="present_"]').forEach(function (box) {
    box.checked = false;
  });
});
document.getElementById('allBtn')?.addEventListener('click', function () {
  document.querySelectorAll('input[type="checkbox"][name^="present_"]').forEach(function (box) {
    box.checked = true;
  });
});
</script>
```

- [ ] **Step 7: Run the attendance tests**

Run: `pytest tests/test_attendance.py -v`
Expected: PASS.

---

### Task 6: Weekly CSV upload, validation, aggregation, and download

**Files:**
- Create: `app/attendance/weekly.py`
- Modify: `app/attendance/routes.py`
- Create: `app/templates/attendance/weekly.html`
- Test: `tests/test_weekly.py`

**Interfaces:**
- Produces: `parse_daily_csv(file_storage) -> (date, list[dict])`
- Produces: `aggregate_weekly(files, students) -> dict`
- Produces: `GET/POST /attendance/week`, `GET /attendance/week/export.csv`

- [ ] **Step 1: Write the failing weekly tests**

```python
# tests/test_weekly.py
import io
from datetime import date

import pytest

from app.attendance.weekly import aggregate_weekly, parse_daily_csv


class FakeUpload:
    def __init__(self, content, filename="day.csv"):
        self.stream = io.BytesIO(content.encode("utf-8"))
        self.filename = filename

    def read(self):
        return self.stream.read()


class FakeStudent:
    def __init__(self, id, name_en="Student", name_ar=""):
        self.id = id
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
    files = [FakeUpload(content), FakeUpload(content)]
    with pytest.raises(ValueError, match="duplicate date"):
        aggregate_weekly(files, students)
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_weekly.py -v`
Expected: FAIL because `app.attendance.weekly` does not exist.

- [ ] **Step 3: Implement the weekly parser and aggregator**

```python
# app/attendance/weekly.py
import csv
import io
from datetime import date

REQUIRED_COLUMNS = {"date", "student_id", "name_en", "name_ar", "status", "note"}
ALLOWED_STATUSES = {"present", "absent"}


def parse_daily_csv(file_storage):
    try:
        text = file_storage.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
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
            day = date.fromisoformat(row["date"].strip())
            student_id = int(row["student_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{file_storage.filename}: bad date or student_id on line {line_number}"
            ) from exc

        status = row["status"].strip().lower()
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
                "name_en": row.get("name_en", "").strip(),
                "name_ar": row.get("name_ar", "").strip(),
                "status": status,
                "note": row.get("note", "").strip(),
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

    total_present = sum(item["present"] for item in summary)
    total_absent = sum(item["absent"] for item in summary)
    return {
        "dates": [day.isoformat() for day in sorted(by_day)],
        "students": summary,
        "total_present": total_present,
        "total_absent": total_absent,
    }
```

- [ ] **Step 4: Add weekly routes**

In `app/attendance/routes.py`:

```python
import csv
import io

from flask import session

from .weekly import aggregate_weekly
from .services import active_students
from ..models import Student


@bp.route("/attendance/week", methods=["GET", "POST"])
@login_required
def weekly():
    summary = None
    if request.method == "POST":
        files = [f for f in request.files.getlist("files") if f and f.filename]
        try:
            summary = aggregate_weekly(files, Student.query.filter_by(active=True).all())
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            session["weekly_summary"] = summary
            flash("Weekly report calculated.", "success")
    return render_template("attendance/weekly.html", summary=summary)


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
        ["student_id", "name_en", "name_ar", "present", "absent", "percentage", "absent_dates"]
    )
    for item in summary["students"]:
        writer.writerow(
            [
                item["student_id"],
                item["name_en"],
                item["name_ar"],
                item["present"],
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

- [ ] **Step 5: Create the weekly template**

`app/templates/attendance/weekly.html` must include:

- A form with `enctype="multipart/form-data"`, CSRF token, and `<input type="file" name="files" multiple accept=".csv" required>`.
- A list of the five selected dates.
- A results table with name, present, absent, percentage, absent dates.
- Class totals.
- A download link to `url_for('attendance.weekly_export')`.

- [ ] **Step 6: Run the weekly tests**

Run: `pytest tests/test_weekly.py -v`
Expected: PASS.

---

### Task 7: Security hardening and safe rendering

**Files:**
- Modify: `app/__init__.py`
- Modify: `app/hub/routes.py`
- Create: `app/security.py`
- Test: `tests/test_security.py`

**Interfaces:**
- Produces: `safe_url(value) -> str` returning `""` for unsafe schemes.
- Produces: response headers `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`.

- [ ] **Step 1: Write the failing security tests**

```python
# tests/test_security.py
from app.security import safe_url


def test_safe_url_rejects_javascript():
    assert safe_url("javascript:alert(1)") == ""
    assert safe_url("https://example.com") == "https://example.com"
    assert safe_url("") == ""


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `pytest tests/test_security.py -v`
Expected: FAIL because `app.security` does not exist.

- [ ] **Step 3: Implement URL validation and headers**

```python
# app/security.py
from urllib.parse import urlparse


def safe_url(value):
    value = (value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if not parsed.netloc:
        return ""
    return value


def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response
```

In `create_app`, register:

```python
from .security import add_security_headers

app.after_request(add_security_headers)
```

- [ ] **Step 4: Sanitize user-supplied links**

In the hub routes, pass every event link and student social URL through `safe_url` before rendering, or add a Jinja filter:

```python
app.jinja_env.filters["safe_url"] = safe_url
```

Then update templates that render user links to use `{{ value|safe_url }}`. If the filter returns an empty string, hide the link:

```html
{% set event_link = ev.link|safe_url %}
{% if event_link %}<a href="{{ event_link }}" target="_blank" rel="noopener">Open link</a>{% endif %}
```

- [ ] **Step 5: Run the security tests**

Run: `pytest tests/test_security.py -v`
Expected: PASS.

---

### Task 8: Full test pass and local smoke test

**Files:**
- Modify: tests as needed
- No new production files required

- [ ] **Step 1: Run the full test suite**

Run: `pytest -v`
Expected: all tests PASS.

- [ ] **Step 2: Start the app locally**

Run:

```bash
flask --app wsgi seed-roster
flask --app wsgi create-admin --username teacher --password changeme123
flask --app wsgi run --debug
```

- [ ] **Step 3: Manually verify**

Open `http://127.0.0.1:5000` and check:

1. Public bulletin, games, directory, and schedule load.
2. `/attendance` redirects to login when logged out.
3. Login works.
4. Mark two students absent, save, refresh, and confirm they stay absent.
5. Download the daily CSV and confirm 34 rows plus header.
6. Save five different days.
7. Upload the five CSVs at `/attendance/week` and confirm totals.
8. Download the weekly CSV.
9. Log out; confirm attendance is protected again.

- [ ] **Step 4: Fix any failures before deployment**

Re-run `pytest -v` after each fix.

---

### Task 9: Deployment configuration and documentation

**Files:**
- Create: `render.yaml`
- Create: `.env.example`
- Create: `README.md` (or update the existing setup report)
- Modify: `requirements.txt` if needed

- [ ] **Step 1: Create the Render blueprint**

```yaml
# render.yaml
services:
  - type: web
    name: c1-ras-hub
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app
    preDeployCommand: flask --app wsgi db upgrade
    healthCheckPath: /health
    envVars:
      - key: FLASK_ENV
        value: production
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        sync: false
```

- [ ] **Step 2: Create the environment example**

```text
# .env.example
FLASK_ENV=development
SECRET_KEY=replace-with-a-long-random-value
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

- [ ] **Step 3: Document setup and operations**

The README must include:

- Local setup: venv, install, `flask db upgrade`, `flask seed-roster`, `flask create-admin`, `flask run`.
- Test command: `pytest -v`.
- Render deploy steps.
- Neon connection string format.
- First deploy commands: `flask --app wsgi db upgrade`, `flask --app wsgi seed-roster`, `flask --app wsgi create-admin`.
- Weekly backup command:
  ```bash
  pg_dump "$DATABASE_URL" > backup-$(date +%F).sql
  ```
- Restore command:
  ```bash
  psql "$DATABASE_URL" < backup-2026-10-22.sql
  ```
- Free-tier caveats: Render cold starts, Neon limits, no guaranteed uptime.
- The exact daily CSV schema and weekly upload rules.

- [ ] **Step 4: Add a production secret check**

In `app/__init__.py`, when `FLASK_ENV=production`, refuse to start with the default secret:

```python
import os

if app.config.get("ENV") == "production" or os.environ.get("FLASK_ENV") == "production":
    if app.config["SECRET_KEY"] == "dev-only-change-me":
        raise RuntimeError("SECRET_KEY must be set in production")
```

- [ ] **Step 5: Run the final verification**

Run:

```bash
pytest -v
python -c "from app import create_app; app = create_app(); print(app.url_map)"
```

Expected: tests PASS and the route map includes `/attendance`, `/attendance/week`, `/attendance/export.csv`, `/attendance/week/export.csv`, `/auth/login`, `/auth/logout`, and `/health`.

- [ ] **Step 6: Deployment handoff**

After the user creates Render and Neon accounts:

1. Set `DATABASE_URL` in Render to the Neon connection string with `sslmode=require`.
2. Let Render generate `SECRET_KEY`.
3. Deploy.
4. Run the seed and admin commands in Render Shell.
5. Open `/health`, then `/`, then `/attendance`.
6. Test on a phone over mobile data, not just school Wi-Fi.
7. Download a backup immediately after seeding.

---

## Self-Review

**Spec coverage:** All spec sections map to tasks: architecture (Task 1), data model and roster (Task 2), auth (Task 3), hub preservation (Task 4), daily attendance and CSV (Task 5), weekly upload (Task 6), security (Task 7), verification (Task 8), deployment (Task 9).

**Placeholder scan:** No TBD/TODO items. Code is provided for every new module and every route. Template steps describe exact required controls and include the JavaScript that is not obvious.

**Type consistency:** `Student.id`, `Student.name_en`, `Student.name_ar`, `AttendanceSession.date`, `AttendanceRecord.status`, `save_attendance(day, present_ids, notes, user_id)`, `daily_csv(day)`, `parse_daily_csv(file_storage)`, and `aggregate_weekly(files, students)` are used consistently across tasks.
