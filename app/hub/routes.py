# ---------------------------------------------------------------------------
# app/hub/routes.py
# All the public pages of the hub:
#   /                     Bulletin + random KOSEN Spotlight
#   /lhr, /lhr/game/<id>  LHR games
#   /directory            Student directory
#   /student/<id>         One student's profile + their events
#   /schedule             Community events calendar
#   /schedule/add         Post an event (staff only)
#   /event/<id>/join      Ask to go to an event (public)
#
# Data now comes from the SQLAlchemy models instead of raw SQLite.
# ---------------------------------------------------------------------------

import calendar
import re
from datetime import date, datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from . import bp
from ..extensions import db
from ..models import (
    Announcement,
    Event,
    EventRequest,
    LhrGame,
    Meme,
    Student,
    TedTalk,
)


def _random_row(model):
    """Return one random row from a table (used for the KOSEN Spotlight)."""
    return model.query.order_by(db.func.random()).first()


def _events_with_requests():
    """Return (events, {event_id: [requests]}) for the events board."""
    events = Event.query.order_by(Event.id.desc()).all()
    requests = EventRequest.query.order_by(EventRequest.id.asc()).all()

    requests_by_event = {}
    for item in requests:
        requests_by_event.setdefault(item.event_id, []).append(item)
    return events, requests_by_event


@bp.route("/")
def index():
    """Home page: announcements plus a random video and meme."""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template(
        "index.html",
        announcements=announcements,
        ted_talk=_random_row(TedTalk),
        meme=_random_row(Meme),
    )


@bp.route("/lhr")
def lhr():
    """List every LHR game/activity."""
    return render_template("lhr.html", lhr_games=LhrGame.query.order_by(LhrGame.id).all())


@bp.route("/lhr/game/<int:game_id>")
def game_detail(game_id):
    """Detail page for one game. Unknown ids fall back to the list."""
    game = db.session.get(LhrGame, game_id)
    if game is None:
        return redirect(url_for("hub.lhr"))
    return render_template("game_detail.html", game=game)


@bp.route("/directory")
def directory():
    """Student directory: every active student as a card."""
    students = Student.query.filter_by(active=True).order_by(Student.name_en).all()
    return render_template("directory.html", students=students)


@bp.route("/student/<int:student_id>")
def student_profile(student_id):
    """One student's profile, plus the events they organised."""
    student = db.session.get(Student, student_id)
    if student is None:
        return redirect(url_for("hub.directory"))

    events = Event.query.filter_by(organizer_id=student_id).order_by(Event.id.desc()).all()
    return render_template("profile.html", student=student, events=events)


def _shift_month(year, month, delta):
    """Return (year, month) moved by delta months, wrapping across years."""
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


@bp.route("/schedule")
def schedule():
    """Events calendar for a chosen month (defaults to the current month).

    Query params ?year=YYYY&month=M select the visible month. Events are
    placed using their real calendar date; older events that only have free
    text are best-effort matched by day number.
    """
    events, requests_by_event = _events_with_requests()
    students = Student.query.filter_by(active=True).order_by(Student.name_en).all()

    now = datetime.now()

    # Parse the requested month, falling back to the current month.
    try:
        year = int(request.args.get("year", now.year))
        month = int(request.args.get("month", now.month))
        if not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        year, month = now.year, now.month

    view_year, view_month = year, month
    prev_year, prev_month = _shift_month(view_year, view_month, -1)
    next_year, next_month = _shift_month(view_year, view_month, 1)

    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(view_year, view_month)

    # Group events by day number so the calendar grid can place them.
    events_by_day = {}
    for ev in events:
        day = None
        actual = getattr(ev, "event_date_actual", None)
        if actual and actual.month == view_month and actual.year == view_year:
            day = actual.day
        elif actual is None:
            # Legacy free-text events: only guess for the current month.
            if view_year == now.year and view_month == now.month:
                matches = re.findall(r"\b(\d{1,2})\b", ev.event_date or "")
                if matches:
                    try:
                        candidate = int(matches[-1])
                    except ValueError:
                        candidate = None
                    if candidate and 1 <= candidate <= 31:
                        day = candidate
        if day:
            events_by_day.setdefault(day, []).append(ev)

    is_current_month = view_year == now.year and view_month == now.month

    return render_template(
        "schedule.html",
        events=events,
        requests_by_event=requests_by_event,
        students=students,
        weeks=weeks,
        current_month=datetime(view_year, view_month, 1).strftime("%B %Y"),
        today=now.day,
        is_current_month=is_current_month,
        events_by_day=events_by_day,
        prev_month=datetime(prev_year, prev_month, 1),
        next_month=datetime(next_year, next_month, 1),
    )


def _parse_event_date(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@bp.route("/schedule/add", methods=["POST"])
@login_required
def add_event():
    """Post a new event. Staff only, since events appear publicly."""
    organizer_id = request.form.get("organizer_id", "").strip()
    title = request.form.get("title", "").strip()
    if not organizer_id or not title:
        flash("Please choose an organizer and enter an event title.", "error")
        return redirect(url_for("hub.schedule"))

    # The organizer must be a real student, otherwise the foreign key breaks.
    if db.session.get(Student, int(organizer_id)) is None:
        flash("That organizer does not exist.", "error")
        return redirect(url_for("hub.schedule"))

    event_date_actual = _parse_event_date(request.form.get("event_date_actual"))
    event_date_display = request.form.get("event_date", "").strip()[:100]
    if event_date_actual and not event_date_display:
        event_date_display = event_date_actual.strftime("%a %d %b")

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
    db.session.commit()
    flash("Event added to the board!", "success")
    return redirect(url_for("hub.schedule"))


@bp.route("/event/<int:event_id>/join", methods=["POST"])
def join_event(event_id):
    """Public "ask to go with them" request for an event."""
    if db.session.get(Event, event_id) is None:
        flash("That event no longer exists.", "error")
        return redirect(url_for("hub.schedule"))

    name = request.form.get("requester_name", "").strip()
    if not name:
        flash("Please type your name so they know who wants to join.", "error")
        return redirect(url_for("hub.schedule", _anchor=f"event-{event_id}"))

    db.session.add(
        EventRequest(
            event_id=event_id,
            requester_name=name[:200],
            message=request.form.get("message", "").strip(),
        )
    )
    db.session.commit()
    flash("Request sent! The organizer can see you want to go.", "success")
    return redirect(url_for("hub.schedule", _anchor=f"event-{event_id}"))
