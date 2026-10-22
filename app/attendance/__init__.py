# ---------------------------------------------------------------------------
# app/attendance/__init__.py
# The attendance blueprint: daily checklist, CSV export and weekly report.
# ---------------------------------------------------------------------------

from flask import Blueprint

bp = Blueprint("attendance", __name__)

from . import routes  # noqa: E402,F401
