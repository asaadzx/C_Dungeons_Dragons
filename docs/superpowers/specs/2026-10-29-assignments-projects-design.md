# Assignments and Projects Pages — Design

**Date:** 2026-10-29
**Status:** Approved in chat; awaiting written-spec review
**Scope:** Public Assignments and Projects pages plus staff management.

## Goal

Add two simple public pages that staff can fill from the control panel:

- **Assignments**: lecture notes grouped by day, shown as tabs.
- **Projects**: a flat list of project cards with an optional link.

No student accounts, submissions, completion tracking, voting, or rich text.

## Decisions

| Decision | Choice |
|---|---|
| Assignment grouping | Tabs generated from lecture dates, newest first |
| Lecture content | Title plus a read-only checklist |
| Checklist links | Optional `http`/`https` link per item |
| Projects layout | Simple cards with title, description, and optional link |
| Staff editing | Dedicated `/admin/assignments` and `/admin/projects` pages |
| Ordering | Numeric `position` fields, then id |
| Database | Three new tables and one migration |
| Language | New navigation labels translated; staff-entered content is not translated |

## Data Model

### `Lecture`

- `id`
- `date` (`Date`, required, indexed)
- `title` (`String(200)`, required)
- `position` (`Integer`, default `0`)
- `created_at` (`DateTime(timezone=True)`)

### `LectureItem`

- `id`
- `lecture_id` (`FK lectures.id`, required, cascade delete)
- `text` (`String(300)`, required)
- `url` (`String(500)`, default `""`)
- `position` (`Integer`, default `0`)

### `Project`

- `id`
- `title` (`String(200)`, required)
- `description` (`Text`, default `""`)
- `url` (`String(500)`, default `""`)
- `position` (`Integer`, default `0`)
- `created_at` (`DateTime(timezone=True)`)

## Public Behavior

### `/assignments`

- Shows date tabs for every date that has at least one lecture.
- Tabs are newest first; the selected date defaults to the newest date.
- `?date=YYYY-MM-DD` selects a tab. An unknown date falls back to the newest.
- Selected day shows each lecture as a card ordered by `position`, then id.
- Each card shows the lecture title and a read-only checklist.
- Checklist items are ordered by `position`, then id.
- If an item has a safe link, its text is rendered as an external link
  (`target="_blank" rel="noopener"`). Otherwise it is plain text.
- Empty state: “No lectures have been added yet.”

### `/projects`

- Shows every project as a card ordered by `position`, then id.
- Each card shows title, description, and a link button when a safe URL exists.
- Empty state: “No projects have been added yet.”

Both pages are added to the Menu navigation with translated labels.

## Staff Behavior

### `/admin/assignments`

- Requires login.
- Add lecture: date, title, position.
- Edit lecture: date, title, position.
- Delete lecture (also deletes its checklist items).
- Add checklist item to a lecture: text, optional URL, position.
- Edit checklist item: text, URL, position.
- Delete checklist item.

### `/admin/projects`

- Requires login.
- Add project: title, description, optional URL, position.
- Edit and delete projects.

The existing `/admin` page links to both management pages.

## Validation and Safety

- Lecture date must be a valid `YYYY-MM-DD` value.
- Titles and checklist text are required; surrounding whitespace is stripped.
- Text is truncated to its column limit after validation.
- Empty links are allowed. Non-empty links must pass the existing `safe_url`
  check (absolute `http` or `https` with a host).
- Invalid links flash a clear error and are not saved.
- Public templates still pass stored links through `safe_url` so legacy unsafe
  values are never rendered as links.

## Architecture

| File | Change |
|---|---|
| `app/models.py` | Add `Lecture`, `LectureItem`, `Project` |
| `app/hub/routes.py` | Add `/assignments` and `/projects` |
| `app/admin/routes.py` | Add staff CRUD routes |
| `app/templates/assignments.html` | Date tabs, lecture cards, checklist |
| `app/templates/projects.html` | Project cards |
| `app/templates/admin/assignments.html` | Lecture/item management |
| `app/templates/admin/projects.html` | Project management |
| `app/templates/admin/index.html` | Links to the new management pages |
| `app/templates/base.html` | Menu links |
| `app/i18n.py` | Navigation labels |
| `migrations/versions/` | New migration |

No new JavaScript dependency. Date tabs are ordinary links.

## Error Handling

- Invalid date, missing title/text, or unsafe URL: flash an error and redirect
  back to the relevant management page without saving.
- Missing lecture/project/item on edit/delete: flash “not found” and redirect.
- Empty public pages render the empty state.

## Testing

1. Assignments page requires no login and shows the newest day by default.
2. Date tabs appear newest first; `?date=` selects a day.
3. Lecture cards and checklist items render in stored order.
4. A safe checklist link renders as an anchor; an unsafe link renders as text.
5. Projects page shows title, description, and safe link.
6. Unsafe project links are not rendered.
7. Admin assignment routes require login.
8. Staff can add/edit/delete lectures and checklist items.
9. Staff can add/edit/delete projects.
10. Invalid date and unsafe URL submissions are rejected without saving.
11. Existing tests remain green.

## Non-Goals

- Student completion checkboxes or per-student progress.
- Assignment submissions, grading, files, or deadlines beyond lecture dates.
- Project voting, leaderboards, team members, or images.
- Markdown or rich-text editing.
- Drag-and-drop ordering.
- Automatic translation of staff-entered content.

## Done Criteria

1. Staff can publish lectures under dated tabs with checklists and safe links.
2. Staff can publish project cards with descriptions and safe links.
3. Anonymous visitors can read both pages without logging in.
4. Unsafe links are never rendered as clickable links.
5. Database migration applies cleanly.
6. Full test suite and JavaScript lint pass.
