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
from datetime import datetime

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
    """Home page: announcements plus a random TED talk and meme."""
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


@bp.route("/schedule")
def schedule():
    """Events calendar for the current month.

    Note: event_date is currently free text (e.g. "Fri 21 Nov"), so we pull the
    day number out with a regex. A future milestone should store real dates.
    """
    events, requests_by_event = _events_with_requests()
    students = Student.query.filter_by(active=True).order_by(Student.name_en).all()

    now = datetime.now()
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(now.year, now.month)

    # Group events by day number so the calendar grid can place them.
    events_by_day = {}
    for ev in events:
        matches = re.findall(r"\b(\d{1,2})\b", ev.event_date or "")
        if matches:
            try:
                day = int(matches[-1])
            except ValueError:
                continue
            if 1 <= day <= 31:
                events_by_day.setdefault(day, []).append(ev)

    return render_template(
        "schedule.html",
        events=events,
        requests_by_event=requests_by_event,
        students=students,
        weeks=weeks,
        current_month=now.strftime("%B %Y"),
        today=now.day,
        events_by_day=events_by_day,
    )


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

    db.session.add(
        Event(
            organizer_id=int(organizer_id),
            title=title[:200],
            link=request.form.get("link", "").strip()[:500],
            description=request.form.get("description", "").strip(),
            event_date=request.form.get("event_date", "").strip()[:100],
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
