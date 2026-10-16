# ---------------------------------------------------------------------------
# app.py
# Main entry point of the C! Dungeons & Dragons (C! RAS Hub) web application.
#
# This file defines the URLs ("routes") the browser can visit and decides
# which HTML template to render for each one. It reads data from the SQLite
# database using the helpers in database.py, then hands that data to Jinja2
# templates inside the templates/ folder.
#
# Run it with:   python app.py
# Then open:     http://127.0.0.1:5000
#
# Responsibility: Team Lead / Architect role.
# ---------------------------------------------------------------------------

import random  # used to pick a random TED talk + meme for the spotlight

from flask import (Flask, render_template, request, redirect, url_for,
                   flash)  # flash shows short one-time messages to the user
from database import get_db_connection, init_db

# Create the Flask application object. __name__ tells Flask where to find
# the templates/ and static/ folders relative to this file.
app = Flask(__name__)

# A secret key is needed for "flash" messages (they are stored in a signed
# cookie between requests). This is a development value only - a real
# deployment would load it from an environment variable.
app.secret_key = 'c1-ras-hub-dev-secret-key'

# Make sure the database and its tables exist before the first request.
init_db()


def get_random_row(table):
    """
    Return one random row from the given table, or None if the table is empty.

    ORDER BY RANDOM() is a built-in SQLite trick that shuffles the rows, so
    LIMIT 1 gives us a different row on almost every call.
    """
    conn = get_db_connection()
    row = conn.execute(f'SELECT * FROM {table} ORDER BY RANDOM() LIMIT 1').fetchone()
    conn.close()
    return row


def get_events_with_requests():
    """
    Fetch every community event (newest first) together with its join requests.

    Returns a tuple (events, requests_by_event) where:
      * events            -> list of rows, each also carrying organizer_name
      * requests_by_event -> dictionary {event_id: [request rows]}
    Grouping the requests in Python keeps the template simple.
    """
    conn = get_db_connection()
    # JOIN pulls the organizer's name from the students table so we can show
    # (and link to) who is organising each event.
    events = conn.execute(
        'SELECT events.*, students.name AS organizer_name '
        'FROM events JOIN students ON events.organizer_id = students.id '
        'ORDER BY events.id DESC'
    ).fetchall()
    requests = conn.execute(
        'SELECT * FROM event_requests ORDER BY id ASC'
    ).fetchall()
    conn.close()

    # Build {event_id: [requests...]} so the template can show them per event.
    requests_by_event = {}
    for r in requests:
        requests_by_event.setdefault(r['event_id'], []).append(r)

    return events, requests_by_event


# ---------------------------------------------------------------------------
# Route: "/"  ->  Official Bulletin & Culture Board + KOSEN Spotlight
# Shows all announcements (newest first), plus a random TED talk and a
# random meme picked from the database on every page load.
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    conn = get_db_connection()
    # ORDER BY created_at DESC puts the most recent announcement on top.
    announcements = conn.execute(
        'SELECT * FROM announcements ORDER BY created_at DESC'
    ).fetchall()
    conn.close()

    # Pick one random TED talk and one random meme for the spotlight section.
    ted_talk = get_random_row('ted_talks')
    meme = get_random_row('memes')

    # Render the template, passing the rows in as template variables.
    return render_template(
        'index.html',
        announcements=announcements,
        ted_talk=ted_talk,
        meme=meme
    )


# ---------------------------------------------------------------------------
# Route: "/lhr"  ->  LHR Games & Activity Center
# Lists every game/activity in the hub.
# ---------------------------------------------------------------------------
@app.route('/lhr')
def lhr():
    conn = get_db_connection()
    lhr_games = conn.execute('SELECT * FROM lhr_games ORDER BY id ASC').fetchall()
    conn.close()
    return render_template('lhr.html', lhr_games=lhr_games)


# ---------------------------------------------------------------------------
# Route: "/lhr/game/<id>"  ->  a single game's detail page
# <int:game_id> means the URL must contain a whole number, which Flask
# passes to this function as game_id.
# ---------------------------------------------------------------------------
@app.route('/lhr/game/<int:game_id>')
def game_detail(game_id):
    conn = get_db_connection()
    # Fetch the one game whose id matches the URL. The trailing comma makes
    # (game_id,) a tuple, which is what execute() expects for parameters.
    game = conn.execute('SELECT * FROM lhr_games WHERE id = ?', (game_id,)).fetchone()
    conn.close()
    # If no such game exists, send the user back to the games list.
    if game is None:
        return redirect(url_for('lhr'))
    return render_template('game_detail.html', game=game)


# ---------------------------------------------------------------------------
# Route: "/directory"  ->  Student Directory
# Shows all classmates (sorted by name) as profile cards. Each card links to
# the full profile page and shows the contact/social details students added.
# ---------------------------------------------------------------------------
@app.route('/directory')
def directory():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY name ASC').fetchall()
    conn.close()
    return render_template('directory.html', students=students)


