# Project Journey
### Building "C! Dungeons & Dragons" — a step-by-step course

> **What this is:** a day-by-day teaching guide that reconstructs the whole
> project from an empty folder. Follow it in order. Each day has:
> a **Goal** → **Concepts** → **Hands-on steps** → a **Checkpoint** you must
> pass before moving on.
>
> **Stack:** Python 3 · Flask · SQLite · HTML/Jinja2 · NES.css
> **Length:** 10 days (about 1–2 hours each)

---

## Before Day 0 — What you need

| Tool | Why | Check it works |
|------|-----|----------------|
| Python 3.10+ | The language | `python3 --version` |
| VS Code (or any editor) | Writing code | opens a folder |
| A terminal | Running commands | `echo hello` |
| Git | Saving versions | `git --version` |
| A browser | Seeing your site | any |

**Two rules for the whole project:**

1. **Use a virtual environment** (`.venv`). It keeps this project's packages
   separate from your computer's other Python projects.
2. **Quote paths with special characters.** Our folder contains `!` and `&`:
   ```bash
   cd "/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub"
   ```

---

# Day 1 — Empty project + "Hello, world" in Flask

### Goal
A folder that can run a web server and show one page.

### Concepts
- **Virtual environment** (`.venv`): an isolated Python install.
- **Flask**: a "micro web framework" — it maps a URL to a Python function.
- **Route**: a URL your app answers to, like `/` or `/about`.
- **Template**: an HTML file with placeholders filled in by Python.

### Steps

1. Create the folder and enter it:
   ```bash
   mkdir -p c1_ras_hub && cd c1_ras_hub
   ```

2. Make the virtual environment and switch it on:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate       # you'll see (.venv) appear in your prompt
   ```

3. Install Flask **inside** `.venv`:
   ```bash
   pip install Flask
   ```

4. Record it so anyone can rebuild later:
   ```bash
   pip freeze > requirements.txt
   ```

5. Create this file structure (make empty files first, we fill them in later):
   ```text
   c1_ras_hub/
   ├── app.py
   ├── database.py
   ├── schema.sql
   ├── seed.py
   ├── requirements.txt
   ├── templates/
   │   └── base.html
   └── static/
       ├── css/style.css
       └── js/app.js
   ```

6. Write **`app.py`** — the heart of the app:
   ```python
   from flask import Flask, render_template

   app = Flask(__name__)   # __name__ tells Flask where templates/ live

   @app.route('/')          # visiting "/" runs the function below
   def index():
       return render_template('base.html', message="Hello, world!")

   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5000, debug=True)
   ```

7. Write **`templates/base.html`** — the master layout every page will extend:
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>C! Dungeons &amp; Dragons</title>
   </head>
   <body>
       <h1>{{ message }}</h1>
       {% block content %}{% endblock %}
   </body>
   </html>
   ```
   > `{{ message }}` is Jinja2 output. `{% block content %}` is a **hole** that
   > other templates will fill.

8. Run it:
   ```bash
   python app.py
   ```
   Open <http://127.0.0.1:5000> → you should see **Hello, world!**

### ✅ Checkpoint
- [ ] `python app.py` starts without errors.
- [ ] The browser shows `Hello, world!`.
- [ ] You understand: URL → `@app.route` → Python function → template.

---

# Day 2 — Database: SQLite, schema, connection helper

### Goal
A `database.db` file with tables, and a helper module that opens it.

### Concepts
- **SQLite**: a database stored as ONE file (`database.db`). No server needed → perfect for offline demos.
- **Table**: rows + columns, like a spreadsheet.
- **Schema**: the blueprint that says what columns exist and their types.
- **`sqlite3.Row`**: lets you read a column by **name** (`row['title']`) instead of number.

### Steps

