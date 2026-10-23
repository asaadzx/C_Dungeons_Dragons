# ---------------------------------------------------------------------------
# app/admin/routes.py
# Staff-only management pages. All routes require login.
# ---------------------------------------------------------------------------

import re

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import bp
from ..extensions import db
from ..models import (
    Announcement,
    AttendanceAudit,
    Event,
    EventRequest,
    LhrGame,
    Meme,
    Student,
    TedTalk,
)

CLASS_NEWS_CATEGORY = "Class News"


def _extract_youtube_id(url):
    if not url:
        return None
    patterns = [
        r"(?:v=|\/vi\/|youtu\.be\/|\/embed\/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


@bp.route("/admin")
@login_required
def index():
    # Class news is stored as announcements with a fixed category.
    class_news = (
        Announcement.query.filter_by(category=CLASS_NEWS_CATEGORY)
        .order_by(Announcement.created_at.desc())
        .all()
    )
    events = Event.query.order_by(Event.id.desc()).all()
    join_requests = EventRequest.query.order_by(EventRequest.id.desc()).all()
    return render_template(
        "admin/index.html",
        announcements=Announcement.query.order_by(Announcement.created_at.desc()).all(),
        class_news=class_news,
        class_news_category=CLASS_NEWS_CATEGORY,
        events=events,
        students=Student.query.filter_by(active=True).order_by(Student.name_en).all(),
        join_requests=join_requests,
        games=LhrGame.query.order_by(LhrGame.id).all(),
        memes=Meme.query.order_by(Meme.id.desc()).all(),
        ted_talks=TedTalk.query.order_by(TedTalk.id.desc()).all(),
        audits=AttendanceAudit.query.order_by(AttendanceAudit.created_at.desc()).limit(20).all(),
    )


@bp.route("/admin/announcement", methods=["POST"])
@login_required
def add_announcement():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    category = request.form.get("category", "News").strip() or "News"
    if not title or not content:
        flash("Title and content are required.", "error")
        return redirect(url_for("admin.index"))
    db.session.add(Announcement(title=title[:200], content=content, category=category[:20]))
    db.session.commit()
    flash("Announcement added.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/announcement/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_announcement(item_id):
    item = db.session.get(Announcement, item_id)
    if not item:
        flash("Announcement not found.", "error")
        return redirect(url_for("admin.index"))
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    category = request.form.get("category", "News").strip() or "News"
    if not title or not content:
        flash("Title and content are required.", "error")
        return redirect(url_for("admin.index"))
    item.title = title[:200]
    item.content = content
    item.category = category[:20]
    db.session.commit()
    flash("Announcement updated.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/announcement/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_announcement(item_id):
    item = db.session.get(Announcement, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Announcement deleted.", "success")
    else:
        flash("Announcement not found.", "error")
    return redirect(url_for("admin.index"))


@bp.route("/admin/lhr", methods=["POST"])
@login_required
def add_lhr():
    title = request.form.get("title", "").strip()
    rules = request.form.get("rules", "").strip()
    if not title or not rules:
        flash("Game title and rules are required.", "error")
        return redirect(url_for("admin.index"))
    try:
        max_players = int(request.form.get("max_players") or 8)
    except ValueError:
        max_players = 8
    status = request.form.get("status", "Upcoming").strip() or "Upcoming"
    db.session.add(LhrGame(title=title[:200], rules=rules, max_players=max_players, status=status[:20]))
    db.session.commit()
    flash("LHR game added.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/lhr/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_lhr(item_id):
    item = db.session.get(LhrGame, item_id)
    if not item:
        flash("Game not found.", "error")
        return redirect(url_for("admin.index"))
    title = request.form.get("title", "").strip()
    rules = request.form.get("rules", "").strip()
    if not title or not rules:
        flash("Game title and rules are required.", "error")
        return redirect(url_for("admin.index"))
    try:
        max_players = int(request.form.get("max_players") or item.max_players)
    except ValueError:
        max_players = item.max_players
    status = request.form.get("status", item.status).strip() or item.status
    item.title = title[:200]
    item.rules = rules
    item.max_players = max_players
    item.status = status[:20]
    db.session.commit()
    flash("LHR game updated.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/lhr/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_lhr(item_id):
    item = db.session.get(LhrGame, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("LHR game deleted.", "success")
    else:
        flash("Game not found.", "error")
    return redirect(url_for("admin.index"))


@bp.route("/admin/meme", methods=["POST"])
@login_required
def add_meme():
    image_url = request.form.get("image_url", "").strip()
    caption = request.form.get("caption", "").strip()
    if not image_url:
        flash("Image URL or filename is required.", "error")
        return redirect(url_for("admin.index"))
    db.session.add(Meme(image_url=image_url[:300], caption=caption))
    db.session.commit()
    flash("Meme added.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/meme/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_meme(item_id):
    item = db.session.get(Meme, item_id)
    if not item:
        flash("Meme not found.", "error")
        return redirect(url_for("admin.index"))
    image_url = request.form.get("image_url", "").strip()
    caption = request.form.get("caption", "").strip()
    if not image_url:
        flash("Image URL or filename is required.", "error")
        return redirect(url_for("admin.index"))
    item.image_url = image_url[:300]
    item.caption = caption
    db.session.commit()
    flash("Meme updated.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/meme/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_meme(item_id):
    item = db.session.get(Meme, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Meme deleted.", "success")
    else:
        flash("Meme not found.", "error")
    return redirect(url_for("admin.index"))


@bp.route("/admin/ted", methods=["POST"])
@login_required
def add_ted():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    thumbnail = request.form.get("thumbnail", "").strip()
    description = request.form.get("description", "").strip()
    if not title or not url:
        flash("Title and URL are required.", "error")
        return redirect(url_for("admin.index"))
    video_id = _extract_youtube_id(url)
    if video_id and not thumbnail:
        thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    elif not thumbnail:
        thumbnail = "images/ted-placeholder.png"
    db.session.add(TedTalk(title=title[:300], url=url[:500], thumbnail=thumbnail[:300], description=description))
    db.session.commit()
    flash("Video for Knowledge added.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/ted/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_ted(item_id):
    item = db.session.get(TedTalk, item_id)
    if not item:
        flash("Video not found.", "error")
        return redirect(url_for("admin.index"))
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    thumbnail = request.form.get("thumbnail", "").strip()
    description = request.form.get("description", "").strip()
    if not title or not url:
        flash("Title and URL are required.", "error")
        return redirect(url_for("admin.index"))
    item.title = title[:300]
    item.url = url[:500]
    item.description = description
    if thumbnail:
        item.thumbnail = thumbnail[:300]
    else:
        video_id = _extract_youtube_id(url)
        if video_id:
            item.thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        elif not item.thumbnail:
            item.thumbnail = "images/ted-placeholder.png"
    db.session.commit()
    flash("Video for Knowledge updated.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/ted/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_ted(item_id):
    item = db.session.get(TedTalk, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Video for Knowledge deleted.", "success")
    else:
        flash("Video not found.", "error")
    return redirect(url_for("admin.index"))


# ---------------------------------------------------------------------------
# Class News
# Class news is simply an announcement in the "Class News" category. These
# routes make it possible to manage that section from the staff panel.
# ---------------------------------------------------------------------------

@bp.route("/admin/class-news", methods=["POST"])
@login_required
def add_class_news():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title or not content:
        flash("Title and content are required.", "error")
        return redirect(url_for("admin.index"))
    db.session.add(
        Announcement(
            title=title[:200], content=content, category=CLASS_NEWS_CATEGORY
        )
    )
    db.session.commit()
    flash("Class news added.", "success")
    return redirect(url_for("admin.index"))


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def _parse_date(value):
    """Parse an ISO date string, returning None when invalid or empty."""
    from datetime import date

    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@bp.route("/admin/event/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_event(item_id):
    item = db.session.get(Event, item_id)
    if not item:
        flash("Event not found.", "error")
        return redirect(url_for("admin.index"))

    title = request.form.get("title", "").strip()
    if not title:
        flash("Event title is required.", "error")
        return redirect(url_for("admin.index"))

    # Only accept a real student as organizer.
    organizer_id = request.form.get("organizer_id", "").strip()
    if organizer_id.isdigit() and db.session.get(Student, int(organizer_id)):
        item.organizer_id = int(organizer_id)

    item.title = title[:200]
    item.link = request.form.get("link", "").strip()[:500]
    item.description = request.form.get("description", "").strip()
    item.location = request.form.get("location", "").strip()[:200]
    item.event_date_actual = _parse_date(request.form.get("event_date_actual"))
    item.event_date = request.form.get("event_date", "").strip()[:100]
    db.session.commit()
    flash("Event updated.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/event/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_event(item_id):
    item = db.session.get(Event, item_id)
    if item:
        # Remove join requests first so the foreign key stays valid.
        EventRequest.query.filter_by(event_id=item_id).delete()
        db.session.delete(item)
        db.session.commit()
        flash("Event deleted.", "success")
    else:
        flash("Event not found.", "error")
    return redirect(url_for("admin.index"))


# ---------------------------------------------------------------------------
# Event join requests (approve / decline / delete)
# ---------------------------------------------------------------------------

@bp.route("/admin/join/<int:item_id>/<status>", methods=["POST"])
@login_required
def set_join_status(item_id, status):
    item = db.session.get(EventRequest, item_id)
    if not item:
        flash("Request not found.", "error")
        return redirect(url_for("admin.index"))
    if status not in {"pending", "approved", "declined"}:
        flash("Unknown status.", "error")
        return redirect(url_for("admin.index"))
    item.status = status
    db.session.commit()
    flash(f"Request marked {status}.", "success")
    return redirect(url_for("admin.index"))


@bp.route("/admin/join/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_join(item_id):
    item = db.session.get(EventRequest, item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Request deleted.", "success")
    else:
        flash("Request not found.", "error")
    return redirect(url_for("admin.index"))
