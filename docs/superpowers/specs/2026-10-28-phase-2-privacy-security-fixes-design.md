# Phase 2 Privacy, Security, and Small Fixes — Design

**Date:** 2026-10-28
**Status:** Approved for implementation
**Scope:** First Phase 2 sub-project. Privacy, URL safety, database-error handling,
saved-week CSV export, and deployment/docs cleanup.

## Goal

Close the highest-value privacy and reliability gaps without changing the data
model, authentication model, or public join-request behavior. Keep the batch
small enough to implement and verify in one cycle.

## Decisions

| Decision | Choice |
|---|---|
| Contact privacy | Email stays public; phone is visible only to logged-in staff |
| Join requests | Stay public, including requester names and messages |
| Event form | Hidden from logged-out visitors; show a staff-login notice |
| Event links | Render only `http`/`https`; reject unsafe links on create/edit |
| Saved-week CSV | Reuse `/attendance/week/export.csv?start=YYYY-MM-DD` |
| Database failures | Friendly 503 page for HTML routes; JSON 503 from `/health` |
| README | Track in git and update Render references to Railway |
| Schema docs | Commit the existing schema Markdown and diagram assets |
| Stale deployment config | Remove `render.yaml` |
| Database migration | None |

## Behavior

### Contact information

- Directory cards and student profiles continue to show email to everyone.
- Phone numbers render only when `current_user.is_authenticated`.
- Anonymous responses must not contain student phone numbers in their HTML.
- The “no contact information” empty state must be based only on information
  visible to the current visitor. An anonymous profile with a phone but no other
  contact fields shows the empty state rather than an empty contact block.

### Event form and links

- Anonymous visitors see a short notice linking to staff login instead of the
  “Post an event” form.
- Logged-in staff see the existing form.
- Event links are rendered only through the existing `safe_url` filter.
- Creating or editing an event with a non-empty link that is not an absolute
  `http` or `https` URL is rejected with a clear flash message. No other event
  fields are saved in that request.
- Links already stored with unsafe schemes remain in the database but are never
  rendered as clickable links.

### Saved-week CSV

- `GET /attendance/week/export.csv?start=YYYY-MM-DD` computes
  `aggregate_saved_week(start)` and downloads that summary.
- `GET /attendance/week/export.csv` keeps the existing uploaded-five-files
  behavior and reads `session["weekly_summary"]`.
- An invalid `start` value flashes an error and redirects to the saved-week page
  instead of silently exporting a different week.
- Weekly CSV responses include `Cache-Control: no-store`.

### Database failures

- A `SQLAlchemyError` rolls back the session, logs the failure, and renders
  `errors/503.html` with HTTP 503.
- `/health` catches database errors and returns HTTP 503 with
  `{"status": "error", "database": "error"}` instead of allowing an HTML 500.
- Existing 404 and 500 handling is unchanged.

### Documentation and deployment

- `README.md` is removed from `.gitignore` and committed.
- README deployment instructions describe Railway, not Render, and match the
  actual start command, health check, and URL.
- The existing database schema documentation and diagram assets are committed.
- `render.yaml` is removed because Railway is the live deployment target.
- `COMMANDS.md` remains local-only and ignored.

## Architecture

| File | Change |
|---|---|
| `app/hub/routes.py` | Validate event links with `safe_url` before create/edit |
| `app/templates/schedule.html` | Staff-only event form; filter event links |
| `app/templates/directory.html` | Email public; phone staff-only; visible-contact empty state |
| `app/templates/profile.html` | Email public; phone staff-only; visible-contact empty state |
| `app/__init__.py` | `SQLAlchemyError` handler; `/health` JSON failure response |
| `app/templates/errors/503.html` | Friendly database-unavailable page |
| `app/attendance/routes.py` | Saved-week branch in `weekly_export`; `no-store` |
| `app/templates/attendance/week_saved.html` | Export link includes `start` |
| `README.md` | Tracked and updated for Railway |
| `.gitignore` | Stop ignoring README |
| `render.yaml` | Delete |
| `docs/` | Commit existing schema documentation and diagram assets |

No model changes, no migrations, and no new JavaScript dependencies.

## Error Handling

- Unsafe event link: flash `Event link must be a full http:// or https:// URL.`
  and redirect without saving.
- Invalid saved-week start: flash `Invalid week start date.` and redirect to
  `/attendance/week/saved`.
- Missing uploaded weekly summary: preserve the current “Upload five daily files
  first.” behavior.
- Database error: rollback and render 503. No partial writes should be
  committed.
- Missing saved attendance days remain allowed; the existing missing-days notice
  stays unchanged.

## Testing

Add or update tests for:

1. Anonymous directory/profile HTML contains email but not phone.
2. Logged-in directory/profile HTML contains both email and phone.
3. Anonymous profile with only a phone shows the contact empty state.
4. Anonymous schedule hides the event form and shows the login notice.
5. Logged-in schedule shows the event form.
6. Creating an event with a `javascript:` link is rejected and no event is saved.
7. Editing an event to an unsafe link is rejected and the old link remains.
8. An existing unsafe link is not rendered as a clickable link.
9. Saved-week CSV with `start` returns the saved summary as a download.
10. Invalid saved-week start redirects with an error.
11. Weekly CSV has `Cache-Control: no-store`.
12. `/health` returns JSON 503 when the database query fails.
13. A database failure on an HTML route renders `errors/503.html` with 503.
14. All existing tests remain green.

## Non-Goals

- Roster CRUD.
- Staff user/password management.
- Admin-vs-teacher role enforcement.
- Student accounts or opt-in contact permissions.
- Changing public join-request visibility.
- Removing phone/email from the database or admin workflows.
- Reworking unrelated routes, layouts, or deployment infrastructure.

## Done Criteria

1. Phone numbers are absent from anonymous HTML and present for staff.
2. Email remains public.
3. Anonymous visitors cannot see the event form; direct POSTs remain login-protected.
4. Unsafe event links cannot be created or edited, and are never rendered.
5. Saved-week export downloads the selected saved week.
6. Database outages produce 503 responses without an unhandled traceback.
7. README, schema docs, and Railway deployment documentation are tracked and
   accurate.
8. Full test suite and JavaScript lint pass.