# ---------------------------------------------------------------------------
# Route: "/directory/add"  ->  create a new student profile
# Handles the "Add yourself" form. Only the name is required; every other
# field is optional. (Post-Midterm this would be tied to a login account.)
# ---------------------------------------------------------------------------
@app.route('/directory/add', methods=['POST'])
def add_student():
    # .strip() removes accidental spaces at the start/end of the input.
    name = request.form.get('name', '').strip()
    if not name:
        flash('Please enter your name.', 'error')
        return redirect(url_for('directory'))

    # Read the optional fields. The role is checked against a safe list.
    interests = request.form.get('interests', '').strip()
    role = request.form.get('role', 'Student')
    if role not in ('Student', 'Leader', 'Admin'):
        role = 'Student'
    website = request.form.get('website', '').strip()
    facebook = request.form.get('facebook', '').strip()
    instagram = request.form.get('instagram', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO students '
        '(name, interests, role, website, facebook, instagram, phone, email) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (name, interests, role, website, facebook, instagram, phone, email)
    )
    conn.commit()
    conn.close()
    flash(f'Welcome, {name}! Your profile was added to the directory.', 'success')
    return redirect(url_for('directory'))


# ---------------------------------------------------------------------------
# Route: "/student/<id>"  ->  a single student's profile page
# This is the link between the Directory and the Events board: it shows the
# student's contact details AND every event they have posted.
# ---------------------------------------------------------------------------
@app.route('/student/<int:student_id>')
def student_profile(student_id):
    conn = get_db_connection()
    student = conn.execute(
        'SELECT * FROM students WHERE id = ?', (student_id,)
    ).fetchone()
    if student is None:
        conn.close()
        return redirect(url_for('directory'))  # unknown id -> back to the list
    # All events organised by this student.
    events = conn.execute(
        'SELECT * FROM events WHERE organizer_id = ? ORDER BY id DESC',
        (student_id,)
    ).fetchall()
    conn.close()
    return render_template('profile.html', student=student, events=events)


# ---------------------------------------------------------------------------
# Route: "/schedule"  ->  Community Events calendar (month-aware)
# Shows current month grid with events placed by day number extracted from
# event_date (e.g. "21 Oct", "Fri 21 Oct").
# ---------------------------------------------------------------------------
from datetime import datetime
import calendar
import re

@app.route('/schedule')
def schedule():
    events, requests_by_event = get_events_with_requests()
    conn = get_db_connection()
    students = conn.execute(
        'SELECT id, name FROM students ORDER BY name ASC'
    ).fetchall()
    conn.close()

    now = datetime.now()
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(now.year, now.month)
    current_month = now.strftime('%B %Y')

    # group events by day number
    events_by_day = {}
    for ev in events:
        d = ev['event_date'] or ''
        m = re.findall(r'\b(\d{1,2})\b', d)
        if m:
            try:
                day = int(m[-1])
                if 1 <= day <= 31:
                    events_by_day.setdefault(day, []).append(ev)
            except ValueError:
                pass

    return render_template(
        'schedule.html',
        events=events,
        requests_by_event=requests_by_event,
        students=students,
        weeks=weeks,
        current_month=current_month,
        today=now.day,
        events_by_day=events_by_day
    )


# ---------------------------------------------------------------------------
# Route: "/schedule/add"  ->  post a new event to the board
# Handles the "Add an event" form. The organizer must be chosen from the
# student dropdown, which is how an event gets linked to the directory.
# ---------------------------------------------------------------------------
@app.route('/schedule/add', methods=['POST'])
def add_event():
    organizer_id = request.form.get('organizer_id', '').strip()
    title = request.form.get('title', '').strip()
    link = request.form.get('link', '').strip()
    description = request.form.get('description', '').strip()
    event_date = request.form.get('event_date', '').strip()
    location = request.form.get('location', '').strip()

    # Organizer and title are required; the rest are optional.
    if not organizer_id or not title:
        flash('Please choose an organizer and enter an event title.', 'error')
        return redirect(url_for('schedule'))

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO events '
        '(organizer_id, title, link, description, event_date, location) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (organizer_id, title, link, description, event_date, location)
    )
    conn.commit()
    conn.close()
    flash('Event added to the board!', 'success')
    return redirect(url_for('schedule'))


# ---------------------------------------------------------------------------
# Route: "/event/<id>/join"  ->  "Ask to go with them"
# Saves a short request (name + optional message) for an event. The future
# login system will fill in the user_id column instead of asking for a name.
# ---------------------------------------------------------------------------
@app.route('/event/<int:event_id>/join', methods=['POST'])
def join_event(event_id):
    name = request.form.get('requester_name', '').strip()
    message = request.form.get('message', '').strip()

    conn = get_db_connection()
    # Make sure the event still exists before adding a request.
    event = conn.execute('SELECT id FROM events WHERE id = ?', (event_id,)).fetchone()
    if event is None:
        conn.close()
        flash('That event no longer exists.', 'error')
        return redirect(url_for('schedule'))

    if not name:
        conn.close()
        flash('Please type your name so they know who wants to join.', 'error')
        # Jump back to this event's card using its #anchor id.
        return redirect(url_for('schedule', _anchor=f'event-{event_id}'))

    conn.execute(
        'INSERT INTO event_requests (event_id, requester_name, message) '
        'VALUES (?, ?, ?)',
        (event_id, name, message)
    )
    conn.commit()
    conn.close()
    flash('Request sent! The organizer can see you want to go.', 'success')
    return redirect(url_for('schedule', _anchor=f'event-{event_id}'))


# Start the development web server when this file is run directly.
# host='0.0.0.0' allows other devices on the same Wi-Fi/LAN to connect too
# (useful for testing on a phone). debug=True auto-reloads on code changes.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
