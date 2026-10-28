# Attendance Export Parity with class-c1-attendance — Design

**Date:** 2026-10-28
**Status:** Approved for implementation
**Scope:** Phase 1 of the C1 Hub update. Attendance PNG, Excel, and print/PDF exports only.

## Goal

Make the C1 Hub attendance exports visually and structurally match the reference
project `asaadzx/class-c1-attendance`, while preserving the existing CSV format
and weekly-upload workflow.

The reference project is a static bilingual checklist with Excel, PNG, and
print/PDF exports. It has no CSV export and no Late status. The C1 Hub keeps its
server-side export architecture, its CSV format, and its Late status.

## Decisions

| Decision | Choice |
|---|---|
| Implementation approach | Rewrite the existing server-side exporters in Python |
| Exports updated | PNG, Excel, print/PDF |
| CSV | Unchanged: columns, order, data, route, and weekly-upload compatibility |
| Late status | Separate Late section in exports; still counts as attended for weekly percentages |
| Export language | Always bilingual English + Arabic, independent of the site language |
| PNG and print content | Late and Absent sections |
| Excel content | Attended, Late, and Absent sections |
| Filename base | `YYYY-MM-DD-c1Class-attendance` for PNG and Excel |
| CSV filename | Unchanged: `YYYY-MM-DD-c1-attendance.csv` |
| Site UI | Existing NES.css pixel interface unchanged |

## Non-goals

- Assignments, subjects, notes, tasks, or markdown.
- Projects leaderboard page.
- Roster/user management, role permissions, privacy changes, and other Phase 2
  items.
- Changing the CSV schema or the weekly upload flow.
- Adding a browser-side JavaScript Excel/PNG exporter.

## Reference behavior to reproduce

The reference exports use a white background with black text and bright yellow
highlights. The PNG is a poster headed "Absent Students" with:

- a bilingual title and subtitle,
- a yellow date badge with a black border,
- a horizontal divider,
- a count line,
- one large yellow bordered row per absent student showing `#id`, the English
  name on the left, and the Arabic name right-aligned,
- a bilingual institute footer.

The reference Excel uses:

- a bold title block,
- a date and present/absent count row,
- an Attended section with a pale-green header,
- an Absent section with a bright-yellow header and large bold yellow rows,
- column widths of approximately 8, 42, and 34.

The C1 Hub extends this structure with a Late section and always labels sections
bilingually.

## 1. PNG export

`build_png(day)` returns PNG bytes with:

- white background,
- 1400 logical px width and 2x scale for crisp output,
- bilingual title:
  - English: `Late & Absent Students`
  - Arabic: `المتأخرون والغائبون`
- bilingual subtitle:
  - `Class C1 — Egypt-Japan KOSEN Institute`
  - `فصل C1 — معهد مصر اليابان كوسن`
- a yellow date badge containing the ISO date,
- a black horizontal divider,
- a bilingual count line showing both Late and Absent counts,
- a Late section using an amber highlight (`#FDE68A`),
- an Absent section using the reference bright yellow `#FFE600`,
- each student row: `#id`, English name left-aligned, Arabic name right-aligned,
- a bilingual footer:
  - `Egypt-Japan KOSEN Institute — Class C1`
  - `معهد مصر اليابان كوسن — فصل C1`.

If there are no Late students, keep the Late heading and show a bilingual
`Nobody late / لا يوجد متأخرون` line. If there are no Absent students, keep the
Absent heading and show the reference-style bilingual message
`No absent students — everyone attended! / لا يوجد غياب — الجميع حاضر!`.

Dynamic height must accommodate any number of Late and Absent students without
clipping. Long names must either fit, shrink, or wrap in a readable way.

Arabic shaping requires libraqm or an equivalent. The implementation must bundle
an Arabic-capable font and fall back safely when shaping or the font is
unavailable.

## 2. Excel export

`build_excel(day)` returns XLSX bytes with one sheet named `Attendance`:

1. Title row:
   `Egypt-Japan KOSEN Institute — Class C1 Attendance`
   `معهد مصر اليابان كوسن — حضور وغياب فصل C1`
2. Info row: bilingual date label and the date, Present count, Late count,
   Absent count.
3. Blank row.
4. **Attended / الحاضرون** section:
   - pale-green header (`#DCFCE7`),
   - column headers `#`, `Name (English)`, `الاسم (عربي)`,
   - one row per present student.
5. Blank row.
6. **Late / المتأخرون** section:
   - amber header,
   - same column headers,
   - one row per late student.
