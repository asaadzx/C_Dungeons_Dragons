import csv
import io
from datetime import date

from flask import (
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from . import bp
from .dbweekly import aggregate_saved_week, most_recent_sunday
from .exports import build_excel, build_png, group_records
from .services import active_students, daily_csv, get_session, save_attendance
from .weekly import aggregate_weekly
from ..models import AttendanceSession, Student


def _parse_day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


def _download(payload, mimetype, filename):
    """Build a file-download response that is never cached by the browser.

    Exports always use the same URL for a given date, so without no-store the
    browser would serve the previous download after a re-save, making it look
    like the image/CSV never updated. no-store forces a fresh fetch every time.
    """
    response = Response(payload, mimetype=mimetype)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@bp.route("/attendance", methods=["GET", "POST"])
@login_required
def daily():
    day = _parse_day(request.values.get("date", date.today().isoformat()))
    attendance_session = get_session(day)

    if request.method == "POST":
        statuses = {}
        notes = {}
        for student in active_students():
            # Each student has a status_<id> field: present / late / absent.
            statuses[student.id] = request.form.get(f"status_{student.id}", "present")
            notes[student.id] = request.form.get(f"note_{student.id}", "")
        save_attendance(day, statuses, notes, current_user.id)
        flash(f"Attendance saved for {day.isoformat()}.", "success")
        return redirect(url_for("attendance.daily", date=day.isoformat()))

    # The form needs records keyed by student id; the print poster needs three
    # ordered lists. Build both from the same saved session so they cannot drift.
    records = {r.student_id: r for r in attendance_session.records} if attendance_session else {}
    export_groups = (
        group_records(attendance_session.records)
        if attendance_session
        else {"present": [], "late": [], "absent": []}
    )
    recent = (
        AttendanceSession.query.order_by(AttendanceSession.date.desc()).limit(10).all()
    )
    return render_template(
        "attendance/daily.html",
        day=day,
        students=active_students(),
        records=records,
        export_groups=export_groups,
        recent=recent,
    )


@bp.get("/attendance/export.csv")
@login_required
def export_csv():
    day = _parse_day(request.args.get("date", date.today().isoformat()))
    return _download(
        daily_csv(day), "text/csv", f"{day.isoformat()}-c1-attendance.csv"
    )


@bp.get("/attendance/export.xlsx")
@login_required
def export_xlsx():
    day = _parse_day(request.args.get("date", date.today().isoformat()))
    return _download(
        build_excel(day),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # Match the reference project's "c1Class" naming so downloaded files
        # sort together with the PNG. The CSV name stays unchanged.
        f"{day.isoformat()}-c1Class-attendance.xlsx",
    )


@bp.get("/attendance/export.png")
@login_required
def export_png():
    day = _parse_day(request.args.get("date", date.today().isoformat()))
    return _download(
        # The PNG and PDF use the same download stem; the browser adds .pdf
        # from the print dialog title set in daily.html.
        build_png(day),
        "image/png",
        f"{day.isoformat()}-c1Class-attendance.png",
    )


@bp.route("/attendance/week", methods=["GET", "POST"])
@login_required
def weekly():
    summary = None
    if request.method == "POST":
        files = [f for f in request.files.getlist("files") if f and f.filename]
        try:
            summary = aggregate_weekly(files, Student.query.filter_by(active=True).all())
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            session["weekly_summary"] = summary
            flash("Weekly report calculated.", "success")
    return render_template("attendance/weekly.html", summary=summary)


@bp.get("/attendance/week/saved")
@login_required
def week_saved():
    start = _parse_day(request.args.get("start", most_recent_sunday().isoformat()))
    summary = aggregate_saved_week(start)
    return render_template("attendance/week_saved.html", summary=summary, start=start)


@bp.get("/attendance/week/export.csv")
@login_required
def weekly_export():
    summary = session.get("weekly_summary")
    if not summary:
        flash("Upload five daily files first.", "error")
        return redirect(url_for("attendance.weekly"))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["student_id", "name_en", "name_ar", "present", "late", "absent", "percentage", "absent_dates"]
    )
    for item in summary["students"]:
        writer.writerow(
            [
                item["student_id"],
                item["name_en"],
                item["name_ar"],
                item["present"],
                item.get("late", 0),
                item["absent"],
                item["percentage"],
                " ".join(item["absent_dates"]),
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=c1-weekly-attendance.csv"},
    )
