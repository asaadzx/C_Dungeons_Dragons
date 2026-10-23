# ---------------------------------------------------------------------------
# app/news/routes.py
# The /news page: class news written by staff plus global news from RSS.
# ---------------------------------------------------------------------------

from flask import render_template, request

from . import bp
from .feeds import get_global_news
from ..models import Announcement

# Announcements in this category are shown as "Class News".
CLASS_NEWS_CATEGORY = "Class News"


@bp.route("/news")
def index():
    """Show class news and global news side by side."""
    # Staff-written class news: announcements tagged with the Class News
    # category, newest first.
    class_news = (
        Announcement.query.filter_by(category=CLASS_NEWS_CATEGORY)
        .order_by(Announcement.created_at.desc())
        .all()
    )

    # Add ?refresh=1 to bypass the 15-minute RSS cache (handy for demos).
    force = request.args.get("refresh") == "1"
    global_news = get_global_news(force=force)

    return render_template(
        "news.html",
        class_news=class_news,
        global_news=global_news,
        class_news_category=CLASS_NEWS_CATEGORY,
    )
