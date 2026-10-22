# ---------------------------------------------------------------------------
# app/admin/__init__.py
# The admin blueprint. Reserved for staff management pages (students, users,
# announcements). The MVP manages the roster with the "flask seed-roster"
# command, so there are no routes here yet.
# ---------------------------------------------------------------------------

from flask import Blueprint

bp = Blueprint("admin", __name__)
