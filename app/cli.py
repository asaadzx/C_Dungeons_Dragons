import json
from pathlib import Path

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Student, User


def load_roster():
    path = Path(__file__).resolve().parent.parent / "scripts" / "roster.js"
    text = path.read_text(encoding="utf-8")
    payload = text.split("=", 1)[1].strip().rstrip(";")
    return json.loads(payload)


@click.command("create-admin")
@click.option("--username", prompt=True)
@click.option("--password", default=None)
@with_appcontext
def create_admin(username, password):
    if not password:
        password = click.prompt(
            "Password", hide_input=True, confirmation_prompt=True
        )
    existing = User.query.filter_by(username=username).first()
    if existing:
        existing.set_password(password)
        existing.role = "admin"
        existing.active = True
        click.echo(f"Updated admin {username}.")
    else:
        user = User(username=username, role="admin", active=True)
        user.set_password(password)
        db.session.add(user)
        click.echo(f"Created admin {username}.")
    db.session.commit()


@click.command("seed-roster")
@with_appcontext
def seed_roster():
    roster = load_roster()
    created = 0
    for row in roster:
        student = Student.query.filter_by(name_en=row["en"]).first()
        if student is None:
            student = Student(name_en=row["en"], name_ar=row.get("ar", ""))
            db.session.add(student)
            created += 1
        else:
            student.name_ar = row.get("ar", student.name_ar)
            student.active = True
    db.session.commit()
    click.echo(f"Roster ready: {len(roster)} students, {created} created.")


def register_cli(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_roster)
