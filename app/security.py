# ---------------------------------------------------------------------------
# app/security.py
# Small security helpers shared across blueprints.
# ---------------------------------------------------------------------------

from urllib.parse import urlparse

# Only these schemes are allowed in user-supplied links. Anything else
# (javascript:, data:, vbscript:, ...) could run script when clicked.
SAFE_SCHEMES = {"http", "https"}


def safe_url(value):
    """Return a URL only if it is http(s) with a host, otherwise an empty string.

    Used as a Jinja filter: {{ user_link|safe_url }}. Empty output means
    "do not render a link", which blocks javascript: and similar XSS vectors.
    """
    value = (value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in SAFE_SCHEMES:
        return ""
    if not parsed.netloc:
        return ""
    return value


def add_security_headers(response):
    """Attach a few defensive HTTP headers to every response."""
    # Stop browsers from guessing content types (blocks some XSS tricks).
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    # Do not allow the site to be embedded in an iframe (clickjacking).
    response.headers.setdefault("X-Frame-Options", "DENY")
    # Do not leak the full URL to third-party sites.
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response
