![C1 Hub logo](docs/Logo/Logo.png)

# C1 Hub + Attendance

A Flask + PostgreSQL app for class C1 at Egypt-Japan KOSEN. It combines the
student hub (bulletin, games, directory, events, news) with a staff-only
attendance checklist and bilingual exports.

This README is for students helping with development. Read it before changing
code, and ask before adding a new library or a new public data field.

## Tech stack

- Python / Flask app factory with blueprints
- SQLAlchemy + Flask-Migrate
- Flask-Login for staff login
- Flask-WTF for CSRF protection
- PostgreSQL/Neon in production, SQLite locally
- NES.css pixel UI, vendored locally
- pytest for Python tests, ESLint for JavaScript

## Project map

```text
app/
├── __init__.py        app factory, error pages, health check
├── config.py          environment-driven settings
├── models.py          database models
├── security.py        safe URL and media helpers
├── auth/              staff login/logout
├── hub/               public bulletin, directory, events, calendar
├── attendance/        daily checklist, weekly report, PNG/Excel/CSV exports
├── admin/             staff management panel
├── news/              RSS feeds
├── templates/         Jinja pages
└── static/            CSS, JavaScript, fonts, images
tests/                 pytest suite
docs/                  design specs and implementation plans
scripts/roster.js      the class roster seed data
migrations/            database migrations
wsgi.py                production entry point
```

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and leave DATABASE_URL empty for local SQLite before the next command.
flask --app wsgi db upgrade
flask --app wsgi seed-roster
flask --app wsgi create-admin --username teacher
flask --app wsgi run --debug
```

Open <http://127.0.0.1:5000>.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs session cookies and CSRF tokens. Use a long random value. |
| `DATABASE_URL` | PostgreSQL URL, or empty for local SQLite. |
| `FLASK_ENV` | `development` locally, `production` on Railway. |
| `FLASK_APP` | `wsgi.py`. |
| `TZ` | `Africa/Cairo` (or your local timezone). |

Never commit `.env`, passwords, or database dumps.

## Development rules

1. **Read the design before changing behavior.** Specs are in
   `docs/superpowers/specs/`; implementation plans are in
   `docs/superpowers/plans/`.
2. **Make small, focused changes.** One feature or fix per commit.
3. **Test-first for behavior changes.** Add a failing test, make it pass, then
   commit.
4. **Run the whole test suite before you finish:** `.venv/bin/python -m pytest -q`.
5. **Run the JavaScript linter if you touch JS:** `npm run lint:js`.
6. **Use migrations for model changes.** Run `flask --app wsgi db migrate -m "..."`
   and `flask --app wsgi db upgrade`. Never edit the production database by hand.
7. **Follow existing patterns.** Reuse helpers such as `safe_url` and
   `media_url`; do not add a new framework for a small change.
8. **Do not commit secrets.** `.env`, local databases, and local notes are
   ignored.
9. **Preserve privacy.** Student email is public; student phone numbers are
   staff-only. Join requests are public. Do not add public personal data
   without reviewing the privacy impact first.
10. **Treat user-supplied URLs as untrusted.** Only `http`/`https` links may be
    rendered; pass them through `safe_url`.
11. **Keep attendance CSV compatible.** The header and weekly-upload format must
    not change without updating the spec, tests, and documentation.
12. **Keep commits readable.** Explain what changed and why, not just which
    files changed.

## Making a change

```bash
git switch -c your-change-name
# write a failing test
.venv/bin/python -m pytest tests/test_the_feature.py -q
# implement the smallest fix
.venv/bin/python -m pytest -q
npm run lint:js
git add <files>
git commit -m "type: short description"
```

Push the branch and open a pull request. Do not commit `COMMANDS.md`, `.env`,
local database files, or generated caches.

## Tests and lint

```bash
.venv/bin/python -m pytest -q
npm run lint:js
```

## Attendance exports

The daily CSV header is stable:

```csv
date,student_id,name_en,name_ar,status,note
2026-10-22,1,Abdelrahman Khaled Mahdy,عبد الرحمن خالد مهدي,present,
```

PNG and Excel use the bilingual reference design and download as
`YYYY-MM-DD-c1Class-attendance.*`. The CSV name remains
`YYYY-MM-DD-c1-attendance.csv`.

## Deployment

The live app runs on Railway at
<https://cdungeonsdragons-production.up.railway.app>. Pushing `main` deploys
automatically.

- Build: Railpack detects Python and installs `requirements.txt`.
- Start: `gunicorn wsgi:app`
- Health check: `/health`
- Production Python: 3.13
- Runtime system package: `libraqm0` (required for Arabic shaping in PNGs)

Run database commands from the Railway shell:

```bash
flask --app wsgi db upgrade
flask --app wsgi create-admin --username teacher
```

Check the live app:

```bash
curl https://cdungeonsdragons-production.up.railway.app/health
```

Expected: `{"status":"ok","database":"ok"}`

## Backups

```bash
BACKUP=backup-$(date +%F).sql
pg_dump "$DATABASE_URL" > "$BACKUP"
psql "$DATABASE_URL" < "$BACKUP"
```

Back up regularly. A free database is not a backup.

## More docs

- Attendance MVP design: `docs/superpowers/specs/2026-10-22-c1-hub-attendance-mvp-design.md`
- Export parity design: `docs/superpowers/specs/2026-10-28-attendance-export-parity-design.md`
- Database schema: `docs/DATABASE_SCHEMA.md`
