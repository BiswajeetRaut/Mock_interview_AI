"""P2-105 — CORS must be an explicit origin allowlist, never a wildcard
paired with allow_credentials=True."""

import main


def test_no_wildcard_in_allowed_origins():
    assert "*" not in main.ALLOWED_ORIGINS


def test_allowed_origin_gets_cors_header(client):
    resp = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_unlisted_origin_preflight_is_rejected(client):
    resp = client.options(
        "/session/start",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Starlette's CORSMiddleware returns 400 on a preflight from a disallowed
    # origin; the browser blocks the real request from ever being sent.
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}


def test_unlisted_origin_simple_request_has_no_cors_header(client):
    resp = client.get("/", headers={"Origin": "http://evil.example.com"})
    # The request itself isn't blocked server-side (CORS is a browser-enforced
    # policy), but no Access-Control-Allow-Origin header means the browser
    # will refuse to let the calling page read the response.
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}
