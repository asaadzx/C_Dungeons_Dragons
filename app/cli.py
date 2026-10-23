import json
from pathlib import Path

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Announcement, LhrGame, Student, User


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


@click.command("seed-lhr")
@with_appcontext
def seed_lhr():
    games = [
        {
            "title": "Japanese Vocabulary Quiz Show",
            "rules": "Split into teams. Take turns answering Japanese vocabulary questions from the video and class material. Correct answers earn points.",
            "max_players": 8,
            "status": "Upcoming",
        },
        {
            "title": "Charades (Mime & Guess)",
            "rules": "Act out Japanese words/actions without speaking. Teammates guess in Japanese. Great for building vocabulary through movement.",
            "max_players": 12,
            "status": "Upcoming",
        },
        {
            "title": "Bingo Vocabulary Battle",
            "rules": "Create bingo cards with Japanese vocab. Call words in Japanese and mark them. First to get a line wins a round.",
            "max_players": 16,
            "status": "Upcoming",
        },
        {
            "title": "Word Chain (しりとり)",
            "rules": "Take turns saying words where the next word starts with the last syllable of the previous one. Keep it going as long as possible!",
            "max_players": 10,
            "status": "Upcoming",
        },
        {
            "title": "Pictionary in Japanese",
            "rules": "Draw a Japanese word on the board while teammates guess in Japanese. No English allowed during the round.",
            "max_players": 12,
            "status": "Upcoming",
        },
    ]
    created = 0
    for data in games:
        if LhrGame.query.filter_by(title=data["title"]).first() is None:
            db.session.add(LhrGame(**data))
            created += 1
    db.session.commit()
    click.echo(f"LHR ready: {created} games added.")


@click.command("add-announcement")
@click.option("--title", prompt=True)
@click.option("--content", prompt=True)
@click.option("--category", default="News")
@with_appcontext
def add_announcement(title, content, category):
    db.session.add(Announcement(title=title, content=content, category=category))
    db.session.commit()
    click.echo("Announcement added.")


def register_cli(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_roster)
    app.cli.add_command(seed_lhr)
    app.cli.add_command(add_announcement)
