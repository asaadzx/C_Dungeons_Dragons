import io
from datetime import date

from openpyxl import load_workbook

from app.extensions import db
from app.models import Student, User


def _seed(app):
    with app.app_context():
        user = User(username="t", role="teacher")
        user.set_password("x")
        s1 = Student(name_en="Present P", name_ar="ح")
        s2 = Student(name_en="Late L", name_ar="خ")
        s3 = Student(name_en="Absent A", name_ar="ط")
        db.session.add_all([user, s1, s2, s3])
        db.session.commit()
        return user.id, s1.id, s2.id, s3.id


def test_excel_has_sections(app):
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
        text = " ".join(
            str(cell.value)
            for row in workbook.active.iter_rows()
            for cell in row
            if cell.value
        )
        assert "ATTENDED" in text
        assert "LATE" in text
        assert "ABSENT" in text
        assert "Present P" in text
        assert "Late L" in text
        assert "Absent A" in text


def test_png_returns_image(app):
    _seed(app)
    with app.app_context():
        from app.attendance.exports import build_png

        data = build_png(date(2026, 10, 22))
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(data) > 100


def test_export_routes_require_login(client):
    assert client.get("/attendance/export.xlsx").status_code == 302
    assert client.get("/attendance/export.png").status_code == 302
