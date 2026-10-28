# Attendance Export Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the C1 Hub attendance PNG, Excel, and print/PDF exports visually match `asaadzx/class-c1-attendance` while keeping the CSV format and weekly-upload flow unchanged.

**Architecture:** Keep the existing server-side export routes. Add one pure grouping helper, rewrite the openpyxl and Pillow builders to the reference white/yellow bilingual layout, and add a server-rendered print-only poster to the daily attendance page. CSV stays byte-for-byte the same format.

**Tech Stack:** Flask, openpyxl, Pillow, Jinja2, pytest, ESLint.

## Global Constraints

- Do not change the CSV columns, order, header, route, or weekly-upload behavior.
- Exports are always bilingual English + Arabic, regardless of the site language.
- `late` remains a separate export section and still counts as attended for weekly percentages.
- PNG and Excel filenames use `YYYY-MM-DD-c1Class-attendance`.
- CSV filename stays `YYYY-MM-DD-c1-attendance.csv`.
- All export routes remain staff-only.
- All export responses keep `Cache-Control: no-store`.
- No new database migration.
- No browser-side Excel/PNG JavaScript library.
- Site UI remains the existing NES.css pixel interface.

---

### Task 1: Add the shared attendance grouping helper

**Files:**
- Modify: `app/attendance/exports.py`
- Test: `tests/test_exports.py`

