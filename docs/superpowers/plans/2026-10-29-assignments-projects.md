# Assignments and Projects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add public Assignments and Projects pages with staff-managed lectures, checklists, links, and project cards.

**Architecture:** Extend the existing Flask app with three SQLAlchemy models, public hub routes, and staff CRUD routes. Assignments are grouped into date tabs by query string; no JavaScript tabs are needed. Staff-entered links are validated with the existing `safe_url` helper.

**Tech Stack:** Flask, SQLAlchemy, Flask-Migrate/Alembic, Jinja, NES.css, pytest.

## Global Constraints

- No student accounts, submissions, completion tracking, voting, or rich text.
- Public pages require no login.
- All staff management routes require login.
- Links must be absolute `http`/`https` URLs; invalid links are rejected on save and never rendered as anchors.
- Checklist items are read-only for visitors.
- No new JavaScript dependency.
- Work in `.worktrees/assignments-projects`; use the parent venv:
  `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python`
- Run tests with:
  `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest -q`

---

### Task 1: Data model and migration

**Files:**
- Modify: `app/models.py`
- Create: `migrations/versions/1e043007060e_add_lectures_and_projects.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `Lecture(id, date, title, position, created_at)`, `Lecture.items`
- Produces: `LectureItem(id, lecture_id, text, url, position)`, `LectureItem.lecture`
- Produces: `Project(id, title, description, url, position, created_at)`

- [ ] **Step 1: Write the failing model test**

Add to `tests/test_models.py`:

```python
from app.models import Lecture, LectureItem, Project


def test_lecture_items_cascade_and_project_round_trip(app):
    with app.app_context():
        lecture = Lecture(date=date(2026, 10, 29), title="Databases")
        lecture.items.append(
            LectureItem(text="Read chapter 1", url="https://example.com/ch1")
        )
        project = Project(title="Robot", description="Build a robot")
        db.session.add_all([lecture, project])
        db.session.commit()

        assert lecture.items[0].text == "Read chapter 1"

        db.session.delete(lecture)
        db.session.commit()
        assert LectureItem.query.count() == 0
        assert Project.query.one().title == "Robot"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest tests/test_models.py::test_lecture_items_cascade_and_project_round_trip -q`

Expected: FAIL with `ImportError` for `Lecture`, `LectureItem`, or `Project`.

- [ ] **Step 3: Add the models**

Append to `app/models.py`:

```python
class Lecture(db.Model):
    """A lecture note group shown under one day on the Assignments page."""

    __tablename__ = "lectures"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    items = db.relationship(
        "LectureItem",
        back_populates="lecture",
        cascade="all, delete-orphan",
        order_by="LectureItem.position, LectureItem.id",
        lazy="selectin",
    )


class LectureItem(db.Model):
    """One read-only checklist item inside a lecture card."""

    __tablename__ = "lecture_items"

    id = db.Column(db.Integer, primary_key=True)
    lecture_id = db.Column(db.Integer, db.ForeignKey("lectures.id"), nullable=False)
    text = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=0)

    lecture = db.relationship("Lecture", back_populates="items")


