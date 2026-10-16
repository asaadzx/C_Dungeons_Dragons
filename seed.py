# ---------------------------------------------------------------------------
# seed.py
# Populates the database with sample ("mock") data for development and demos.
#
# Run it with:   python seed.py
#
# What it does:
#   1. Makes sure the tables exist (runs schema.sql).
#   2. Clears any old rows so you always start from a known state.
#   3. Inserts announcements, games, students (with contact/social links),
#      the KOSEN Spotlight (TED talks + memes) and the Community Events board
#      (events + "ask to go with them" requests).
#
# Responsibility: Testing & Presentation Lead role.
# ---------------------------------------------------------------------------

import sqlite3   # built-in module used to talk to the SQLite file
import os        # used to build safe file paths


# Paths to the database file and the schema file (both live next to this file).
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')


def seed():
    """Create the tables and insert the starter sample data."""

    # Connect and make sure the tables exist before inserting anything.
    conn = sqlite3.connect(DATABASE_PATH)
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())

    # --- Reset: delete any existing rows so re-running gives a clean slate ---
    # Child tables (that reference others) are cleared first for tidiness.
    conn.execute('DELETE FROM event_requests')
    conn.execute('DELETE FROM events')
    conn.execute('DELETE FROM announcements')
    conn.execute('DELETE FROM lhr_games')
    conn.execute('DELETE FROM students')
    conn.execute('DELETE FROM ted_talks')
    conn.execute('DELETE FROM memes')

    # Reset the AUTOINCREMENT counters so the first row is id = 1 again.
    # (sqlite_sequence is created automatically by SQLite for AUTOINCREMENT
    #  tables; we guard with try/except in case it does not exist yet.)
    try:
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN "
            "('announcements', 'lhr_games', 'students', 'ted_talks', 'memes', "
            " 'events', 'event_requests')"
        )
    except sqlite3.OperationalError:
        pass

    # ---------------------------- Announcements ----------------------------
    # Each tuple matches (title, content, category).
    # The '?' placeholders are replaced safely by the values in the tuple,
    # which protects against SQL-injection and quoting mistakes.
    conn.execute(
        "INSERT INTO announcements (title, content, category) VALUES (?, ?, ?)",
        ('Welcome to C1 RAS Hub',
         'This is the official hub for C1 class announcements.',
         'News')
    )
    conn.execute(
        "INSERT INTO announcements (title, content, category) VALUES (?, ?, ?)",
        ('Study Tip',
         'Always review lecture notes after class.',
         'Tip')
    )
    conn.execute(
        "INSERT INTO announcements (title, content, category) VALUES (?, ?, ?)",
        ('Fun Friday',
         'Get ready for LHR activities this Friday!',
         'News')
    )

    # ------------------------------ LHR games ------------------------------
    # Each tuple matches (title, rules, max_players, status).
    conn.execute(
        "INSERT INTO lhr_games (title, rules, max_players, status) VALUES (?, ?, ?, ?)",
        ('Trivia Battle',
         'Form teams and answer questions. Highest score wins!',
         4, 'Upcoming')
    )
    conn.execute(
        "INSERT INTO lhr_games (title, rules, max_players, status) VALUES (?, ?, ?, ?)",
        ('Word Puzzle',
         'Solve word puzzles against other teams.',
         3, 'Active')
    )
    conn.execute(
        "INSERT INTO lhr_games (title, rules, max_players, status) VALUES (?, ?, ?, ?)",
        ('Quiz Rush',
         'Fast-paced quiz competition.',
         5, 'Upcoming')
    )

    # ------------------------------ Students -------------------------------
    # Each tuple matches the columns in order:
    #   (name, interests, role, website, facebook, instagram, phone, email)
    # The link/phone/email values are EXAMPLE placeholders (example.com) so the
    # directory shows how the fields look - students can add their real ones
    # using the "Add yourself" form on the /directory page.
    students = [
        ('Asaad Zein', 'Python, web dev and fun side projects. Ask me about Flask!',
         'Leader', 'https://asaad.example.com', 'https://facebook.com/asaad.zein',
         'https://instagram.com/asaad.dev', '+20 100 000 0001', 'asaad@example.com'),
        ('Mohaned Mahmoud', 'Engineering + programming. Member of the robotics club.',
         'Student', 'https://mohaned.example.com', 'https://facebook.com/mohaned.m',
         'https://instagram.com/mohaned.eng', '+20 100 000 0002', 'mohaned@example.com'),
        ('Joyce Gaber', 'Coding and graphic design. I love pixel art and retro games.',
         'Student', '', 'https://facebook.com/joyce.g',
         'https://instagram.com/joyce.designs', '+20 100 000 0003', 'joyce@example.com'),
        ('Recardo Maged', 'Tech and gaming. Always up for a LAN party or a good hackathon.',
         'Student', 'https://recardo.example.com', 'https://facebook.com/recardo.m',
         '', '+20 100 000 0004', 'recardo@example.com'),
        ('Anas Abdelmenem', 'Programming and sports. Football on the weekends.',
         'Student', '', '', 'https://instagram.com/anas.zzz',
         '+20 100 000 0005', 'anas@example.com'),
    ]
    conn.executemany(
        "INSERT INTO students "
        "(name, interests, role, website, facebook, instagram, phone, email) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        students
    )

    # ---------------------- KOSEN Spotlight: TED talks ---------------------
    # Each tuple matches (title, url, thumbnail, description).
    # "thumbnail" is a path inside the static/ folder so it loads OFFLINE.
    ted_talks = [
        (
            'AI brain fry is real. Here is what is causing it',
            'https://www.ted.com/talks/julie_bedard_ai_brain_fry_is_real_here_s_what_s_causing_it',
            'img/ted/ted_1.jpg',
            'Why constant notifications leave your brain exhausted, and how to get your focus back.'
        ),
        (
            'The next outbreak? We are not ready',
            'https://www.ted.com/talks/bill_gates_the_next_outbreak_we_re_not_ready',
            'img/ted/ted_2.jpg',
            'A wake-up call on global health, preparedness and the technology that can save lives.'
        ),
        (
            'Do schools kill creativity?',
            'https://www.ted.com/talks/sir_ken_robinson_do_schools_kill_creativity',
            'img/ted/ted_3.jpg',
            'A legendary talk on why creativity deserves the same status as literacy in education.'
        ),
    ]
    conn.executemany(
        "INSERT INTO ted_talks (title, url, thumbnail, description) VALUES (?, ?, ?, ?)",
        ted_talks
    )

    # ------------------------ KOSEN Spotlight: memes -----------------------
    # Each tuple matches (image_url, caption).
    # "image_url" is a path inside the static/ folder so it loads OFFLINE.
    memes = [
        ('img/memes/meme_physics.jpg', 'after studying all physics 😭'),
        ('img/memes/meme_drake.jpg', 'Ignoring 3 weeks of lectures then blaming the exam'),
        ('img/memes/meme_twobuttons.jpg', 'Sleep  vs.  "just one more chapter"'),
        ('img/memes/meme_distracted.jpg', 'Me: "I will study after this video"'),
        ('img/memes/meme_uno.jpg', 'Draw 25 cards  or  start the project before the night before'),
        ('img/memes/meme_gru.jpg', 'Step 1: make a study plan. Step 3: cry'),
        ('img/memes/meme_alwaysbeen.jpg', 'Wait... the whole grade was one exam?'),
        ('img/memes/meme_handshake.jpg', 'Making a study playlist = studying (apparently)'),
        ('img/memes/meme_disastergirl.jpg', 'Me: "I will start tonight." Me at 3 a.m.: *surprised*'),
    ]
    conn.executemany(
        "INSERT INTO memes (image_url, caption) VALUES (?, ?)",
        memes
    )

    # --------------------------- Community Events --------------------------
    # Each tuple matches (organizer_id, title, link, description, event_date, location).
    # organizer_id points at a student row (see the students list above, ids 1-5),
    # which is what links the events board to the Student Directory.
    events = [
        (1, 'Cairo Jazz Festival', 'https://www.cairojazzfest.com',
         'Live jazz nights by the Nile. Let us go together!', 'Fri 21 Nov', 'Zamalek, Cairo'),
        (3, 'NASA Space Apps Hackathon', 'https://www.spaceappschallenge.org',
         '48-hour global hackathon - teams are formed on the day.', 'Sat 5 Oct', 'Online + Cairo'),
        (5, 'C1 vs C2 Football Match', '',
         'Friendly match between class C1 and C2. Bring your kit!', 'Thu 4 PM', 'College field'),
        (2, 'PyCon Egypt', 'https://www.pycon.eg',
         'Python talks and workshops. Beginners are very welcome.', 'Dec (TBA)', 'Cairo'),
    ]
    conn.executemany(
        "INSERT INTO events "
        "(organizer_id, title, link, description, event_date, location) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        events
    )

    # ---------------------- "Ask to go with them" requests -----------------
    # Each tuple matches (event_id, requester_name, message).
    # These are sample join-requests shown on the events board. The optional
    # user_id column is left NULL for now (reserved for the future login).
    event_requests = [
        (1, 'Joyce Gaber', 'I love jazz, count me in!'),
        (1, 'Recardo Maged', 'Can I bring a friend?'),
        (2, 'Mohaned Mahmoud', 'Looking for a team!'),
    ]
    conn.executemany(
        "INSERT INTO event_requests (event_id, requester_name, message) VALUES (?, ?, ?)",
        event_requests
    )

    conn.commit()   # save all inserts to disk
    conn.close()    # release the connection
    print('Database seeded successfully!')
    print('  announcements: 3 | games: 3 | students: '
          f'{len(students)} | events: {len(events)} | requests: {len(event_requests)}')
    print(f'  ted_talks: {len(ted_talks)} | memes: {len(memes)}')


# This block runs only when the file is executed directly
# (i.e. "python seed.py"), not when it is imported by another file.
if __name__ == '__main__':
    seed()
