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
from .services import active_students, daily_csv, get_session, save_attendance
from .weekly import aggregate_weekly
from ..models import AttendanceSession, Student


def _parse_day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return date.today()


@bp.route("/attendance", methods=["GET", "POST"])
@login_required
def daily():
    day = _parse_day(request.values.get("date", date.today().isoformat()))
    attendance_session = get_session(day)

    if request.method == "POST":
        present_ids = set()
        notes = {}
        for student in active_students():
            if request.form.get(f"present_{student.id}") == "on":
                present_ids.add(student.id)
            notes[student.id] = request.form.get(f"note_{student.id}", "")
        save_attendance(day, present_ids, notes, current_user.id)
        flash(f"Attendance saved for {day.isoformat()}.", "success")
        return redirect(url_for("attendance.daily", date=day.isoformat()))

    records = {r.student_id: r for r in attendance_session.records} if attendance_session else {}
    recent = (
        AttendanceSession.query.order_by(AttendanceSession.date.desc()).limit(10).all()
    )
    return render_template(
        "attendance/daily.html",
        day=day,
        students=active_students(),
        records=records,
        recent=recent,
    )


@bp.get("/attendance/export.csv")
@login_required
def export_csv():
    day = _parse_day(request.args.get("date", date.today().isoformat()))
    return Response(
        daily_csv(day),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={day.isoformat()}-c1-attendance.csv"
        },
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
        ["student_id", "name_en", "name_ar", "present", "absent", "percentage", "absent_dates"]
    )
    for item in summary["students"]:
        writer.writerow(
            [
                item["student_id"],
                item["name_en"],
                item["name_ar"],
                item["present"],
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
