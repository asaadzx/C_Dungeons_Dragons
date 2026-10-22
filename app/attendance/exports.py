# ---------------------------------------------------------------------------
# app/attendance/exports.py
# Server-side export builders for a single day's attendance:
#   * build_excel(day)  -> .xlsx bytes (openpyxl)
#   * build_png(day)    -> .png bytes (Pillow)
#
# Both reuse day_records() so the data grouping lives in one place and the
# export format never drifts from the CSV.
# ---------------------------------------------------------------------------

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageFont

from .services import get_session

# The project's pixel palette (matches static/css/style.css).
PALETTE = {
    "dark_red": "#BE1A1A",     # background
    "red": "#D0311E",          # headings
    "yellow": "#F7D87F",       # absent highlight
    "cream": "#F8EBAB",        # text
}

# Status order and human labels used in every export.
SECTIONS = [
    ("present", "ATTENDED"),
    ("late", "LATE"),
    ("absent", "ABSENT"),
]


def day_records(day):
    """Group a day's records by status: {status: [records sorted by name]}.

    Returns empty lists when the day has not been saved yet.
    """
    session = get_session(day)
    grouped = {"present": [], "late": [], "absent": []}
    if session is None:
        return grouped

    for record in sorted(session.records, key=lambda r: r.student.name_en):
        grouped.setdefault(record.status, []).append(record)
    return grouped


def build_excel(day):
    """Return an .xlsx workbook as bytes with Attended/Late/Absent sections."""
    records = day_records(day)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Attendance"

    # Column widths (index, letter, width).
    sheet.column_dimensions["A"].width = 6
    sheet.column_dimensions["B"].width = 40
    sheet.column_dimensions["C"].width = 40

    # ---- Title block ----
    sheet["A1"] = f"C1 Attendance - {day.isoformat()}"
    sheet["A1"].font = Font(bold=True, size=14, color=PALETTE["red"][1:])
    sheet.merge_cells("A1:C1")
    sheet["A1"].alignment = Alignment(horizontal="center")

    row = 3
    for status, label in SECTIONS:
        # Section heading.
        sheet.cell(row=row, column=1, value=label)
        heading = sheet.cell(row=row, column=1)
        heading.font = Font(bold=True, size=12, color="FFFFFF")
        heading.fill = PatternFill("solid", fgColor=PALETTE["dark_red"][1:])
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        row += 1

        items = records.get(status, [])

        # Absent and late rows are highlighted so they stand out on paper.
        if status == "absent":
            fill = PatternFill("solid", fgColor=PALETTE["yellow"][1:])
            font = Font(bold=True, size=12)
        elif status == "late":
            fill = PatternFill("solid", fgColor=PALETTE["red"][1:])
            font = Font(bold=True, size=12, color="FFFFFF")
        else:
            fill = None
            font = Font(size=11)

        if not items:
            sheet.cell(row=row, column=1, value="-")
            row += 1
        else:
            for index, record in enumerate(items, start=1):
                cells = [
                    sheet.cell(row=row, column=1, value=index),
                    sheet.cell(row=row, column=2, value=record.student.name_en),
                    sheet.cell(row=row, column=3, value=record.student.name_ar),
                ]
                for cell in cells:
                    cell.font = font
                    if fill is not None:
                        cell.fill = fill
                row += 1
        row += 1  # blank line between sections

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _load_font(size):
    """Return a usable font, falling back to Pillow's default.

    We do not bundle a TTF, so on a fresh host this returns the built-in
    bitmap font. That is small but readable and, crucially, never crashes.
    """
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def build_png(day):
    """Return a poster-style .png (bytes) listing late and absent students."""
    records = day_records(day)
    absent = [r.student.name_en for r in records.get("absent", [])]
    late = [r.student.name_en for r in records.get("late", [])]

    width = 900
    line_height = 46
    header_height = 150
    late_block = 60 + len(late) * line_height if late else 0
    absent_block = 60 + max(len(absent), 1) * line_height
    height = header_height + late_block + absent_block + 80

    image = Image.new("RGB", (width, height), PALETTE["dark_red"])
    draw = ImageDraw.Draw(image)

    title_font = _load_font(40)
    small_font = _load_font(22)
    name_font = _load_font(28)

    # Header.
    draw.text((40, 40), "C1 ATTENDANCE", font=title_font, fill=PALETTE["cream"])
    draw.text((40, 100), day.isoformat(), font=small_font, fill=PALETTE["cream"])

    y = header_height

    # Late section.
    if late:
        draw.text((40, y), "LATE", font=small_font, fill=PALETTE["red"])
        y += 40
        for name in late:
            draw.text((60, y), f"- {name}", font=name_font, fill=PALETTE["cream"])
            y += line_height
        y += 20

    # Absent section.
    draw.text((40, y), "ABSENT", font=small_font, fill=PALETTE["yellow"])
    y += 40
    if absent:
        for name in absent:
            draw.text((60, y), f"- {name}", font=name_font, fill=PALETTE["yellow"])
            y += line_height
    else:
        draw.text((60, y), "Nobody absent. Nice!", font=name_font, fill=PALETTE["cream"])

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
