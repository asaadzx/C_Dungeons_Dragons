# ---------------------------------------------------------------------------
# app/auth/routes.py
# Staff login and logout.
#
# Only teachers/admins log in. Students browse the hub without an account,
# so there is no registration page here.
# ---------------------------------------------------------------------------

from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from . import bp
from ..models import User


def _safe_next(target):
    """Validate the ?next= redirect target.

    Only allow same-site (relative) paths. This blocks "open redirect" abuse
    where an attacker crafts a login link that bounces to their own site.
    """
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.netloc:   # an absolute URL pointing at another host
        return None
    return target


@bp.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        # One generic error message for both wrong user and wrong password,
        # so attackers cannot tell which usernames exist.
        if user is None or not user.active or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return render_template("auth/login.html"), 401

        login_user(user)
        target = _safe_next(request.args.get("next"))
        return redirect(target or url_for("hub.index"))

    return render_template("auth/login.html")


@bp.route("/auth/logout", methods=["POST"])
def logout():
    # POST only (with CSRF token) so a random image/link cannot log people out.
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("hub.index"))
