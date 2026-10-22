from app.security import safe_url


def test_safe_url_rejects_javascript():
    assert safe_url("javascript:alert(1)") == ""
    assert safe_url("https://example.com") == "https://example.com"
    assert safe_url("") == ""
    assert safe_url("data:text/html,x") == ""


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
