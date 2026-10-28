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
from functools import lru_cache
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from PIL import Image, ImageDraw, ImageFont

from .services import get_session

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

REFERENCE = {
    "green": "DCFCE7",
    "amber": "FDE68A",
    "yellow": "FFE600",
    "yellow_soft": "FFF2B0",
    "black": "000000",
    "white": "FFFFFF",
}


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
