# ---------------------------------------------------------------------------
# app/extensions.py
# Shared Flask extension objects.
#
# They are created here (not inside create_app) so that any module can import
# them without creating a circular import. The app factory then binds them to
# the app with init_app().
# ---------------------------------------------------------------------------

from flask_login import LoginManager      # session-based staff login
from flask_migrate import Migrate         # database migrations (Alembic)
from flask_sqlalchemy import SQLAlchemy   # ORM models <-> database tables
from flask_wtf import CSRFProtect         # CSRF protection for POST forms

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
