# ---------------------------------------------------------------------------
# app/hub/__init__.py
# The hub blueprint: all the public pages (bulletin, games, directory, events).
# ---------------------------------------------------------------------------

from flask import Blueprint

bp = Blueprint("hub", __name__)

from . import routes  # noqa: E402,F401