**Interfaces:**
- Consumes: `AttendanceRecord` objects loaded from an `AttendanceSession`.
- Produces: `group_records(records) -> dict[str, list[AttendanceRecord]]` with keys `present`, `late`, `absent`.
- Produces: `day_records(day) -> dict[str, list[AttendanceRecord]]` using `group_records()`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_exports.py`:

```python
def test_group_records_separates_statuses(app):
    user_id, s1, s2, s3 = _seed(app)
    with app.app_context():
        from app.attendance.exports import group_records
        from app.attendance.services import save_attendance
        from app.models import AttendanceSession

        save_attendance(
            date(2026, 10, 22),
            {s1: "present", s2: "late", s3: "absent"},
            {},
            user_id,
        )
        session = AttendanceSession.query.one()
        groups = group_records(session.records)

        assert [r.student.name_en for r in groups["present"]] == ["Present P"]
        assert [r.student.name_en for r in groups["late"]] == ["Late L"]
        assert [r.student.name_en for r in groups["absent"]] == ["Absent A"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_exports.py::test_group_records_separates_statuses -v`

Expected: FAIL with `ImportError: cannot import name 'group_records'`.

- [ ] **Step 3: Add the helper and refactor `day_records()`**

Replace the current `day_records()` in `app/attendance/exports.py` with:

```python
def group_records(records):
    """Group attendance records by status, sorted by English name."""
    grouped = {"present": [], "late": [], "absent": []}
    for record in sorted(records, key=lambda r: r.student.name_en.lower()):
        grouped.setdefault(record.status, []).append(record)
    return grouped


def day_records(day):
    """Return a day's records grouped by status."""
    session = get_session(day)
    if session is None:
        return {"present": [], "late": [], "absent": []}
    return group_records(session.records)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_exports.py::test_group_records_separates_statuses -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/attendance/exports.py tests/test_exports.py
git commit -m "refactor: share attendance status grouping"
```

---

### Task 2: Rewrite the Excel export in the reference style

**Files:**
- Modify: `app/attendance/exports.py`
- Test: `tests/test_exports.py`

**Interfaces:**
- Consumes: `day_records(day)` from Task 1.
- Produces: `build_excel(day) -> bytes` with Attended/Late/Absent sections.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_exports.py`:

```python
def test_excel_uses_reference_layout(app):
    user_id, s1, s2, s3 = _seed(app)
    with app.app_context():
        from app.attendance.exports import build_excel
        from app.attendance.services import save_attendance

        save_attendance(
            date(2026, 10, 22),
            {s1: "present", s2: "late", s3: "absent"},
            {},
            user_id,
        )
        data = build_excel(date(2026, 10, 22))
        workbook = load_workbook(io.BytesIO(data))
        sheet = workbook.active
        text = " ".join(
            str(cell.value)
            for row in sheet.iter_rows()
            for cell in row
            if cell.value
        )

        assert "Egypt-Japan KOSEN Institute" in text
        assert "حضور وغياب فصل C1" in text
        assert "2026-10-22" in text
        assert "Attended / الحاضرون" in text
        assert "Late / المتأخرون" in text
        assert "Absent / الغائبون" in text
        assert "Present P" in text
        assert "Late L" in text
        assert "Absent A" in text
        assert "ط" in text
        assert "ح" in text
        assert "خ" in text


def test_excel_shows_all_present_message(app):
    user_id, s1, _s2, _s3 = _seed(app)
    with app.app_context():
        from app.attendance.exports import build_excel
        from app.attendance.services import save_attendance

        save_attendance(date(2026, 10, 22), {s1: "present"}, {}, user_id)
        data = build_excel(date(2026, 10, 22))
        workbook = load_workbook(io.BytesIO(data))
        text = " ".join(
            str(cell.value)
            for row in workbook.active.iter_rows()
            for cell in row
            if cell.value
        )

        assert "No absent students" in text
        assert "لا يوجد غياب" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_exports.py::test_excel_uses_reference_layout tests/test_exports.py::test_excel_shows_all_present_message -v`

Expected: FAIL because the old workbook does not contain the reference headings or all-present message.

- [ ] **Step 3: Replace the Excel constants and builder**

In `app/attendance/exports.py`, replace the old `PALETTE`, `SECTIONS`, and `build_excel()` with:

```python
REFERENCE = {
    "green": "DCFCE7",
    "amber": "FDE68A",
    "yellow": "FFE600",
    "yellow_soft": "FFF2B0",
    "black": "000000",
    "white": "FFFFFF",
}


def _safe_spreadsheet_value(value):
    """Prevent spreadsheet formula injection in text cells."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _write_excel_section(
    sheet,
    row,
    title,
    records,
    *,
    header_fill,
    row_fill,
    row_font,
    empty_message,
):
    sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    heading = sheet.cell(row=row, column=1, value=title)
    heading.font = Font(bold=True, size=14, color=REFERENCE["black"])
    heading.fill = PatternFill("solid", fgColor=header_fill)
    heading.alignment = Alignment(horizontal="left")
    row += 1

    for column, label in enumerate(("#", "Name (English)", "الاسم (عربي)"), start=1):
        cell = sheet.cell(row=row, column=column, value=label)
        cell.font = Font(bold=True, size=11)
        cell.fill = PatternFill("solid", fgColor=header_fill)
    sheet.cell(row=row, column=3).alignment = Alignment(
        horizontal="right", readingOrder=2
    )
    row += 1

    if records:
        for record in records:
            values = (
                record.student_id,
                _safe_spreadsheet_value(record.student.name_en),
                _safe_spreadsheet_value(record.student.name_ar),
            )
            for column, value in enumerate(values, start=1):
                cell = sheet.cell(row=row, column=column, value=value)
                cell.font = row_font
                cell.fill = PatternFill("solid", fgColor=row_fill)
                if column == 3:
                    cell.alignment = Alignment(horizontal="right", readingOrder=2)
            row += 1
    else:
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        cell = sheet.cell(row=row, column=1, value=empty_message)
        cell.font = row_font
        cell.fill = PatternFill("solid", fgColor=row_fill)
        row += 1

    return row + 1


def build_excel(day):
    """Return the reference-style bilingual .xlsx workbook as bytes."""
    records = day_records(day)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Attendance"
    sheet.sheet_view.showGridLines = False

    sheet.column_dimensions["A"].width = 8
    sheet.column_dimensions["B"].width = 42
    sheet.column_dimensions["C"].width = 34

    sheet.merge_cells("A1:C1")
    sheet["A1"] = (
        "Egypt-Japan KOSEN Institute — Class C1 Attendance / "
        "معهد مصر اليابان كوسن — حضور وغياب فصل C1"
    )
    sheet["A1"].font = Font(bold=True, size=16)
    sheet["A1"].alignment = Alignment(horizontal="center", wrap_text=True)
    sheet.row_dimensions[1].height = 34

    sheet["A2"] = f"Date / التاريخ: {day.isoformat()}"
    sheet["B2"] = (
        f"Present / حاضر: {len(records['present'])}   "
        f"Late / متأخر: {len(records['late'])}"
    )
    sheet["C2"] = f"Absent / غائب: {len(records['absent'])}"
    for coordinate in ("A2", "B2", "C2"):
        sheet[coordinate].font = Font(bold=True, size=12)

    row = 4
    row = _write_excel_section(
        sheet,
        row,
        "Attended / الحاضرون",
        records["present"],
        header_fill=REFERENCE["green"],
        row_fill=REFERENCE["white"],
        row_font=Font(size=11),
        empty_message="No present students / لا يوجد حاضرون",
    )
    row = _write_excel_section(
        sheet,
        row,
        "Late / المتأخرون",
        records["late"],
        header_fill=REFERENCE["amber"],
        row_fill=REFERENCE["yellow_soft"],
        row_font=Font(bold=True, size=12),
        empty_message="Nobody late / لا يوجد متأخرون",
    )
    _write_excel_section(
        sheet,
        row,
        "Absent / الغائبون",
        records["absent"],
        header_fill=REFERENCE["yellow"],
        row_fill=REFERENCE["yellow"],
        row_font=Font(bold=True, size=18),
        empty_message="No absent students — everyone attended! / لا يوجد غياب — الجميع حاضر!",
    )

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_exports.py -v`

Expected: all tests in `tests/test_exports.py` PASS.

- [ ] **Step 5: Commit**

```bash
git add app/attendance/exports.py tests/test_exports.py
git commit -m "feat: export reference-style bilingual attendance Excel"
```

---

### Task 3: Bundle fonts and rewrite the PNG export in the reference style

**Files:**
- Create: `app/static/fonts/DejaVuSans-Bold.ttf`
- Create: `app/static/fonts/NotoSansArabic-Bold.ttf`
- Create: `app/static/fonts/README.md`
- Modify: `app/attendance/exports.py`
- Test: `tests/test_exports.py`

**Interfaces:**
- Consumes: `day_records(day)` from Task 1.
- Produces: `poster_model(day) -> dict` with `date`, `late`, `absent`, `late_count`, `absent_count`.
- Produces: `build_png(day) -> bytes` using the reference white/yellow poster layout.

- [ ] **Step 1: Bundle the fonts and document their licenses**

Run:

```bash
mkdir -p app/static/fonts
cp /usr/share/fonts/TTF/DejaVuSans-Bold.ttf app/static/fonts/DejaVuSans-Bold.ttf
cp /usr/share/fonts/noto/NotoSansArabic-Bold.ttf app/static/fonts/NotoSansArabic-Bold.ttf
```

Create `app/static/fonts/README.md`:

```markdown
# Bundled fonts

These fonts are bundled so attendance image exports render identically on
development machines and on the production host.

| File | Source | License |
| --- | --- | --- |
| `DejaVuSans-Bold.ttf` | DejaVu Fonts | DejaVu Fonts License (Bitstream Vera derivative) |
| `NotoSansArabic-Bold.ttf` | Google Noto Fonts | SIL Open Font License 1.1 |

The fonts are used only by Pillow when generating attendance PNG exports.
```

- [ ] **Step 2: Write the failing tests**

Replace the existing `test_png_returns_image` in `tests/test_exports.py` with:

```python
def test_png_uses_reference_white_palette(app):
    user_id, s1, s2, s3 = _seed(app)
    with app.app_context():
        from app.attendance.exports import build_png
        from app.attendance.services import save_attendance

        save_attendance(
            date(2026, 10, 22),
            {s1: "present", s2: "late", s3: "absent"},
            {},
            user_id,
        )
        data = build_png(date(2026, 10, 22))

    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    image = Image.open(io.BytesIO(data)).convert("RGB")
    assert image.getpixel((0, 0)) == (255, 255, 255)
    assert image.getpixel((0, 0)) != (190, 26, 26)


def test_poster_model_has_late_and_absent(app):
    user_id, s1, s2, s3 = _seed(app)
    with app.app_context():
        from app.attendance.exports import poster_model
        from app.attendance.services import save_attendance

        save_attendance(
            date(2026, 10, 22),
            {s1: "present", s2: "late", s3: "absent"},
            {},
            user_id,
        )
        model = poster_model(date(2026, 10, 22))

        assert [r.student.name_en for r in model["late"]] == ["Late L"]
        assert [r.student.name_en for r in model["absent"]] == ["Absent A"]
        assert model["late_count"] == 1
        assert model["absent_count"] == 1
```

Add `from PIL import Image` to the imports at the top of `tests/test_exports.py`.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_exports.py::test_png_uses_reference_white_palette tests/test_exports.py::test_poster_model_has_late_and_absent -v`

Expected: FAIL because `poster_model` does not exist and the old PNG is dark red.

- [ ] **Step 4: Replace the PNG constants and builder**

In `app/attendance/exports.py`, add these imports near the top:

```python
from functools import lru_cache
from pathlib import Path
```

Replace the old `PALETTE`, `_load_font()`, and `build_png()` with:

```python
FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
LATIN_FONT = FONT_DIR / "DejaVuSans-Bold.ttf"
ARABIC_FONT = FONT_DIR / "NotoSansArabic-Bold.ttf"

POSTER = {
    "yellow": "#FFE600",
    "amber": "#FDE68A",
    "black": "#000000",
    "white": "#FFFFFF",
    "footer": "#333333",
}


@lru_cache(maxsize=64)
def _load_font(path_text, size):
    """Load a bundled font, then a system copy, then Pillow's default."""
    path = Path(path_text)
    candidates = [path]
    if path.name == "DejaVuSans-Bold.ttf":
        candidates.append(Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"))
    if path.name == "NotoSansArabic-Bold.ttf":
        candidates.append(Path("/usr/share/fonts/noto/NotoSansArabic-Bold.ttf"))
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _draw_text(draw, xy, text, font, fill, *, anchor="la", rtl=False):
    """Draw text with optional RTL shaping, falling back safely."""
    kwargs = {"font": font, "fill": fill, "anchor": anchor}
    if rtl:
        try:
            draw.text(xy, text, direction="rtl", **kwargs)
            return
        except (TypeError, ValueError):
            pass
    draw.text(xy, text, **kwargs)


def _fit_font(draw, text, font_path, max_width, start_size, min_size=18):
    """Shrink, then truncate, until text fits in max_width."""
    size = start_size
    while size >= min_size:
        font = _load_font(str(font_path), size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font, text
        size -= 2

    font = _load_font(str(font_path), min_size)
    truncated = text
    while truncated and draw.textlength(truncated + "…", font=font) > max_width:
        truncated = truncated[:-1]
    if truncated != text:
        truncated += "…"
    return font, truncated


def poster_model(day):
    """Return the data used by the PNG poster."""
    records = day_records(day)
    return {
        "date": day.isoformat(),
        "late": records["late"],
        "absent": records["absent"],
        "late_count": len(records["late"]),
        "absent_count": len(records["absent"]),
    }


def build_png(day):
    """Return the reference-style bilingual Late/Absent poster as PNG bytes."""
    model = poster_model(day)
    scale = 2
    width = 1400
    pad = 60
    line_h = 110
    section_h = 70
    gap = 16
    header_h = 540

    def section_height(rows):
        return section_h + gap + max(len(rows), 1) * line_h + gap

    height = header_h + section_height(model["late"]) + section_height(model["absent"]) + 130
    image = Image.new("RGB", (width * scale, height * scale), POSTER["white"])
    draw = ImageDraw.Draw(image)

    def px(value):
        return int(value * scale)

    def center_text(text, y, font_path, size, fill, *, rtl=False):
        font, fitted = _fit_font(draw, text, font_path, px(width - 2 * pad), px(size))
        _draw_text(draw, (px(width / 2), px(y)), fitted, font, fill, anchor="mm", rtl=rtl)

    center_text("Late & Absent Students", 60, LATIN_FONT, 64, POSTER["black"])
    center_text("المتأخرون والغائبون", 145, ARABIC_FONT, 56, POSTER["black"], rtl=True)
    center_text(
        "Class C1 — Egypt-Japan KOSEN Institute",
        215,
        LATIN_FONT,
        26,
        POSTER["black"],
    )
    center_text(
        "فصل C1 — معهد مصر اليابان كوسن",
        255,
        ARABIC_FONT,
        26,
        POSTER["black"],
        rtl=True,
    )

    date_font = _load_font(str(LATIN_FONT), px(30))
    date_bbox = draw.textbbox((0, 0), model["date"], font=date_font)
    badge_w = date_bbox[2] - date_bbox[0] + px(60)
    draw.rectangle(
        [px(width / 2) - badge_w / 2, px(310), px(width / 2) + badge_w / 2, px(370)],
        fill=POSTER["yellow"],
        outline=POSTER["black"],
        width=px(4),
    )
    _draw_text(
        draw,
        (px(width / 2), px(340)),
        model["date"],
        date_font,
        POSTER["black"],
        anchor="mm",
    )

    draw.line([(px(pad), px(405)), (px(width - pad), px(405))], fill=POSTER["black"], width=px(6))
    center_text(
        f"Late: {model['late_count']}   Absent: {model['absent_count']}",
        450,
        LATIN_FONT,
        30,
        POSTER["black"],
    )
    center_text(
        f"متأخرون: {model['late_count']}   غائبون: {model['absent_count']}",
        492,
        ARABIC_FONT,
        26,
        POSTER["black"],
        rtl=True,
    )

    def draw_section(y, title_en, title_ar, rows, fill, empty_en, empty_ar):
        top = px(y)
        draw.rectangle(
            [px(pad), top, px(width - pad), top + px(section_h)],
            fill=fill,
            outline=POSTER["black"],
            width=px(4),
        )
        en_font = _load_font(str(LATIN_FONT), px(34))
        ar_font = _load_font(str(ARABIC_FONT), px(34))
        _draw_text(
            draw,
            (px(pad + 24), top + px(section_h / 2)),
            title_en,
            en_font,
            POSTER["black"],
            anchor="lm",
        )
        _draw_text(
            draw,
            (px(width - pad - 24), top + px(section_h / 2)),
            title_ar,
            ar_font,
            POSTER["black"],
            anchor="rm",
            rtl=True,
        )
        y += section_h + gap

        if rows:
            for record in rows:
                top = px(y)
                draw.rectangle(
                    [px(pad), top, px(width - pad), top + px(line_h)],
                    fill=fill,
                    outline=POSTER["black"],
                    width=px(4),
                )
                id_font = _load_font(str(LATIN_FONT), px(40))
                _draw_text(
                    draw,
                    (px(pad + 24), top + px(line_h / 2)),
                    f"#{record.student_id}",
                    id_font,
                    POSTER["black"],
                    anchor="lm",
                )
                en_font, en_text = _fit_font(
                    draw,
                    record.student.name_en,
                    LATIN_FONT,
                    px((width - 2 * pad) * 0.52),
                    px(40),
                    px(24),
                )
                _draw_text(
                    draw,
                    (px(pad + 120), top + px(line_h / 2)),
                    en_text,
                    en_font,
                    POSTER["black"],
                    anchor="lm",
                )
                ar_font, ar_text = _fit_font(
                    draw,
                    record.student.name_ar,
                    ARABIC_FONT,
                    px((width - 2 * pad) * 0.34),
                    px(40),
                    px(24),
                )
                _draw_text(
                    draw,
                    (px(width - pad - 24), top + px(line_h / 2)),
                    ar_text,
                    ar_font,
                    POSTER["black"],
                    anchor="rm",
                    rtl=True,
                )
                y += line_h
        else:
            top = px(y)
            draw.rectangle(
                [px(pad), top, px(width - pad), top + px(line_h)],
                fill=fill,
                outline=POSTER["black"],
                width=px(4),
            )
            empty_font = _load_font(str(LATIN_FONT), px(34))
            _draw_text(
                draw,
                (px(width / 2), top + px(line_h / 2)),
                empty_en,
                empty_font,
                POSTER["black"],
                anchor="mm",
            )
            y += line_h
        return y + gap

    y = header_h
    y = draw_section(
        y,
        "Late",
        "المتأخرون",
        model["late"],
        POSTER["amber"],
        "Nobody late",
        "لا يوجد متأخرون",
    )
    y = draw_section(
        y,
        "Absent",
        "الغائبون",
        model["absent"],
        POSTER["yellow"],
        "No absent students — everyone attended!",
        "لا يوجد غياب — الجميع حاضر!",
    )

    footer_font = _load_font(str(LATIN_FONT), px(24))
    footer_ar_font = _load_font(str(ARABIC_FONT), px(22))
    _draw_text(
        draw,
        (px(width / 2), px(height - 70)),
        "Egypt-Japan KOSEN Institute — Class C1",
        footer_font,
        POSTER["footer"],
        anchor="mm",
    )
    _draw_text(
        draw,
        (px(width / 2), px(height - 35)),
        "معهد مصر اليابان كوسن — فصل C1",
        footer_ar_font,
        POSTER["footer"],
        anchor="mm",
        rtl=True,
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_exports.py -v`

Expected: all tests in `tests/test_exports.py` PASS.

- [ ] **Step 6: Commit**

```bash
git add app/attendance/exports.py app/static/fonts tests/test_exports.py
git commit -m "feat: export reference-style bilingual attendance PNG"
```

---

### Task 4: Add the print/PDF poster

**Files:**
- Modify: `app/attendance/routes.py`
- Modify: `app/templates/attendance/daily.html`
- Modify: `app/static/css/style.css`
- Test: `tests/test_exports.py`

**Interfaces:**
- Consumes: `group_records(records)` from Task 1.
- Produces: `export_groups` template variable with `present`, `late`, `absent` lists.
- Produces: `#attendance-print` print-only poster markup.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_exports.py`:

```python
def test_daily_page_has_print_poster(client, app):
    user_id, s1, s2, s3 = _seed(app)
    with app.app_context():
        from app.attendance.services import save_attendance

        save_attendance(
            date(2026, 10, 22),
            {s1: "present", s2: "late", s3: "absent"},
            {},
            user_id,
        )
    _login(client)

    page = client.get("/attendance?date=2026-10-22").data.decode()
    assert 'id="attendance-print"' in page
    assert "attendance-poster" in page
    assert "Late L" in page
    assert "Absent A" in page
    assert "المتأخرون" in page
    assert "الغائبون" in page
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_exports.py::test_daily_page_has_print_poster -v`

Expected: FAIL because the page has no print poster.

- [ ] **Step 3: Pass grouped records to the template**

In `app/attendance/routes.py`, update the import:

```python
from .exports import build_excel, build_png, group_records
```

Replace the `records = ...` line in `daily()` with:

```python
    records = {r.student_id: r for r in attendance_session.records} if attendance_session else {}
    export_groups = (
        group_records(attendance_session.records)
        if attendance_session
        else {"present": [], "late": [], "absent": []}
    )
```

Add `export_groups=export_groups,` to the `render_template()` call for `attendance/daily.html`.

- [ ] **Step 4: Add the print poster markup**

At the end of `app/templates/attendance/daily.html`, immediately before `{% endblock %}`, add:

```html
<!-- Print-only poster: matches the reference class-c1-attendance design. -->
<div id="attendance-print" class="attendance-print" aria-hidden="true">
    <div class="attendance-poster">
        <header class="ap-head">
            <h2 class="ap-title-en">Late &amp; Absent Students</h2>
            <p class="ap-title-ar" dir="rtl">المتأخرون والغائبون</p>
            <p class="ap-sub-en">Class C1 — Egypt-Japan KOSEN Institute</p>
            <p class="ap-sub-ar" dir="rtl">فصل C1 — معهد مصر اليابان كوسن</p>
            <div class="ap-date">{{ day.isoformat() }}</div>
            <div class="ap-counts">
                <span>Late / متأخر: {{ export_groups.late|length }}</span>
                <span>Absent / غائب: {{ export_groups.absent|length }}</span>
            </div>
        </header>

        <section class="ap-section">
            <h3 class="ap-section-title">
                <span>Late</span>
                <span dir="rtl">المتأخرون</span>
            </h3>
            {% for record in export_groups.late %}
                <div class="ap-row ap-row-late">
                    <span class="ap-num">#{{ record.student_id }}</span>
                    <span class="ap-name-en" dir="ltr">{{ record.student.name_en }}</span>
                    <span class="ap-name-ar" dir="rtl">{{ record.student.name_ar }}</span>
                </div>
            {% else %}
                <div class="ap-empty ap-row-late">Nobody late / لا يوجد متأخرون</div>
            {% endfor %}
        </section>

        <section class="ap-section">
            <h3 class="ap-section-title">
                <span>Absent</span>
                <span dir="rtl">الغائبون</span>
            </h3>
            {% for record in export_groups.absent %}
                <div class="ap-row ap-row-absent">
                    <span class="ap-num">#{{ record.student_id }}</span>
                    <span class="ap-name-en" dir="ltr">{{ record.student.name_en }}</span>
                    <span class="ap-name-ar" dir="rtl">{{ record.student.name_ar }}</span>
                </div>
            {% else %}
                <div class="ap-empty ap-row-absent">
                    No absent students — everyone attended! / لا يوجد غياب — الجميع حاضر!
                </div>
            {% endfor %}
        </section>

        <footer class="ap-footer">
            Egypt-Japan KOSEN Institute — Class C1 /
            معهد مصر اليابان كوسن — فصل C1
        </footer>
    </div>
</div>
```

Also update the existing `<script>` block in `daily.html` to set the PDF filename title:

```javascript
var printTitle = '{{ day.isoformat() }}-c1Class-attendance';
var originalTitle = document.title;
window.addEventListener('beforeprint', function () {
  document.title = printTitle;
});
window.addEventListener('afterprint', function () {
  document.title = originalTitle;
});
```

- [ ] **Step 5: Add the print styles**

Append to `app/static/css/style.css`:

```css
/* ---------------------------------------------------------------------------
   Attendance print/PDF poster (reference class-c1-attendance design)
   --------------------------------------------------------------------------- */
.attendance-print {
    display: none;
}

.attendance-poster {
    background: #ffffff;
    color: #000000;
    font-family: "Segoe UI", Tahoma, "Noto Sans Arabic", sans-serif;
    padding: 34px;
}

.ap-head {
    text-align: center;
    border-bottom: 4px solid #000000;
    padding-bottom: 18px;
    margin-bottom: 24px;
}

.ap-title-en {
    margin: 0;
    font-size: 42px;
    font-weight: 900;
    color: #000000;
    text-shadow: none;
}

.ap-title-ar {
    margin: 6px 0 0;
    font-size: 36px;
    font-weight: 900;
}

.ap-sub-en,
.ap-sub-ar {
    margin: 6px 0 0;
    font-size: 20px;
    font-weight: 700;
}

.ap-date {
    display: inline-block;
    margin-top: 14px;
    padding: 6px 24px;
    background: #ffe600;
    border: 4px solid #000000;
    font-size: 24px;
    font-weight: 900;
}

.ap-counts {
    display: flex;
    justify-content: center;
    gap: 32px;
    margin-top: 16px;
    font-size: 20px;
    font-weight: 800;
}

.ap-section {
    margin-bottom: 22px;
}

.ap-section-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 0 0 12px;
    padding: 8px 16px;
    background: #ffe600;
    border: 4px solid #000000;
    font-size: 34px;
    font-weight: 900;
    color: #000000;
    text-shadow: none;
}

.ap-row,
.ap-empty {
    display: flex;
    align-items: center;
    gap: 18px;
    min-height: 62px;
    margin-bottom: 10px;
    padding: 10px 18px;
    border: 3px solid #000000;
    font-size: 28px;
    font-weight: 900;
}

.ap-row-late {
    background: #fde68a;
}

.ap-row-absent {
    background: #ffe600;
}

.ap-num {
    min-width: 70px;
    font-size: 30px;
}

.ap-name-en {
    flex: 1;
}

.ap-name-ar {
    flex: 1;
    text-align: right;
}

.ap-empty {
    justify-content: center;
    text-align: center;
}

.ap-footer {
    margin-top: 20px;
    text-align: center;
    font-size: 18px;
    font-weight: 600;
    color: #333333;
}

@media print {
    body {
        background: #ffffff !important;
        background-image: none !important;
        padding: 0;
        text-shadow: none;
    }

    body * {
        visibility: hidden;
    }

    .attendance-print,
    .attendance-print * {
        visibility: visible;
    }

    .attendance-print {
        display: block !important;
        position: absolute;
        inset: 0;
        width: 100%;
    }

    .ap-row-late,
    .ap-row-absent,
    .ap-section-title,
    .ap-date {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    @page {
        margin: 12mm;
    }
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_exports.py -v`

Expected: all tests PASS, including `test_daily_page_has_print_poster`.

- [ ] **Step 7: Commit**

```bash
git add app/attendance/routes.py app/templates/attendance/daily.html app/static/css/style.css tests/test_exports.py
git commit -m "feat: add reference-style attendance print poster"
```

---

### Task 5: Update export filenames and documentation

**Files:**
- Modify: `app/attendance/routes.py`
- Modify: `README.md` (local documentation; file is gitignored)
- Test: `tests/test_exports.py`

**Interfaces:**
- Consumes: existing `export_xlsx` and `export_png` routes.
- Produces: `Content-Disposition` filenames `YYYY-MM-DD-c1Class-attendance.xlsx` and `.png`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_exports.py`:

```python
def test_export_filenames_match_reference(app, client):
    _seed(app)
    _login(client)

    for path, expected in (
        ("/attendance/export.png?date=2026-10-22", "2026-10-22-c1Class-attendance.png"),
        ("/attendance/export.xlsx?date=2026-10-22", "2026-10-22-c1Class-attendance.xlsx"),
        ("/attendance/export.csv?date=2026-10-22", "2026-10-22-c1-attendance.csv"),
    ):
        response = client.get(path)
        disposition = response.headers.get("Content-Disposition", "")
        assert f"filename={expected}" in disposition
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_exports.py::test_export_filenames_match_reference -v`

Expected: FAIL because the PNG/XLSX filenames still use `c1-attendance`.

- [ ] **Step 3: Change the filenames**

In `app/attendance/routes.py`, change the `export_xlsx()` filename to:

```python
        f"{day.isoformat()}-c1Class-attendance.xlsx",
```

Change the `export_png()` filename to:

```python
        f"{day.isoformat()}-c1Class-attendance.png",
```

Leave the CSV filename unchanged.

- [ ] **Step 4: Update the local README**

In `README.md`, update the Routes table:

```markdown
| `/attendance/export.png` | staff | Bilingual reference-style PNG poster |
| `/attendance/export.xlsx` | staff | Bilingual reference-style Excel workbook |
```

Add this note under the daily CSV section:

```markdown
PNG and Excel exports use the reference `class-c1-attendance` white/yellow
bilingual design and download as `YYYY-MM-DD-c1Class-attendance.*`. The CSV
format above is unchanged and remains the input for weekly reports.
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_exports.py::test_export_filenames_match_reference -v`

Expected: PASS.

- [ ] **Step 6: Run the full test suite and JS lint**

Run:

```bash
.venv/bin/python -m pytest -q
npm run lint:js
```

Expected: all pytest tests pass and ESLint exits 0.

- [ ] **Step 7: Run a local-host smoke test**

Start the app in the background:

```bash
SECRET_KEY=local-dev-key FLASK_ENV=development .venv/bin/python wsgi.py > /tmp/c1-hub.log 2>&1 &
```

Wait a moment, then check the public and protected pages:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/attendance
```

Expected: `200`, `200`, and `302` (attendance redirects anonymous users to login).

Stop the server:

```bash
kill %1
```

- [ ] **Step 8: Commit**

```bash
git add app/attendance/routes.py tests/test_exports.py
git commit -m "feat: use reference attendance export filenames"
```

`README.md` is gitignored in this repository, so it is updated locally but not committed.

---

### Task 6: Review, push, and deploy

**Files:**
- No source changes expected.
- Verify: `git status`, `git diff`, test output, lint output.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: a pushed `main` branch that triggers the Render deployment.

- [ ] **Step 1: Review the complete diff**

Run:

```bash
git status --short
git diff --stat HEAD~4..HEAD
git log --oneline -6
```

Expected: only intended source, font, test, and spec/plan files; no `.env`, database, or secret files staged.

- [ ] **Step 2: Re-run final verification**

Run:

```bash
.venv/bin/python -m pytest -q
npm run lint:js
```

Expected: all tests pass, lint exits 0.

- [ ] **Step 3: Push to GitHub**

Run:

```bash
git push origin main
```

Expected: push succeeds. Render deploys from `main` using `render.yaml` (`gunicorn wsgi:app`, pre-deploy `flask --app wsgi db upgrade`, health check `/health`).

- [ ] **Step 4: Verify the deployment health endpoint**

Run:

```bash
curl -sS https://<render-service-url>/health
```

Expected: `{"status":"ok","database":"ok"}`. Replace `<render-service-url>` with the URL shown in the Render dashboard.

- [ ] **Step 5: Report the result**

Report the pushed commit hash, test/lint results, local smoke results, and deployment health result. Do not claim deploy success until `/health` returns the expected JSON.
