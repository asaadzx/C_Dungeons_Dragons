# ---------------------------------------------------------------------------
# app/admin/routes.py
# Staff-only management pages. All routes require login.
# ---------------------------------------------------------------------------

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import bp
from ..extensions import db
from ..models import Announcement, LhrGame, Meme, TedTalk


def _require_staff():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    return None


@bp.route("/admin")
@login_required
def index():
    return render_template(
        "admin/index.html",
        announcements=Announcement.query.order_by(Announcement.created_at.desc()).all(),
        games=LhrGame.query.order_by(LhrGame.id).all(),
        memes=Meme.query.order_by(Meme.id.desc()).all(),
        ted_talks=TedTalk.query.order_by(TedTalk.id.desc()).all(),
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
    if not thumbnail:
        thumbnail = "images/ted-placeholder.png"
    db.session.add(TedTalk(title=title[:300], url=url[:500], thumbnail=thumbnail[:300], description=description))
    db.session.commit()
    flash("TED talk added.", "success")
    return redirect(url_for("admin.index"))