7. Blank row.
8. **Absent / الغائبون** section:
   - bright-yellow header (`#FFE600`) with bold black text,
   - same column headers with pale-yellow fill,
   - absent rows use `#FFE600`, bold, large text, matching the reference,
   - the bilingual all-present message when nobody is absent.

Column widths are 8, 42, and 34. Arabic cells are right-aligned and use a
right-to-left reading direction. The sheet should remain readable when opened in
Excel, LibreOffice, and Google Sheets.

Empty sections must show a bilingual empty-state line rather than an ambiguous
blank area.

## 3. Print/PDF export

The daily attendance page gains a server-rendered, print-only poster:

- hidden on screen with a `print-area` style,
- shown only by the print stylesheet,
- all normal page chrome hidden while printing,
- content and ordering match the PNG poster,
- date, Late/Absent counts, student rows, and footer are present,
- the browser's Print / PDF button continues to use `window.print()`.

The poster uses standard HTML/CSS (not canvas), so it works without JavaScript
once the page has loaded.

## 4. CSV export

The existing CSV route and format remain unchanged:

```csv
date,student_id,name_en,name_ar,status,note
```

No columns are added, removed, or reordered. The weekly upload feature must keep
passing with the existing CSV fixtures. CSV responses keep the current
`Cache-Control: no-store` behavior.

## 5. Architecture and data flow

All export data comes from the saved `AttendanceSession` for the requested date.

`app/attendance/exports.py` gains one pure grouping helper:

```text
group_records(records) -> {"present": [...], "late": [...], "absent": [...]}
```

`day_records(day)` loads the session and delegates to `group_records()`.
`build_excel()` and `build_png()` both call `day_records()`.

The daily attendance route already loads the session and its records. It passes
the same grouped lists to the template so the print poster does not issue a
second query. The route must remain the only place that knows the requested day.

No new routes, database tables, migrations, or JavaScript dependencies are added.

### Font handling

Two fonts are bundled under `app/static/fonts/`:

- `DejaVuSans-Bold.ttf` for English/Latin text,
- `NotoSansArabic-Bold.ttf` for Arabic text.

The PNG builder chooses the Arabic font for Arabic strings and the Latin font for
English strings. If a bundled file is missing, the loader tries the same font
name from the system, then Pillow's default font. If Arabic shaping is unavailable,
the export still completes rather than crashing.

Font licenses and provenance are recorded in `app/static/fonts/README.md`.

## 6. Edge cases and error handling

- **Unsaved day:** exports download successfully and show bilingual
  "No attendance saved" empty states.
- **No Late students:** show a bilingual "Nobody late" line; keep the section
  structure consistent.
- **No Absent students:** show the reference all-present message.
- **Only Present students:** both Late and Absent sections show empty-state
  messages.
- **Long names:** truncate, shrink, or wrap without overlapping adjacent rows.
- **Missing font:** fall back to DejaVu or Pillow default.
- **Arabic shaping unavailable:** render the best available glyphs; do not raise.
- **Spreadsheet formula injection:** values beginning with `=`, `+`, `-`, or `@`
  are escaped in Excel exports. The CSV output must not change shape or columns.
- **Browser caching:** PNG and Excel responses keep `Cache-Control: no-store`.
- **Authentication:** all export routes remain staff-only.

## 7. Testing

Automated pytest coverage:

1. PNG output starts with the PNG signature and has a white background pixel.
2. PNG is not generated with the old dark-red palette.
3. `group_records()` places present, late, and absent students in separate lists,
   and the PNG/print poster consume those lists.
4. Excel contains the bilingual title, date row, counts, and the
   Attended/Late/Absent headings.
5. Excel includes English and Arabic names for all three statuses.
6. Excel shows the all-present message when nobody is absent.
7. Print poster HTML contains Late/Absent sections and the print-only wrapper.
8. Export download filenames are `YYYY-MM-DD-c1Class-attendance.png` and
   `YYYY-MM-DD-c1Class-attendance.xlsx`.
9. CSV header, rows, route, and weekly-upload tests remain unchanged and pass.
10. Export routes still redirect anonymous users to login.
11. Export responses still include `Cache-Control: no-store`.

## 8. Done criteria

1. PNG, Excel, and print/PDF visually match the reference project's white/yellow
   bilingual style, with Late added as a separate section.
2. CSV columns, rows, and header remain compatible with the current format and
   weekly upload still works.
3. All existing tests pass, and the new export tests pass.
4. No new database migration is required.
5. No browser-side Excel/PNG library is added.
6. The attendance page still works on mobile and in both site languages.
