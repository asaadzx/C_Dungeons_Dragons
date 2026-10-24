# C1 RAS Hub — Command Cheat Sheet

Local notes. This file is gitignored, so it will never be pushed to GitHub.

All commands are run from the project root:

```bash
cd "/home/asaad/Documents/MyStuff/C!_Dungeons_&_Dragons/c1_ras_hub"
```

The `.venv/bin/` prefix runs tools from the virtual environment without
activating it. If you prefer, run `source .venv/bin/activate` first and then
drop the prefix.

---

## Run the site locally

```bash
SECRET_KEY=local-dev-key FLASK_ENV=development .venv/bin/python wsgi.py
```

- Opens on http://127.0.0.1:5000
- On the same Wi-Fi, phones can use http://<your-local-ip>:5000
- Stop with `Ctrl+C`

---

## Create or reset an admin (teacher) account

Interactive (prompts for password, hidden):

```bash
.venv/bin/flask --app wsgi create-admin --username teacher
```

Non-interactive (good for scripts; replace the password):

```bash
.venv/bin/flask --app wsgi create-admin --username teacher --password "changeme123"
```

Running it again with an existing username resets that account's password
and makes sure it is an active admin.

---

## Seed data

```bash
# Import the 34-student roster from scripts/roster.js
.venv/bin/flask --app wsgi seed-roster

# Add the default LHR games
.venv/bin/flask --app wsgi seed-lhr

# Add a bulletin announcement
.venv/bin/flask --app wsgi add-announcement \
  --title "Field trip" --content "Sunday at 9am" --category News

# Add class news instead
.venv/bin/flask --app wsgi add-announcement \
  --title "Class update" --content "..." --category "Class News"
```

`--category` accepts `News` or `Class News`.

---

## Database migrations

Only needed when a model (column/table) changes.

```bash
# Create a migration after editing app/models.py
.venv/bin/flask --app wsgi db migrate -m "describe the change"

# Apply pending migrations to the database
.venv/bin/flask --app wsgi db upgrade

# Check which migration is current
.venv/bin/flask --app wsgi db current

# See migration history
.venv/bin/flask --app wsgi db history
```

---

## Tests and lint

```bash
# Run the test suite
.venv/bin/python -m pytest -q

# Run the JavaScript linter
npm run lint:js
```

---

## Production (Railway)

The site deploys automatically from the `main` branch. Push:

```bash
git add -A
git commit -m "message"
git push origin main
```

Run database commands against production from the **Railway Shell**:

```bash
flask --app wsgi db upgrade
flask --app wsgi create-admin --username teacher
```

Check the live app:

```bash
curl https://cdungeonsdragons-production.up.railway.app/health
```

Expected answer: `{"status":"ok","database":"ok"}`

---

## Git basics

```bash
git status                 # what changed
git log --oneline -10      # recent commits
git diff                   # unstaged changes
git push origin main       # deploy the current branch
```
