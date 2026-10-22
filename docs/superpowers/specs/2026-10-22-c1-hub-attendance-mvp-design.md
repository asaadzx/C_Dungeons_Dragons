# C1 Hub + Attendance MVP — Design

**Date:** 2026-10-22
**Status:** Approved for implementation
**Scope:** Class-usable MVP for 34 students

## Goal

Combine the existing C! RAS Hub (Flask + SQLite) and the static
`class-c1-attendance` app into one Flask application with a shared PostgreSQL
database, teacher-only login, server-saved daily attendance, and a weekly CSV
upload report.

The app must remain free to run for one class using Render Free + Neon Free.

## Decisions

| Decision | Choice |
|---|---|
| Target | Class-usable MVP, not school-wide |
| Architecture | Single Flask app + SQLAlchemy |
| Hosting | Render Free web service |
| Database | Neon Free PostgreSQL |
| Login | Teacher/admin only; students browse without accounts |
| Attendance | One checklist per day |
| Weekly report | Upload five daily CSV files |
| Roster | Import the real 34 students (English + Arabic) |
| Offline | Online-only; no sync or service worker |
| UI | Keep the existing NES.css pixel style |

## Non-goals

Student accounts, offline sync, per-subject attendance periods, multi-school
tenancy, full Arabic/RTL UI, audit history, email notifications, and advanced
reports are out of scope for this MVP.

## Architecture

```text
c1-school-hub/
├── app/
│   ├── __init__.py        # app factory
│   ├── config.py          # env-driven configuration
│   ├── extensions.py      # db, login_manager, csrf
│   ├── models.py          # SQLAlchemy models
│   ├── auth/              # login/logout routes
│   ├── hub/               # bulletin, games, directory, events
│   ├── attendance/        # daily checklist + weekly upload
│   ├── admin/             # students, users, announcements
│   ├── services/          # CSV parsing + weekly aggregation
│   ├── templates/
│   └── static/
├── migrations/
├── tests/
├── scripts/seed.py
├── wsgi.py
├── requirements.txt
└── render.yaml
```

The current repository becomes the canonical monorepo. The attendance
repository is imported into it; the static app is not deployed separately.

## Data model

Keep the existing tables: `announcements`, `lhr_games`, `ted_talks`, `memes`,
`events`, `event_requests`.

Replace the five sample students with the real roster:

### students
- `id` integer primary key
- `name_en` text not null
- `name_ar` text not null default ''
- `interests` text not null default ''
- `website`, `facebook`, `instagram`, `phone`, `email` text default ''
- `active` boolean not null default true

### users
- `id` integer primary key
- `username` text unique not null
- `password_hash` text not null
- `role` text not null, allowed: `admin`, `teacher`
- `active` boolean not null default true

### attendance_sessions
- `id` integer primary key
- `date` date unique not null
- `created_by` integer references `users.id`
- `created_at`, `updated_at` timestamps

### attendance_records
- `id` integer primary key
- `session_id` integer references `attendance_sessions.id`
- `student_id` integer references `students.id`
- `status` text not null, allowed: `present`, `absent`
- `note` text default ''
- unique constraint on `(session_id, student_id)`

`events.organizer_id` continues to reference `students.id`. Events and
announcements are created by logged-in staff in this MVP.

## Authentication and permissions

- Flask-Login for sessions.
- Passwords hashed with Werkzeug.
- Flask-WTF for CSRF on every form.
- Secret key, database URL, and environment read from env vars.
- Public routes: bulletin, games, directory, profiles, schedule viewing,
  join requests, health check.
- Protected routes: all attendance pages, weekly upload, student management,
  event creation, announcement management.
- Remove the public "Add yourself" form and self-selected Admin role. The
  teacher manages the roster.

## Daily attendance flow

Route: `GET/POST /attendance`

1. Date defaults to today; teacher may choose another date.
2. All active students are checked present by default.
3. Teacher unchecks absent students and optionally adds a note.
4. Save creates or updates the `attendance_sessions` row for that date and
   upserts all 34 `attendance_records`.
5. The page lists recent saved days.
6. Export controls:
   - CSV (required for weekly upload)
   - Excel (reuse the existing `xlsx-js-style` bundle)
   - PNG (reuse the existing canvas export)
   - PDF via browser print

CSV format:

```csv
date,student_id,name_en,name_ar,status,note
2026-10-22,1,Abdelrahman Khaled Mahdy,عبد الرحمن خالد مهدي,present,
```

## Weekly report flow

Route: `GET/POST /attendance/week`

1. Teacher uploads five daily CSV files.
2. Server validates:
   - valid ISO date in every row
   - exactly one date per file
   - unique dates across files
   - all student IDs exist in the roster
   - status is `present` or `absent`
   - no duplicate student within a file
3. On validation failure, show the file and row that failed; do not partially
   save.
4. On success, show per student:
   - present days
   - absent days
   - weekly percentage
   - absent dates
5. Show class totals.
6. Offer the weekly summary as a CSV download.

The MVP computes the report in memory from the uploaded files. It does not
require the daily records to already exist in the database, but using the same
export format guarantees they match.

## Error handling

- Friendly error pages for 404 and 500.
- Form validation errors re-render the form with messages.
- Database connection errors return a clear 503 page.
- CSV upload errors are shown inline and never crash the request.
- `/health` returns a JSON status and checks the database connection.

## Deployment

- `gunicorn` production server.
- `render.yaml` defines the web service and health check.
- Required environment variables:
  - `DATABASE_URL` (Neon Postgres URL)
  - `SECRET_KEY`
  - `FLASK_APP=wsgi.py`
  - `FLASK_ENV=production`
- Neon requires SSL; the URL must include `sslmode=require`.
- Run `flask db upgrade` as the Render release command.
- README documents weekly `pg_dump` backups and how to restore.

## Testing

Use pytest with an in-memory or temporary SQLite database for tests.

Minimum tests:

1. App factory starts and `/health` responds.
2. Login rejects bad credentials and accepts a valid teacher.
3. Protected attendance route redirects anonymous users.
4. Saving attendance creates one session and 34 records.
5. Re-saving the same date updates rather than duplicates.
6. CSV export contains the agreed header and rows.
7. Weekly upload aggregates five valid files correctly.
8. Weekly upload rejects unknown students, duplicate dates, and bad statuses.
9. Public hub routes still return 200.

## Done criteria

1. App runs locally with the real 34-student roster.
2. Teacher can log in and manage daily attendance.
3. Daily CSV export works.
4. Five CSVs produce a correct weekly report.
5. Existing hub pages still work.
6. Critical security issues from the audit are fixed.
7. `pytest` passes.
8. App deploys to Render and connects to Neon.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Render sleeps on free tier | Add optional free uptime pinger; accept cold start |
| Free tier limits change | Document a migration path to a paid tier or VPS |
| Free database has no long-term backup | Weekly `pg_dump` and documented restore |
| Real student names are personal data | No public phone/email by default; teacher-managed roster |
| CSV format drifts | One documented schema and validation on upload |
| Scope creep | Non-goals are explicit; defer student accounts and offline mode |