class Project(db.Model):
    """A simple project card shown on the Projects page."""

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    url = db.Column(db.String(500), nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
```

- [ ] **Step 4: Add the migration**

Create `migrations/versions/1e043007060e_add_lectures_and_projects.py`:

```python
"""add lectures and projects

Revision ID: 1e043007060e
Revises: 7c256e11f12e
Create Date: 2026-10-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "1e043007060e"
down_revision = "7c256e11f12e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lectures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lectures_date"), "lectures", ["date"], unique=False)

    op.create_table(
        "lecture_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lecture_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lecture_id"], ["lectures.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("projects")
    op.drop_table("lecture_items")
    op.drop_index(op.f("ix_lectures_date"), table_name="lectures")
    op.drop_table("lectures")
```

- [ ] **Step 5: Verify the migration applies**

Run:

```bash
rm -f /tmp/opencode/assignments-projects-migration.db
DATABASE_URL=sqlite:////tmp/opencode/assignments-projects-migration.db \
  /home/asaad/Documents/MyStuff/C!_Dungeons_\&_Dragons/c1_ras_hub/.venv/bin/python \
  -m flask --app wsgi db upgrade
```

Expected: exit code 0 and an `upgrade` log ending at `1e043007060e`.

- [ ] **Step 6: Run the model test**

Run: `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest tests/test_models.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/models.py migrations/versions/1e043007060e_add_lectures_and_projects.py tests/test_models.py
git commit -m "feat: add lecture and project models"
```

---

### Task 2: Public Assignments and Projects pages

**Files:**
- Modify: `app/hub/routes.py`
- Modify: `app/templates/base.html`
- Modify: `app/i18n.py`
- Modify: `app/static/css/style.css`
- Create: `app/templates/assignments.html`
- Create: `app/templates/projects.html`
- Test: `tests/test_assignments_projects.py`

**Interfaces:**
- Consumes: `Lecture`, `Lecture.items`, `Project`
- Produces: `GET /assignments`, `GET /assignments?date=YYYY-MM-DD`, `GET /projects`
- Produces: endpoint names `hub.assignments`, `hub.projects`

- [ ] **Step 1: Write the failing public tests**

Create `tests/test_assignments_projects.py`:

```python
from datetime import date

from app.extensions import db
from app.models import Lecture, LectureItem, Project


def test_assignments_show_newest_date_and_tabs(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Lecture(date=date(2026, 10, 1), title="Old lecture"),
                Lecture(date=date(2026, 10, 29), title="New lecture"),
            ]
        )
        db.session.commit()

    page = client.get("/assignments").data.decode()
    assert "New lecture" in page
    assert "Old lecture" not in page
    assert "01 Oct 2026" in page
    assert "29 Oct 2026" in page
    assert 'href="/assignments?date=2026-10-01"' in page


def test_assignments_date_query_selects_day(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Lecture(date=date(2026, 10, 1), title="Old lecture"),
                Lecture(date=date(2026, 10, 29), title="New lecture"),
            ]
        )
        db.session.commit()

    page = client.get("/assignments?date=2026-10-01").data.decode()
    assert "Old lecture" in page
    assert "New lecture" not in page


def test_assignments_render_ordered_items_and_safe_links(client, app):
    with app.app_context():
        lecture = Lecture(date=date(2026, 10, 29), title="Databases")
        lecture.items = [
            LectureItem(text="Second", position=2),
            LectureItem(
                text="First",
                url="https://example.com/notes",
                position=1,
            ),
        ]
        db.session.add(lecture)
        db.session.commit()

    page = client.get("/assignments").data.decode()
    assert page.index("First") < page.index("Second")
    assert 'href="https://example.com/notes"' in page
    assert 'target="_blank"' in page


def test_assignments_do_not_render_unsafe_links(client, app):
    with app.app_context():
        lecture = Lecture(date=date(2026, 10, 29), title="Safety")
        lecture.items = [LectureItem(text="Bad link", url="javascript:alert(1)")]
        db.session.add(lecture)
        db.session.commit()

    page = client.get("/assignments").data.decode()
    assert "Bad link" in page
    assert "javascript:" not in page


def test_projects_render_cards_and_safe_links(client, app):
    with app.app_context():
        db.session.add_all(
            [
                Project(
                    title="Robot",
                    description="Build a robot",
                    url="https://example.com/robot",
                    position=1,
                ),
                Project(title="Game", description="Make a game", position=2),
            ]
        )
        db.session.commit()

    page = client.get("/projects").data.decode()
    assert "Robot" in page
    assert "Build a robot" in page
    assert 'href="https://example.com/robot"' in page
    assert "Make a game" in page


def test_projects_do_not_render_unsafe_links(client, app):
    with app.app_context():
        db.session.add(Project(title="Bad", url="javascript:alert(1)"))
        db.session.commit()

    page = client.get("/projects").data.decode()
    assert "Bad" in page
    assert "javascript:" not in page
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest tests/test_assignments_projects.py -q`

Expected: FAIL with 404 responses for `/assignments` and `/projects`.

- [ ] **Step 3: Add the public routes**

Modify `app/hub/routes.py` imports to include `Lecture` and `Project`:

```python
from ..models import (
    Announcement,
    Event,
    EventRequest,
    Lecture,
    LhrGame,
    Meme,
    Project,
    Student,
    TedTalk,
)
```

Add after `student_profile()`:

```python
@bp.route("/assignments")
def assignments():
    """Lecture notes grouped by day, with the newest day selected by default."""
    lectures = Lecture.query.order_by(
        Lecture.date.desc(), Lecture.position.asc(), Lecture.id.asc()
    ).all()
    dates = sorted({lecture.date for lecture in lectures}, reverse=True)

    selected = None
    requested = (request.args.get("date") or "").strip()
    if requested:
        try:
            requested_date = date.fromisoformat(requested)
        except ValueError:
            requested_date = None
        if requested_date in dates:
            selected = requested_date
    if selected is None and dates:
        selected = dates[0]

    day_lectures = (
        [lecture for lecture in lectures if lecture.date == selected] if selected else []
    )
    return render_template(
        "assignments.html",
        dates=dates,
        selected=selected,
        lectures=day_lectures,
    )


@bp.route("/projects")
def projects():
    """Project cards ordered by staff-defined position."""
    return render_template(
        "projects.html",
        projects=Project.query.order_by(Project.position.asc(), Project.id.asc()).all(),
    )
```

- [ ] **Step 4: Add the public templates**

Create `app/templates/assignments.html`:

```html
{% extends 'base.html' %}

{% block content %}

<h2 class="page-title">&#128218; Assignments</h2>
<p class="page-subtitle">Lecture notes and checklists by day.</p>

{% if dates %}
    <div class="tab-row">
        {% for day in dates %}
            <a class="nes-btn {% if day == selected %}is-primary{% else %}is-warning{% endif %}"
               href="{{ url_for('hub.assignments', date=day.isoformat()) }}">
                {{ day.strftime('%d %b %Y') }}
            </a>
        {% endfor %}
    </div>

    <div class="cards-grid mt-2">
        {% for lecture in lectures %}
            <section class="nes-container with-title is-rounded">
                <p class="title">{{ lecture.title }}</p>
                {% if lecture.items %}
                    <ul class="nes-list is-circle">
                        {% for item in lecture.items %}
                            {% set link = item.url|safe_url %}
                            <li>
                                {% if link %}
                                    <a href="{{ link }}" target="_blank" rel="noopener">{{ item.text }}</a>
                                {% else %}
                                    {{ item.text }}
                                {% endif %}
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <p>No checklist items yet.</p>
                {% endif %}
            </section>
        {% else %}
            <section class="nes-container is-rounded">
                <p>No lectures for this day.</p>
            </section>
        {% endfor %}
    </div>
{% else %}
    <section class="nes-container is-rounded">
        <p>No lectures have been added yet.</p>
    </section>
{% endif %}

{% endblock %}
```

Create `app/templates/projects.html`:

```html
{% extends 'base.html' %}

{% block content %}

<h2 class="page-title">&#128640; Projects</h2>
<p class="page-subtitle">Class projects and useful links.</p>

<div class="cards-grid">
    {% for project in projects %}
        <section class="nes-container is-rounded">
            <h3>{{ project.title }}</h3>
            {% if project.description %}
                <p>{{ project.description }}</p>
            {% endif %}
            {% set link = project.url|safe_url %}
            {% if link %}
                <a class="nes-btn is-primary" href="{{ link }}"
                   target="_blank" rel="noopener">Open project</a>
            {% endif %}
        </section>
    {% else %}
        <section class="nes-container is-rounded">
            <p>No projects have been added yet.</p>
        </section>
    {% endfor %}
</div>

{% endblock %}
```

- [ ] **Step 5: Add navigation, translations, and tab styles**

In `app/templates/base.html`, add after the News link:

```html
<a href="{{ url_for('hub.assignments') }}" class="nes-btn is-warning">{{ t('nav.assignments') }}</a>
<a href="{{ url_for('hub.projects') }}" class="nes-btn is-error">{{ t('nav.projects') }}</a>
```

In `app/i18n.py`, add after `nav.news`:

```python
"nav.assignments": {"en": "Assignments", "ar": "الواجبات"},
"nav.projects": {"en": "Projects", "ar": "المشاريع"},
```

In `app/static/css/style.css`, add under `/* Utility */`:

```css
.tab-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
```

- [ ] **Step 6: Run the public tests**

Run: `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest tests/test_assignments_projects.py -q`

Expected: PASS for the six public tests.

- [ ] **Step 7: Commit**

```bash
git add app/hub/routes.py app/templates/assignments.html app/templates/projects.html \
  app/templates/base.html app/i18n.py app/static/css/style.css \
  tests/test_assignments_projects.py
git commit -m "feat: add public assignments and projects pages"
```

---

### Task 3: Staff management for lectures, checklist items, and projects

**Files:**
- Modify: `app/admin/routes.py`
- Modify: `app/templates/admin/index.html`
- Create: `app/templates/admin/assignments.html`
- Create: `app/templates/admin/projects.html`
- Test: `tests/test_assignments_projects.py`

**Interfaces:**
- Consumes: `Lecture`, `LectureItem`, `Project`, `safe_url`
- Produces: `GET /admin/assignments`, `GET /admin/projects`
- Produces: `POST /admin/assignments/lecture`, `/lecture/<id>/edit`, `/lecture/<id>/delete`
- Produces: `POST /admin/assignments/item`, `/item/<id>/edit`, `/item/<id>/delete`
- Produces: `POST /admin/project`, `/project/<id>/edit`, `/project/<id>/delete`

- [ ] **Step 1: Write the failing admin tests**

Append to `tests/test_assignments_projects.py`:

```python
import re

from app.models import User


def _login(client, app):
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
    return token


def test_assignment_admin_requires_login(client):
    assert client.get("/admin/assignments").status_code == 302
    assert client.get("/admin/projects").status_code == 302


def test_assignment_admin_crud(client, app):
    token = _login(client, app)
    client.post(
        "/admin/assignments/lecture",
        data={
            "csrf_token": token,
            "date": "2026-10-29",
            "title": "Databases",
            "position": "1",
        },
    )
    with app.app_context():
        lecture = Lecture.query.one()
        lecture_id = lecture.id
        assert lecture.title == "Databases"

    client.post(
        "/admin/assignments/item",
        data={
            "csrf_token": token,
            "lecture_id": str(lecture_id),
            "text": "Read chapter 1",
            "url": "https://example.com/ch1",
            "position": "0",
        },
    )
    with app.app_context():
        item = LectureItem.query.one()
        item_id = item.id
        assert item.url == "https://example.com/ch1"

    client.post(
        f"/admin/assignments/item/{item_id}/edit",
        data={"csrf_token": token, "text": "Read chapter 2", "url": "", "position": "2"},
    )
    client.post(
        f"/admin/assignments/lecture/{lecture_id}/edit",
        data={
            "csrf_token": token,
            "date": "2026-10-30",
            "title": "Databases II",
            "position": "0",
        },
    )
    with app.app_context():
        lecture = db.session.get(Lecture, lecture_id)
        item = db.session.get(LectureItem, item_id)
        assert lecture.title == "Databases II"
        assert lecture.date == date(2026, 10, 30)
        assert item.text == "Read chapter 2"
        assert item.url == ""
        assert item.position == 2

    client.post(
        f"/admin/assignments/item/{item_id}/delete", data={"csrf_token": token}
    )
    client.post(
        f"/admin/assignments/lecture/{lecture_id}/delete", data={"csrf_token": token}
    )
    with app.app_context():
        assert Lecture.query.count() == 0
        assert LectureItem.query.count() == 0


def test_project_admin_crud(client, app):
    token = _login(client, app)
    client.post(
        "/admin/project",
        data={
            "csrf_token": token,
            "title": "Robot",
            "description": "Build a robot",
            "url": "https://example.com/robot",
            "position": "1",
        },
    )
    with app.app_context():
        project = Project.query.one()
        project_id = project.id

    client.post(
        f"/admin/project/{project_id}/edit",
        data={
            "csrf_token": token,
            "title": "Robot 2",
            "description": "Build a better robot",
            "url": "",
            "position": "0",
        },
    )
    with app.app_context():
        project = db.session.get(Project, project_id)
        assert project.title == "Robot 2"
        assert project.description == "Build a better robot"
        assert project.url == ""

    client.post(f"/admin/project/{project_id}/delete", data={"csrf_token": token})
    with app.app_context():
        assert Project.query.count() == 0


def test_admin_rejects_invalid_date_and_links(client, app):
    token = _login(client, app)
    client.post(
        "/admin/assignments/lecture",
        data={"csrf_token": token, "date": "not-a-date", "title": "Bad"},
    )
    client.post(
        "/admin/project",
        data={"csrf_token": token, "title": "Bad", "url": "javascript:alert(1)"},
    )
    with app.app_context():
        assert Lecture.query.count() == 0
        assert Project.query.count() == 0
        lecture = Lecture(date=date(2026, 10, 29), title="Valid")
        db.session.add(lecture)
        db.session.commit()
        lecture_id = lecture.id

    client.post(
        "/admin/assignments/item",
        data={
            "csrf_token": token,
            "lecture_id": str(lecture_id),
            "text": "Bad",
            "url": "javascript:alert(1)",
        },
    )
    with app.app_context():
        assert LectureItem.query.count() == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest tests/test_assignments_projects.py -q`

Expected: FAIL with 404 or missing endpoint errors for the admin routes.

- [ ] **Step 3: Add the admin routes**

Update imports at the top of `app/admin/routes.py`:

```python
from datetime import date

from ..models import (
    Announcement,
    AttendanceAudit,
    Event,
    EventRequest,
    Lecture,
    LectureItem,
    LhrGame,
    Meme,
    NewsSource,
    Project,
    Student,
    TedTalk,
)
from ..security import safe_url
```

Add these helpers after `CLASS_NEWS_CATEGORY`:

```python
def _int_or_default(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _form_date(value):
    try:
        return date.fromisoformat((value or "").strip())
    except (TypeError, ValueError):
        return None


def _safe_link(value):
    value = (value or "").strip()
    if not value:
        return ""
    return safe_url(value)
```

Add these routes before `@bp.route("/admin")`:

```python
@bp.route("/admin/assignments")
@login_required
def assignments_index():
    lectures = Lecture.query.order_by(
        Lecture.date.desc(), Lecture.position.asc(), Lecture.id.asc()
    ).all()
    return render_template("admin/assignments.html", lectures=lectures)


@bp.route("/admin/assignments/lecture", methods=["POST"])
@login_required
def add_lecture():
    title = request.form.get("title", "").strip()
    lecture_date = _form_date(request.form.get("date"))
    if not title or lecture_date is None:
        flash("A valid date and lecture title are required.", "error")
        return redirect(url_for("admin.assignments_index"))
    db.session.add(
        Lecture(
            date=lecture_date,
            title=title[:200],
            position=_int_or_default(request.form.get("position")),
        )
    )
    db.session.commit()
    flash("Lecture added.", "success")
    return redirect(url_for("admin.assignments_index"))


@bp.route("/admin/assignments/lecture/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_lecture(item_id):
    item = db.session.get(Lecture, item_id)
    if not item:
        flash("Lecture not found.", "error")
        return redirect(url_for("admin.assignments_index"))
    title = request.form.get("title", "").strip()
    lecture_date = _form_date(request.form.get("date"))
    if not title or lecture_date is None:
        flash("A valid date and lecture title are required.", "error")
        return redirect(url_for("admin.assignments_index"))
    item.date = lecture_date
    item.title = title[:200]
    item.position = _int_or_default(request.form.get("position"), item.position)
    db.session.commit()
    flash("Lecture updated.", "success")
    return redirect(url_for("admin.assignments_index"))


@bp.route("/admin/assignments/lecture/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_lecture(item_id):
    item = db.session.get(Lecture, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Lecture deleted.", "success")
    else:
        flash("Lecture not found.", "error")
    return redirect(url_for("admin.assignments_index"))


@bp.route("/admin/assignments/item", methods=["POST"])
@login_required
def add_lecture_item():
    lecture_id = request.form.get("lecture_id", "").strip()
    lecture = db.session.get(Lecture, int(lecture_id)) if lecture_id.isdigit() else None
    text = request.form.get("text", "").strip()
    link = request.form.get("url", "").strip()
    safe_link = _safe_link(link)
    if lecture is None or not text:
        flash("Lecture and checklist text are required.", "error")
        return redirect(url_for("admin.assignments_index"))
    if link and not safe_link:
        flash("Link must be a full http:// or https:// URL.", "error")
        return redirect(url_for("admin.assignments_index"))
    db.session.add(
        LectureItem(
            lecture_id=lecture.id,
            text=text[:300],
            url=safe_link[:500],
            position=_int_or_default(request.form.get("position")),
        )
    )
    db.session.commit()
    flash("Checklist item added.", "success")
    return redirect(url_for("admin.assignments_index"))


@bp.route("/admin/assignments/item/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_lecture_item(item_id):
    item = db.session.get(LectureItem, item_id)
    if not item:
        flash("Checklist item not found.", "error")
        return redirect(url_for("admin.assignments_index"))
    text = request.form.get("text", "").strip()
    link = request.form.get("url", "").strip()
    safe_link = _safe_link(link)
    if not text:
        flash("Checklist text is required.", "error")
        return redirect(url_for("admin.assignments_index"))
    if link and not safe_link:
        flash("Link must be a full http:// or https:// URL.", "error")
        return redirect(url_for("admin.assignments_index"))
    item.text = text[:300]
    item.url = safe_link[:500]
    item.position = _int_or_default(request.form.get("position"), item.position)
    db.session.commit()
    flash("Checklist item updated.", "success")
    return redirect(url_for("admin.assignments_index"))


@bp.route("/admin/assignments/item/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_lecture_item(item_id):
    item = db.session.get(LectureItem, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Checklist item deleted.", "success")
    else:
        flash("Checklist item not found.", "error")
    return redirect(url_for("admin.assignments_index"))


@bp.route("/admin/projects")
@login_required
def projects_index():
    projects = Project.query.order_by(Project.position.asc(), Project.id.asc()).all()
    return render_template("admin/projects.html", projects=projects)


@bp.route("/admin/project", methods=["POST"])
@login_required
def add_project():
    title = request.form.get("title", "").strip()
    link = request.form.get("url", "").strip()
    safe_link = _safe_link(link)
    if not title:
        flash("Project title is required.", "error")
        return redirect(url_for("admin.projects_index"))
    if link and not safe_link:
        flash("Link must be a full http:// or https:// URL.", "error")
        return redirect(url_for("admin.projects_index"))
    db.session.add(
        Project(
            title=title[:200],
            description=request.form.get("description", "").strip(),
            url=safe_link[:500],
            position=_int_or_default(request.form.get("position")),
        )
    )
    db.session.commit()
    flash("Project added.", "success")
    return redirect(url_for("admin.projects_index"))


@bp.route("/admin/project/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_project(item_id):
    item = db.session.get(Project, item_id)
    if not item:
        flash("Project not found.", "error")
        return redirect(url_for("admin.projects_index"))
    title = request.form.get("title", "").strip()
    link = request.form.get("url", "").strip()
    safe_link = _safe_link(link)
    if not title:
        flash("Project title is required.", "error")
        return redirect(url_for("admin.projects_index"))
    if link and not safe_link:
        flash("Link must be a full http:// or https:// URL.", "error")
        return redirect(url_for("admin.projects_index"))
    item.title = title[:200]
    item.description = request.form.get("description", "").strip()
    item.url = safe_link[:500]
    item.position = _int_or_default(request.form.get("position"), item.position)
    db.session.commit()
    flash("Project updated.", "success")
    return redirect(url_for("admin.projects_index"))


@bp.route("/admin/project/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_project(item_id):
    item = db.session.get(Project, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Project deleted.", "success")
    else:
        flash("Project not found.", "error")
    return redirect(url_for("admin.projects_index"))
```

- [ ] **Step 4: Add the admin templates and links**

Create `app/templates/admin/assignments.html`:

```html
{% extends 'base.html' %}

{% block content %}

<h2 class="page-title">&#128218; Manage Assignments</h2>
<p class="page-subtitle">
    <a class="nes-btn" href="{{ url_for('admin.index') }}">Back to staff panel</a>
</p>

<section class="nes-container with-title is-rounded">
    <p class="title">New Lecture</p>
    <form method="POST" action="{{ url_for('admin.add_lecture') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <label for="lecture-date">Date</label>
        <input class="nes-input" id="lecture-date" type="date" name="date" required>
        <label for="lecture-title" class="mt-1">Title</label>
        <input class="nes-input" id="lecture-title" name="title" required>
        <label for="lecture-position" class="mt-1">Position</label>
        <input class="nes-input" id="lecture-position" type="number" name="position" value="0">
        <button class="nes-btn is-primary mt-1" type="submit">Add lecture</button>
    </form>
</section>

{% for lecture in lectures %}
    <section class="nes-container with-title is-rounded mt-2">
        <p class="title">{{ lecture.date.strftime('%d %b %Y') }}</p>

        <form method="POST" action="{{ url_for('admin.edit_lecture', item_id=lecture.id) }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <div class="grid-2">
                <div>
                    <label>Date</label>
                    <input class="nes-input" type="date" name="date"
                           value="{{ lecture.date.isoformat() }}" required>
                </div>
                <div>
                    <label>Position</label>
                    <input class="nes-input" type="number" name="position"
                           value="{{ lecture.position }}">
                </div>
            </div>
            <label class="mt-1">Title</label>
            <input class="nes-input" name="title" value="{{ lecture.title }}" required>
            <button class="nes-btn is-primary mt-1" type="submit">Save lecture</button>
        </form>

        <form method="POST" action="{{ url_for('admin.delete_lecture', item_id=lecture.id) }}" class="mt-1">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <button class="nes-btn is-error" type="submit">Delete lecture</button>
        </form>

        <h4 class="mt-2">Checklist</h4>
        {% for item in lecture.items %}
            <div class="admin-item">
                <form method="POST" action="{{ url_for('admin.edit_lecture_item', item_id=item.id) }}">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <div class="grid-2">
                        <div>
                            <label>Text</label>
                            <input class="nes-input" name="text" value="{{ item.text }}" required>
                        </div>
                        <div>
                            <label>Position</label>
                            <input class="nes-input" type="number" name="position"
                                   value="{{ item.position }}">
                        </div>
                    </div>
                    <label class="mt-1">Link (optional)</label>
                    <input class="nes-input" name="url" value="{{ item.url }}"
                           placeholder="https://example.com">
                    <button class="nes-btn is-primary mt-1" type="submit">Save item</button>
                </form>
                <form method="POST" action="{{ url_for('admin.delete_lecture_item', item_id=item.id) }}" class="mt-1">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button class="nes-btn is-error" type="submit">Delete item</button>
                </form>
            </div>
        {% else %}
            <p>No checklist items yet.</p>
        {% endfor %}

        <form method="POST" action="{{ url_for('admin.add_lecture_item') }}" class="mt-2">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="lecture_id" value="{{ lecture.id }}">
            <label>New checklist text</label>
            <input class="nes-input" name="text" required>
            <label class="mt-1">Link (optional)</label>
            <input class="nes-input" name="url" placeholder="https://example.com">
            <label class="mt-1">Position</label>
            <input class="nes-input" type="number" name="position" value="0">
            <button class="nes-btn is-success mt-1" type="submit">Add item</button>
        </form>
    </section>
{% else %}
    <section class="nes-container is-rounded mt-2">
        <p>No lectures yet.</p>
    </section>
{% endfor %}

{% endblock %}
```

Create `app/templates/admin/projects.html`:

```html
{% extends 'base.html' %}

{% block content %}

<h2 class="page-title">&#128640; Manage Projects</h2>
<p class="page-subtitle">
    <a class="nes-btn" href="{{ url_for('admin.index') }}">Back to staff panel</a>
</p>

<section class="nes-container with-title is-rounded">
    <p class="title">New Project</p>
    <form method="POST" action="{{ url_for('admin.add_project') }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <label for="project-title">Title</label>
        <input class="nes-input" id="project-title" name="title" required>
        <label for="project-description" class="mt-1">Description</label>
        <textarea class="nes-textarea" id="project-description" name="description"></textarea>
        <label for="project-url" class="mt-1">Link (optional)</label>
        <input class="nes-input" id="project-url" name="url" placeholder="https://example.com">
        <label for="project-position" class="mt-1">Position</label>
        <input class="nes-input" id="project-position" type="number" name="position" value="0">
        <button class="nes-btn is-primary mt-1" type="submit">Add project</button>
    </form>
</section>

{% for project in projects %}
    <section class="nes-container with-title is-rounded mt-2">
        <p class="title">{{ project.title }}</p>
        <form method="POST" action="{{ url_for('admin.edit_project', item_id=project.id) }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <div class="grid-2">
                <div>
                    <label>Title</label>
                    <input class="nes-input" name="title" value="{{ project.title }}" required>
                </div>
                <div>
                    <label>Position</label>
                    <input class="nes-input" type="number" name="position"
                           value="{{ project.position }}">
                </div>
            </div>
            <label class="mt-1">Description</label>
            <textarea class="nes-textarea" name="description">{{ project.description }}</textarea>
            <label class="mt-1">Link (optional)</label>
            <input class="nes-input" name="url" value="{{ project.url }}"
                   placeholder="https://example.com">
            <button class="nes-btn is-primary mt-1" type="submit">Save project</button>
        </form>
        <form method="POST" action="{{ url_for('admin.delete_project', item_id=project.id) }}" class="mt-1">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <button class="nes-btn is-error" type="submit">Delete project</button>
        </form>
    </section>
{% else %}
    <section class="nes-container is-rounded mt-2">
        <p>No projects yet.</p>
    </section>
{% endfor %}

{% endblock %}
```

In `app/templates/admin/index.html`, add after the page subtitle:

```html
<p class="mt-1">
    <a class="nes-btn is-warning" href="{{ url_for('admin.assignments_index') }}">Manage Assignments</a>
    <a class="nes-btn is-success" href="{{ url_for('admin.projects_index') }}">Manage Projects</a>
</p>
```

- [ ] **Step 5: Run the admin tests**

Run: `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest tests/test_assignments_projects.py -q`

Expected: PASS for all public and admin tests.

- [ ] **Step 6: Commit**

```bash
git add app/admin/routes.py app/templates/admin/index.html \
  app/templates/admin/assignments.html app/templates/admin/projects.html \
  tests/test_assignments_projects.py
git commit -m "feat: add staff management for assignments and projects"
```

---

### Task 4: Full verification and handoff

**Files:**
- Verify: all changed files

- [ ] **Step 1: Run the full test suite**

Run: `/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/.venv/bin/python -m pytest -q`

Expected: all tests pass, including the new ones.

- [ ] **Step 2: Run JavaScript lint with the parent node modules**

Run:

```bash
PATH='/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub/node_modules/.bin':$PATH npm run lint:js
```

Expected: exit code 0.

- [ ] **Step 3: Check for whitespace errors and review the branch diff**

Run:

```bash
git diff --check origin/main..HEAD
git diff --stat origin/main..HEAD
git status --short
```

Expected: no whitespace errors; only the intended files changed; clean worktree.

- [ ] **Step 4: Request code review**

Use the `requesting-code-review` skill. Resolve any Critical or Important findings before continuing.

- [ ] **Step 5: Commit any review fixes and push**

```bash
git push -u origin assignments-projects
```

Then open a PR with `gh pr create --base main --head assignments-projects`.
