# ---------------------------------------------------------------------------
# app/auth/__init__.py
# The auth blueprint: login and logout routes.
# ---------------------------------------------------------------------------

from flask import Blueprint

bp = Blueprint("auth", __name__)

# Imported last so the routes above can use "from . import bp".
from . import routes  # noqa: E402,F401