1. Write **`schema.sql`** — the blueprint:
   ```sql
   -- A table of announcements. IF NOT EXISTS makes it safe to run twice.
   CREATE TABLE IF NOT EXISTS announcements (
       id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique, auto-numbered
       title TEXT NOT NULL,                   -- must not be empty
       content TEXT NOT NULL,
       category TEXT CHECK(category IN ('News','Tip','Meme','TED')) NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- auto timestamp
   );
   ```
   > The `CHECK(...)` is a **guard**: only those four category values are ever
   > allowed in. If a programmer types `category='Gossip'`, SQLite refuses it.

2. Write **`database.py`** — the connection helper (Database Specialist role):
   ```python
   import sqlite3
   import os

   # os.path.dirname(__file__) = "the folder this file lives in"
   DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


   def get_db_connection():
       """Open the DB and return rows you can read by column name."""
       conn = sqlite3.connect(DATABASE_PATH)
       conn.row_factory = sqlite3.Row   # <-- row['title'] now works
       return conn


   def init_db():
       """Create the tables if they don't exist yet."""
       conn = get_db_connection()
       with open(os.path.join(os.path.dirname(__file__), 'schema.sql'),
                 'r', encoding='utf-8') as f:
           conn.executescript(f.read())   # run the whole .sql file
       conn.commit()
       conn.close()
   ```

3. Call it once when the app starts — add to **`app.py`**:
   ```python
   from database import init_db

   app = Flask(__name__)
   init_db()          # tables exist before the first page is requested
   ```

4. Test it from the terminal:
   ```bash
   source .venv/bin/activate
   python -c "
   from database import get_db_connection, init_db
   init_db()
   c = get_db_connection()
   print([r['name'] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")])
   c.close()
   "
   ```
   Output: `['announcements']`

5. Start a `.gitignore` so junk never enters Git:
   ```gitignore
   .venv/
   __pycache__/
   *.db
   ```

### ✅ Checkpoint
- [ ] `database.db` file appears in the folder.
- [ ] You can list the table from the terminal.
- [ ] `.venv` and `*.db` are ignored by Git.

---

# Day 3 — Reading data and rendering a real page

### Goal
Store announcements in the DB and show them on `/`.

