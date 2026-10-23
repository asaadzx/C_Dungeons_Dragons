# ---------------------------------------------------------------------------
# app/admin/__init__.py
# Staff-only management pages.
# ---------------------------------------------------------------------------

from flask import Blueprint

bp = Blueprint("admin", __name__)

from . import routes  # noqa: F401, E402
