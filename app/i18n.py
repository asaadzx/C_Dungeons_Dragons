# ---------------------------------------------------------------------------
# app/i18n.py
# Very small translation layer for the English/Arabic UI toggle.
#
# The chosen language is stored in the Flask session. A context processor
# exposes `lang`, `dir` and `t()` to every template, so templates can write
# {{ t('nav.bulletin') }} and the page direction flips automatically for
# Arabic (dir="rtl").
# ---------------------------------------------------------------------------

from flask import redirect, request, session, url_for

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "ar")

# Translation table: English key -> {lang: text}. Missing entries fall back to
# the key's English text.
TRANSLATIONS = {
    "app.title": {
        "en": "C1 RAS Hub",
        "ar": "مركز الصف الأول",
    },
    "nav.bulletin": {"en": "Bulletin", "ar": "النشرة"},
    "nav.news": {"en": "News", "ar": "الأخبار"},
    "nav.calendar": {"en": "Calendar", "ar": "التقويم"},
    "nav.lhr": {"en": "LHR Games", "ar": "ألعاب الغرفة"},
    "nav.directory": {"en": "Directory", "ar": "دليل الطلاب"},
    "nav.attendance": {"en": "Attendance", "ar": "الحضور"},
    "nav.weekly": {"en": "Weekly", "ar": "التقرير الأسبوعي"},
    "nav.admin": {"en": "Staff Panel", "ar": "لوحة المعلمين"},
    "nav.login": {"en": "Log in", "ar": "تسجيل الدخول"},
    "nav.logout": {"en": "Log out", "ar": "تسجيل الخروج"},
    "nav.language": {"en": "العربية", "ar": "English"},
    "common.read_more": {"en": "Read more", "ar": "اقرأ المزيد"},
    "common.load_more": {"en": "Load more", "ar": "تحميل المزيد"},
}


def get_lang():
    """Return the language for this request, defaulting to English."""
    lang = session.get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def translate(key):
    """Return the translated string for key, falling back to English."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(get_lang(), entry.get(DEFAULT_LANG, key))


def register_i18n(app):
    """Register the language route and the template context processor."""

    @app.route("/set-language/<lang>")
    def set_language(lang):
        if lang in SUPPORTED_LANGS:
            session["lang"] = lang
        # Go back to the page the user was viewing (fall back to home).
        return redirect(request.referrer or url_for("hub.index"))

    @app.context_processor
    def inject_i18n():
        lang = get_lang()
        return {
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "other_lang": "en" if lang == "ar" else "ar",
            "t": translate,
        }
