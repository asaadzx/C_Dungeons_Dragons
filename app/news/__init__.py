# ---------------------------------------------------------------------------
# app/news/__init__.py
# The "News" area: class news (written by staff) and global news (pulled from
# public RSS feeds). Kept in its own blueprint so the feed fetching and cache
# logic stay separate from the rest of the hub.
# ---------------------------------------------------------------------------

from flask import Blueprint

bp = Blueprint("news", __name__)

from . import routes  # noqa: F401, E402
