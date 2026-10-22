# Attendance Exports, LATE Status and Weekly-from-DB — Design

**Date:** 2026-10-22
**Status:** Approved for implementation
**Scope:** Second batch, extends the C1 Hub + Attendance MVP

## Goal

Add a `late` attendance status, server-side Excel and PNG exports with the
project's pixel look, and a weekly report computed directly from saved daily
sessions. Finish the Render deployment documentation.

## Decisions

| Decision | Choice |
|---|---|
| Export location | Server-side (Python generates the files) |
| Export content | Attended / Late / Absent sections, absentee highlighting |
| Export style | Project pixel palette |
| Late counting | Counts as present for the weekly percentage, tracked separately |
| Weekly from DB | Pick a week start (Sunday), load the five following days |
| CSV upload | Kept as a fallback, unchanged |
| PDF | Browser print, no new dependency |

## Non-goals

Arabic UI, admin panel, real date column for events, student accounts,
multi-class, and audit history remain out of scope.

## 1. LATE status

`attendance_records.status` accepts `present`, `absent`, or `late`.

- The daily checklist offers three choices per student: Present, Late, Absent.
  Default remains Present.
- The service layer accepts a mapping of student id to status instead of a set
  of present ids.
- The daily CSV keeps the same columns; `status` may now be `late`.
- Weekly validation accepts `late`.

Aggregation rule: `late` counts toward the present total for the percentage,
and is additionally counted in its own `late` column.

## 2. Excel and PNG export

New staff-only routes:

- `GET /attendance/export.xlsx?date=YYYY-MM-DD`
- `GET /attendance/export.png?date=YYYY-MM-DD`

**Excel** (openpyxl), one sheet:

- Title block with the date and class name.
- An `ATTENDED` section listing present students.
- A `LATE` section listing late students (amber fill, bold).
- An `ABSENT` section listing absent students (yellow fill, bold).
- Header row styling using the project palette.

**PNG** (Pillow):

- Poster image: dark pixel background, title, date, and the Absent plus Late
  names in a large bold font.
- Uses the palette `#BE1A1A`, `#D0311E`, `#F7D87F`, `#F8EBAB`.
- A default bitmap/monospace font is used when no custom font is bundled, so
  the export never fails on a fresh host.

A shared helper collects a day's records grouped by status so Excel and PNG
(and any future export) reuse the same data.

## 3. Weekly from DB

New staff-only route:

- `GET /attendance/week/saved?start=YYYY-MM-DD`

Behaviour:

- Start defaults to the most recent Sunday.
- The app loads the five consecutive calendar days beginning at that Sunday.
- For each day it reads the saved `AttendanceSession` and its records.
- Missing days are reported as warnings, not errors.
- Per-student output matches the upload path: present, late, absent,
  percentage (late counted as present), absent dates.
- The same aggregation function powers both the upload path and the DB path.
- The existing `/attendance/week` upload flow is unchanged.

## 4. Deployment

- Keep `render.yaml`, `gunicorn wsgi:app`, `flask --app wsgi db upgrade`.
- README gains a deploy checklist and the daily/weekly usage steps.
- `/health` remains the Render health check.

## 5. Testing

- Late: status validation, daily CSV contains `late`, aggregation counts late
  as present and reports the late column.
- Excel: openpyxl opens the generated file and finds the three section headers.
- PNG: response is a non-empty PNG with the correct content type.
- Weekly-from-DB: a seeded week aggregates correctly; missing days reported.

## Done criteria

1. Teacher can mark a student Late and save it.
2. Excel download contains Attended, Late and Absent sections.
3. PNG download renders with the pixel palette.
4. Weekly-from-DB matches the upload path for the same data.
5. All existing tests pass, plus the new ones.
6. README documents deployment and usage.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Extra dependencies break deploy | Pin openpyxl and Pillow; they are pure/common wheels |
| Font missing on host for PNG | Fall back to Pillow's default font |
| Late counting confuses reports | One documented rule and a visible Late column |
| Scope creep | Non-goals explicit |