### Concepts
- **Placeholder query**: `'SELECT * FROM announcements WHERE id = ?'` — the `?`
  is filled safely by a tuple. **Never** paste user text into SQL by hand
  (that's *SQL injection*).
- **Passing data to a template**: `render_template('x.html', rows=rows)`.
- **Jinja2 loops**: `{% for row in rows %} ... {% endfor %}`.

### Steps

1. Add a second table to **`schema.sql`**:
   ```sql
   CREATE TABLE IF NOT EXISTS lhr_games (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       title TEXT NOT NULL,
       rules TEXT NOT NULL,
       max_players INTEGER NOT NULL,
       status TEXT CHECK(status IN ('Upcoming','Active','Completed')) DEFAULT 'Upcoming'
   );
   ```

2. Update `index()` in **`app.py`**:
   ```python
   from flask import render_template
   from database import get_db_connection, init_db

   @app.route('/')
   def index():
       conn = get_db_connection()
       # DESC = newest first
       announcements = conn.execute(
           'SELECT * FROM announcements ORDER BY created_at DESC'
       ).fetchall()
       conn.close()                    # always close!
       return render_template('index.html', announcements=announcements)
   ```

3. Make **`templates/index.html`** fill the hole in `base.html`:
   ```html
   {% extends 'base.html' %}          <!-- reuse the master layout -->

   {% block content %}
     <h2>Bulletin</h2>
     {% for a in announcements %}
       <article>
         <span>{{ a['category'] }}</span>
         <h3>{{ a['title'] }}</h3>
         <p>{{ a['content'] }}</p>
       </article>
     {% else %}
       <p>Nothing yet.</p>
     {% endfor %}
   {% endblock %}
   ```

### ✅ Checkpoint
- [ ] The page renders (even with zero rows — you see "Nothing yet.").
- [ ] You can explain why `?` placeholders exist.

---

# Day 4 — Sample data + more pages

### Goal
A `seed.py` that fills the DB with realistic data, plus `/lhr` and `/directory`.

### Concepts
- **Seeding**: wiping and refilling the DB so every run starts known.
- **`executemany`**: insert a whole list of rows in one call.
- **Resetting the id counter**: SQLite keeps a hidden `sqlite_sequence` table.
  Deleting from it makes the next insert start at `1` again — this is what
  makes a "clean undo" button possible during a demo.
- **Path parameters**: `/lhr/game/<int:game_id>` passes `game_id` into your function.

### Steps

1. Write **`seed.py`**:
   ```python
   import sqlite3, os

   DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
   SCHEMA_PATH   = os.path.join(os.path.dirname(__file__), 'schema.sql')

   def seed():
       conn = sqlite3.connect(DATABASE_PATH)
       with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
           conn.executescript(f.read())      # make sure tables exist

       # 1) wipe old data (children first)
       conn.execute('DELETE FROM announcements')
       conn.execute('DELETE FROM lhr_games')
       conn.execute('DELETE FROM students')

       # 2) reset id counters back to 1
       try:
           conn.execute("DELETE FROM sqlite_sequence WHERE name IN "
                        "('announcements','lhr_games','students')")
       except sqlite3.OperationalError:
           pass

       # 3) insert sample rows (the ? are replaced safely by the tuple)
       conn.execute(
           "INSERT INTO announcements (title, content, category) VALUES (?, ?, ?)",
           ('Welcome to C1 RAS Hub', 'Official hub for C1 announcements.', 'News'))
       conn.execute(
           "INSERT INTO lhr_games (title, rules, max_players, status) VALUES (?, ?, ?, ?)",
           ('Trivia Battle', 'Form teams and answer questions!', 4, 'Upcoming'))

       conn.commit()
       conn.close()
       print('Seeded!')

   if __name__ == '__main__':
       seed()
   ```

2. Add the games routes to **`app.py`**:
   ```python
   @app.route('/lhr')
   def lhr():
       conn = get_db_connection()
       games = conn.execute('SELECT * FROM lhr_games ORDER BY id ASC').fetchall()
       conn.close()
       return render_template('lhr.html', lhr_games=games)


   @app.route('/lhr/game/<int:game_id>')
   def game_detail(game_id):
       conn = get_db_connection()
       game = conn.execute('SELECT * FROM lhr_games WHERE id = ?',
                           (game_id,)).fetchone()   # trailing comma → tuple
       conn.close()
       if game is None:
           return redirect(url_for('lhr'))          # unknown id → go back
       return render_template('game_detail.html', game=game)
   ```
   > Note the **trailing comma**: `(game_id,)` is a tuple. `execute()` needs a
   > tuple of parameters, not a bare value.

3. Add navigation to **`templates/base.html`**:
   ```html
   <nav>
     <a href="{{ url_for('index') }}">Bulletin</a>
     <a href="{{ url_for('lhr') }}">LHR Games</a>
   </nav>
   ```
   > Always use `url_for('function_name')` instead of typing `/lhr` by hand.
   > If you rename the route later, every link updates itself.

4. Fill the DB:
   ```bash
   python seed.py
   ```

### ✅ Checkpoint
- [ ] `/` and `/lhr` show seeded data.
- [ ] `/lhr/game/1` shows the game; `/lhr/game/999` redirects away.
- [ ] Re-running `python seed.py` gives the exact same data again.

---

# Day 5 — Making it look good, offline

### Goal
A pixel/retro UI that works with **no internet**.

### Concepts
- **Vendoring**: downloading a library into `static/` so it never needs a CDN.
- **`url_for('static', filename=...)`**: how Flask points at a file in `static/`.
- **CSS variables** (`:root { --color: ... }`): change a theme in ONE place.
- **Load order matters**: your CSS loads *after* the library so it wins.

### Steps

1. Download the CSS library and font once (needs internet **once**):
   ```bash
   mkdir -p static/nes/fonts
   curl -L -o static/nes/nes.min.css \
     https://unpkg.com/nes.css/css/nes.min.css
   curl -L -o static/nes/fonts/press-start-2p.woff2 \
     "https://fonts.gstatic.com/s/pressstart2p/v15/e3t4euO8T-267oIAQAu6jDQyK3nVivM.woff2"
   ```
   > We use **NES.css** (MIT licence, CSS-only) rather than a React library,
   > because React needs a Node build step that Flask can't use.

2. Link both files in **`templates/base.html`**:
   ```html
   <head>
     <link rel="stylesheet" href="{{ url_for('static', filename='nes/nes.min.css') }}">
     <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
   </head>
   ```

3. Create **`static/css/style.css`** with a theme you can edit in one spot:
   ```css
   @font-face {
       font-family: 'Press Start 2P';
       src: url('../nes/fonts/press-start-2p.woff2') format('woff2');
       font-display: swap;
   }

   :root {
       --theme-base:   #BE1A1A;   /* base red        */
       --theme-accent: #D0311E;   /* lighter red     */
       --theme-gold:   #F7D87F;   /* light gold      */
       --theme-paper:  #F8EBAB;   /* cream (bg)      */
   }

   body {
       font-family: 'Press Start 2P', monospace;
       background-color: var(--theme-paper);
       color: #111111;                       /* dark text on light bg */
       text-shadow: 1px 1px 0 #ffffffaa;     /* boosts legibility */
   }
   h1, h2, h3 { color: var(--theme-base); text-shadow: 2px 2px 0 #ffffffcc; }
   ```

4. Use the library's classes in your HTML:
   ```html
   <a class="nes-btn is-primary">Click me</a>
   <section class="nes-container is-rounded">A card</section>
   ```

### ✅ Checkpoint
- [ ] Turn Wi-Fi **off** → reload → still styled (fonts + CSS load).
- [ ] Changing one line in `:root` changes the whole theme.

> **Design rule you'll use forever:** text must contrast with its background.
> Put *dark text on light backgrounds* (and add a light `text-shadow` to make
> pixel fonts pop).

---

# Day 6 — The "KOSEN Spotlight": one random row per page load

### Goal
Every home-page load shows **one random TED talk** and **one random meme**.

### Concepts
- **`ORDER BY RANDOM() LIMIT 1`** — SQLite's built-in shuffle, take the first.
- Grouping related data into tables so the spotlight is *data*, not hardcoded.

### Steps

1. Add two tables to **`schema.sql`**:
   ```sql
   CREATE TABLE IF NOT EXISTS ted_talks (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       title TEXT NOT NULL,
       url TEXT NOT NULL,
       thumbnail TEXT NOT NULL,   -- path INSIDE static/ → loads offline
       description TEXT NOT NULL
   );

   CREATE TABLE IF NOT EXISTS memes (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       image_url TEXT NOT NULL,
       caption TEXT NOT NULL
   );
   ```

2. Add a tiny reusable helper in **`app.py`**:
   ```python
   def get_random_row(table):
       """Return one random row (or None if the table is empty)."""
       conn = get_db_connection()
       row = conn.execute(
           f'SELECT * FROM {table} ORDER BY RANDOM() LIMIT 1'
       ).fetchone()
       conn.close()
       return row
   ```
   > ⚠️ `table` is put into SQL **with f-strings** — only ever safe because we
   > hardcode the table name in our own code. **Never** build it from user input.

3. Use it in `index()`:
   ```python
   ted_talk = get_random_row('ted_talks')
   meme    = get_random_row('memes')
   return render_template('index.html', announcements=announcements,
                          ted_talk=ted_talk, meme=meme)
   ```

4. Render it (guard against `None` when the table is empty):
   ```html
   {% if ted_talk %}
     <div class="spotlight">
       <img src="{{ url_for('static', filename=ted_talk['thumbnail']) }}" alt="">
       <h3>{{ ted_talk['title'] }}</h3>
       <a href="{{ ted_talk['url'] }}" target="_blank">Watch</a>
     </div>
   {% endif %}
   ```

### ✅ Checkpoint
- [ ] Refresh 5 times → you see **different** talks/memes.
- [ ] Images still show with Wi-Fi off (they're local files).

---

# Day 7 — Forms: letting users add data

### Goal
An "Add yourself" form on `/directory` that writes to the database.

### Concepts
- **GET vs POST**: GET *reads* a page; POST *sends* data to be stored.
- **`request.form`**: the dictionary of what the user typed.
- **Validation**: never trust input — check it before saving.
- **`flash()`**: a one-time message shown after a redirect ("Profile added!").
- **`redirect()` + `url_for()`**: send the user back after a successful POST.
  This is the **Post/Redirect/Get** pattern — it stops the "re-submit the
  form?" warning when someone refreshes.

### Steps

1. Add the columns to the `students` table:
   ```sql
   website TEXT DEFAULT '',  facebook TEXT DEFAULT '',
   instagram TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT ''
   ```

2. Add the GET route (the page) and the POST route (the handler):
   ```python
   from flask import render_template, request, redirect, url_for, flash

   app.secret_key = 'dev-secret'   # required for flash()

   @app.route('/directory')
   def directory():
       conn = get_db_connection()
       students = conn.execute('SELECT * FROM students ORDER BY name ASC').fetchall()
       conn.close()
       return render_template('directory.html', students=students)


   @app.route('/directory/add', methods=['POST'])   # POST only!
   def add_student():
       name = request.form.get('name', '').strip()   # .strip() trims spaces
       if not name:
           flash('Please enter your name.', 'error')
           return redirect(url_for('directory'))

       conn = get_db_connection()
       conn.execute(
           'INSERT INTO students (name, interests, role) VALUES (?, ?, ?)',
           (name, request.form.get('interests', '').strip(), 'Student')
       )
       conn.commit()
       conn.close()

       flash(f'Welcome, {name}!', 'success')
       return redirect(url_for('directory'))
   ```

3. The form in **`templates/directory.html`**:
   ```html
   <form action="{{ url_for('add_student') }}" method="POST">
     <label for="name">Your name</label>
     <input class="nes-input" type="text" id="name" name="name" required>
     <button class="nes-btn is-primary" type="submit">Add</button>
   </form>
   ```
   > `name="name"` is what the server reads — the `id` is only for the `<label>`.

4. Show the flash messages in **`base.html`** (they disappear on the next load):
   ```html
   {% with messages = get_flashed_messages(with_categories=true) %}
     {% for category, message in messages %}
       <div class="flash flash-{{ category }}">{{ message }}</div>
     {% endfor %}
   {% endwith %}
   ```

### ✅ Checkpoint
- [ ] Submit with an empty name → red message, nothing saved.
- [ ] Submit a real name → green message, card appears.
- [ ] Refresh → the message is gone but the student remains (Post/Redirect/Get).

---

# Day 8 — Relationships: linking Events to Students

### Goal
Students post **events**; each event points at the student who organized it.

### Concepts
- **Primary key (PK)**: the unique `id` of a row.
- **Foreign key (FK)**: a column storing *another table's* id, e.g.
  `events.organizer_id` → `students.id`.
- **`JOIN`**: stitch two tables together so one query returns both.
- **Grouping in Python**: collect related rows into a dict so templates stay simple.

### Steps

1. Add both tables to **`schema.sql`**:
   ```sql
   CREATE TABLE IF NOT EXISTS events (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       organizer_id INTEGER NOT NULL,          -- FK → students.id
       title TEXT NOT NULL,
       link TEXT DEFAULT '',
       description TEXT DEFAULT '',
       event_date TEXT DEFAULT '',
       location TEXT DEFAULT '',
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (organizer_id) REFERENCES students(id)
   );

   CREATE TABLE IF NOT EXISTS event_requests (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       event_id INTEGER NOT NULL,              -- FK → events.id
       requester_name TEXT NOT NULL,
       message TEXT DEFAULT '',
       user_id INTEGER,        -- reserved: future login will fill this
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (event_id) REFERENCES events(id)
   );
   ```

2. Read events **with** the organizer's name in one query:
   ```python
   def get_events_with_requests():
       conn = get_db_connection()
       events = conn.execute(
           'SELECT events.*, students.name AS organizer_name '
           'FROM events JOIN students ON events.organizer_id = students.id '
           'ORDER BY events.id DESC'
       ).fetchall()
       requests = conn.execute('SELECT * FROM event_requests ORDER BY id ASC').fetchall()
       conn.close()

       # group: {event_id: [requests...]} so the template can look up fast
       grouped = {}
       for r in requests:
           grouped.setdefault(r['event_id'], []).append(r)
       return events, grouped
   ```
   > `ON events.organizer_id = students.id` is the join condition: "match an
   > event to the student whose id equals the event's organizer_id".

3. Wire it up in **`app.py`**:
   ```python
   @app.route('/schedule')
   def schedule():
       events, grouped = get_events_with_requests()
       conn = get_db_connection()
       students = conn.execute('SELECT id, name FROM students ORDER BY name').fetchall()
       conn.close()
       return render_template('schedule.html', events=events,
                              requests_by_event=grouped, students=students)


   @app.route('/schedule/add', methods=['POST'])
   def add_event():
       organizer_id = request.form.get('organizer_id', '').strip()
       title        = request.form.get('title', '').strip()
       if not organizer_id or not title:
           flash('Choose an organizer and enter a title.', 'error')
           return redirect(url_for('schedule'))
       conn = get_db_connection()
       conn.execute('INSERT INTO events (organizer_id, title, link, description, '
                    'event_date, location) VALUES (?, ?, ?, ?, ?, ?)',
                    (organizer_id, title, request.form.get('link', '').strip(),
                     request.form.get('description', '').strip(),
                     request.form.get('event_date', '').strip(),
                     request.form.get('location', '').strip()))
       conn.commit(); conn.close()
       flash('Event added!', 'success')
       return redirect(url_for('schedule'))


   @app.route('/event/<int:event_id>/join', methods=['POST'])
   def join_event(event_id):
       name = request.form.get('requester_name', '').strip()
       conn = get_db_connection()
       if not name or conn.execute('SELECT id FROM events WHERE id = ?',
                                   (event_id,)).fetchone() is None:
           conn.close()
           flash('Please type your name.', 'error')
           return redirect(url_for('schedule', _anchor=f'event-{event_id}'))
       conn.execute('INSERT INTO event_requests (event_id, requester_name, message) '
                    'VALUES (?, ?, ?)',
                    (event_id, name, request.form.get('message', '').strip()))
       conn.commit(); conn.close()
       flash('Request sent!', 'success')
       return redirect(url_for('schedule', _anchor=f'event-{event_id}'))
   ```

4. In the organizer dropdown, the value stored is the **id** (not the name):
   ```html
   <select name="organizer_id" required>
     {% for s in students %}
       <option value="{{ s['id'] }}">{{ s['name'] }}</option>
     {% endfor %}
   </select>
   ```

5. Link back the other way — on `/student/<id>` list that student's events:
   ```python
   events = conn.execute('SELECT * FROM events WHERE organizer_id = ? ORDER BY id DESC',
                         (student_id,)).fetchall()
   ```

### ✅ Checkpoint
- [ ] Add an event choosing yourself → it appears on `/schedule`.
- [ ] Clicking the organizer's name takes you to their profile.
- [ ] Their profile lists that event → directory and schedule are **linked**.
- [ ] "Ask to go" adds a name under the event.

---

# Day 9 — A real month calendar + popup detail view

### Goal
Events shown on a **calendar grid for the current month**, with a popup when
you click one.

### Concepts
- **`datetime.now()`**: the machine's current date/time.
- **`calendar.Calendar(firstweekday=SUNDAY)`**: builds the month's weeks.
- **`monthdayscalendar(year, month)`**: returns weeks of day numbers, `0` = empty cell.
- **Extracting a day from text**: events store free text like `"Fri 21 Oct"`,
  so we find the number with a regular expression.
- **Client-side interactivity**: a little JavaScript shows/hides a popup — no
  page reload needed.

### Steps

1. In **`app.py`**, build the calendar:
   ```python
   from datetime import datetime
   import calendar, re

   @app.route('/schedule')
   def schedule():
       events, grouped = get_events_with_requests()
       # ... (students query as before)

       now  = datetime.now()
       cal  = calendar.Calendar(firstweekday=calendar.SUNDAY)
       weeks = cal.monthdayscalendar(now.year, now.month)   # [[0,0,0,1,2,3,4], ...]

       # find the day number inside "Fri 21 Oct" → 21
       events_by_day = {}
       for ev in events:
           found = re.findall(r'\b(\d{1,2})\b', ev['event_date'] or '')
           if found:
               day = int(found[-1])
               if 1 <= day <= 31:
                   events_by_day.setdefault(day, []).append(ev)

       return render_template('schedule.html', events=events,
                              requests_by_event=grouped, students=students,
                              weeks=weeks, current_month=now.strftime('%B %Y'),
                              today=now.day, events_by_day=events_by_day)
   ```

2. Render the 7-column grid — **`templates/schedule.html`**:
   ```html
   <table class="month-calendar">
     <thead><tr>
       <th>Sun</th><th>Mon</th><th>Tue</th><th>Wed</th>
       <th>Thu</th><th>Fri</th><th>Sat</th>
     </tr></thead>
     <tbody>
       {% for week in weeks %}
       <tr>
         {% for day in week %}
           <td class="calendar-cell {% if day == today %}is-today{% endif %}">
             {% if day != 0 %}
               <div class="day-number">{{ day }}</div>
               {% for ev in events_by_day.get(day, []) %}
                 <button class="event-chip-btn" data-ev="ev-{{ ev.id }}">{{ ev['title'] }}</button>
               {% endfor %}
             {% endif %}
           </td>
         {% endfor %}
       </tr>
       {% endfor %}
     </tbody>
   </table>
   ```
   > `day == 0` means "this cell belongs to the previous/next month" — we skip it.

3. Render one hidden popup per event (below the table):
   ```html
   {% for ev in events %}
     <div class="event-popup" id="ev-{{ ev.id }}">
       <div class="event-popup-content nes-container is-rounded">
         <button class="event-popup-close" data-close="ev-{{ ev.id }}">X</button>
         <h3>{{ ev['title'] }}</h3>
         <p>by {{ ev['organizer_name'] }}</p>
         <p>{{ ev['description'] }}</p>
       </div>
     </div>
   {% endfor %}
   ```

4. The JavaScript that makes it a popup (add before `</body>`):
   ```html
   <script>
   document.addEventListener('DOMContentLoaded', () => {
     document.querySelectorAll('.event-chip-btn').forEach(btn =>
       btn.addEventListener('click', () =>
         document.getElementById(btn.dataset.ev).classList.add('show')));
     document.querySelectorAll('.event-popup-close').forEach(btn =>
       btn.addEventListener('click', () =>
         document.getElementById(btn.dataset.close).classList.remove('show')));
     document.querySelectorAll('.event-popup').forEach(p =>
       p.addEventListener('click', e => { if (e.target === p) p.classList.remove('show'); }));
   });
   </script>
   ```

5. The CSS that hides it until `.show` is added:
   ```css
   .event-popup     { display: none; position: fixed; inset: 0;
                      background: rgba(0,0,0,.5); z-index: 1000; }
   .event-popup.show{ display: flex; align-items: center; justify-content: center; }
   .event-popup-content { max-width: 600px; width: 90%; max-height: 90vh;
                          overflow-y: auto; background: #fff8dc; }
   ```

### ✅ Checkpoint
- [ ] The header shows the **real current month** (not hardcoded).
- [ ] Today's cell is highlighted.
- [ ] Clicking an event opens a popup; **X** and clicking the dark area close it.

---

# Day 10 — Testing, going offline, and shipping

### Goal
Prove it works, make sure it never needs internet, and push to GitHub.

### Concepts
- **`test_client()`**: Flask lets you "visit" pages from Python without a browser.
- **Offline audit**: search your code for `http://` / `https://` to find anything
  that would break with Wi-Fi off.
- **Branches**: a branch is an independent copy of the project to work on safely.

### Steps

1. **Test every route without a browser:**
   ```python
   # save as test_smoke.py and run: python test_smoke.py
   from app import app
   c = app.test_client()
   paths = ['/', '/lhr', '/lhr/game/1', '/directory', '/schedule', '/student/1']
   for p in paths:
       r = c.get(p)
       assert r.status_code == 200, f'{p} -> {r.status_code}'
       print(f'OK  {p}')
   ```

2. **Offline audit** — nothing should be loaded from the internet:
   ```bash
   grep -rn "https\?://" templates/ | grep -v "href=" 
   # external links inside <a href> are FINE (they're optional clicks);
   # anything in <link>, <script src> or <img src> must be local!
   ```

3. **Test on a phone** (same Wi-Fi or hotspot):
   ```bash
   hostname -I        # find your IP
   # on the phone:  http://<that-ip>:5000
   ```

4. **Git + GitHub:**
   ```bash
   git init
   git branch -M AiGenprototype        # work on your own branch
   git add .
   git commit -m "Initial prototype"
   gh repo create C_Dungeons_Dragons --private --source=. --remote=origin
   git push -u origin AiGenprototype
   ```
   > GitHub **disallows** `!` and `&` in repository names, so
   > `C!_Dungeons_&_Dragons` becomes `C_Dungeons_Dragons`.

5. **Demo checklist (do this the night before):**
   - [ ] `python seed.py` → clean data, ids restart at 1.
   - [ ] `python app.py` → server starts.
   - [ ] Open all 6 pages, refresh the home page to see the spotlight change.
   - [ ] Resize the window / check on a phone (it must not break).
   - [ ] Wi-Fi **off** → reload → still fully styled.
   - [ ] Keep the terminal open during the demo (closing it stops the server).

### ✅ Checkpoint
- [ ] All routes return HTTP 200.
- [ ] Works with the internet disconnected.
- [ ] Code is on the `AiGenprototype` branch on GitHub.

---

## Roles & workload (for the report)

| Role | What they own | Files |
|------|---------------|-------|
| **Team Lead / Architect** | Routes & app structure | `app.py` |
| **Database Specialist** | Schema, connections | `schema.sql`, `database.py` |
| **Frontend Developer** | Layout, theme, offline assets | `templates/*`, `static/*` |
| **Logic & Data Helper** | Spotlight randomness, calendar math | helpers in `app.py` |
| **Testing & Presentation Lead** | Seed data, tests, docs | `seed.py`, `SETUP_REPORT.md` |

---

## Roadmap after the midterm

1. **User authentication** — replace "type your name" with real logins. The
   `event_requests.user_id` column is already reserved for this.
2. **PWA** — add a `manifest.json` + service worker so students can install it.
3. **Community integrations** — Minecraft server / class community hub.

---

*End of Project Journey. If you can explain each Day's checkpoint out loud,
you understand how the whole project works.*
