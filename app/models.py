# ---------------------------------------------------------------------------
# app/models.py
# Every database table as a Python class (SQLAlchemy ORM).
#
# One class = one table. Each Column() = one column. Relationships let us
# navigate between rows in Python (e.g. record.student.name_en).
#
# Tables:
#   User               staff accounts (teacher/admin)
#   Student            the C1 roster (English + Arabic names)
#   AttendanceSession  one attendance record per calendar day
#   AttendanceRecord   one present/absent row per student per day
#   Announcement       bulletin board posts
#   LhrGame            LHR games/activities
#   TedTalk / Meme     KOSEN Spotlight content
#   Event / EventRequest  community events and join requests
# ---------------------------------------------------------------------------

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    """Timezone-aware UTC timestamp. Used as the default for timestamp columns."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """A staff member who can log in (teacher or admin)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    # Only the hash is stored, never the password itself.
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="teacher")
    active = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, password):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Return True if the given password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        # Flask-Login reads this to allow/deny login for disabled accounts.
        return self.active


class Student(db.Model):
    """A class member. English and Arabic names live in separate columns."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(200), nullable=False)
    name_ar = db.Column(db.String(200), nullable=False, default="")
    # Contact fields are optional and empty by default.
    interests = db.Column(db.Text, nullable=False, default="")
    website = db.Column(db.String(300), nullable=False, default="")
    facebook = db.Column(db.String(300), nullable=False, default="")
    instagram = db.Column(db.String(300), nullable=False, default="")
    phone = db.Column(db.String(50), nullable=False, default="")
    email = db.Column(db.String(200), nullable=False, default="")
    # Inactive students stay in the database but are hidden from the app.
    active = db.Column(db.Boolean, nullable=False, default=True)

    # Deleting a student also deletes their attendance rows.
    records = db.relationship(
        "AttendanceRecord", back_populates="student", cascade="all, delete-orphan"
    )


class AttendanceSession(db.Model):
    """One attendance sheet for one calendar day (unique per date)."""

    __tablename__ = "attendance_sessions"
    __table_args__ = (db.UniqueConstraint("date", name="uq_attendance_session_date"),)

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # selectin loads all records efficiently when a session is fetched.
    records = db.relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AttendanceRecord(db.Model):
    """One student's present/absent result for one day."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        # A student can only appear once per session.
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
    """A post on the Official Bulletin."""

    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(20), nullable=False, default="News")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class LhrGame(db.Model):
    """A game or activity in the LHR center."""

    __tablename__ = "lhr_games"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    rules = db.Column(db.Text, nullable=False)
    max_players = db.Column(db.Integer, nullable=False, default=4)
    status = db.Column(db.String(20), nullable=False, default="Upcoming")


class TedTalk(db.Model):
    """A TED talk shown randomly in the KOSEN Spotlight."""

    __tablename__ = "ted_talks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    thumbnail = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)


class Meme(db.Model):
    """A meme shown randomly in the KOSEN Spotlight."""

    __tablename__ = "memes"

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.Text, nullable=False)


class Event(db.Model):
    """A community event posted by a student."""

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    link = db.Column(db.String(500), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    # Real calendar date used for sorting and grid placement.
    event_date_actual = db.Column(db.Date, nullable=True, index=True)
    # Free-text date for display, e.g. "Fri 21 Nov".
    event_date = db.Column(db.String(100), nullable=False, default="")
    location = db.Column(db.String(200), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    organizer = db.relationship("Student")


class EventRequest(db.Model):
    """An "ask to go with them" request made on an event."""

    __tablename__ = "event_requests"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    requester_name = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False, default="")
    # Staff can approve or decline a request: pending / approved / declined.
    status = db.Column(db.String(20), nullable=False, default="pending")
    # Reserved for a future student login system; NULL for now.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    event = db.relationship("Event")


class NewsSource(db.Model):
    """An RSS feed shown on the Global News page.

    Staff can edit this list from the control panel. The rows are seeded
    from the defaults in app/news/feeds.py the first time they are needed.
    """

    __tablename__ = "news_sources"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    # Disabled feeds stay in the panel but are not fetched.
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class AttendanceAudit(db.Model):
    """Audit log for attendance changes."""

    __tablename__ = "attendance_audits"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_sessions.id"), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False, default="save")
    day = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


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
