
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.security_headers import SecurityHeadersMiddleware


app = FastAPI()
app.add_middleware(SecurityHeadersMiddleware)


@app.get("/test")
def sample_endpoint():
    return {"status": "ok"}


client = TestClient(app)


def test_security_headers_present():
    response = client.get("/test")

    assert response.status_code == 200

    assert (
        response.headers["X-Content-Type-Options"]
        == "nosniff"
    )

    assert response.headers["X-Frame-Options"] == "DENY"

    assert (
        response.headers["Referrer-Policy"]
        == "no-referrer"
    )

    assert (
        response.headers["X-XSS-Protection"]
        == "0"
    )


def test_content_security_policy():
    response = client.get("/test")

    csp = response.headers["Content-Security-Policy"]

    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_on_https():
    https_client = TestClient(
        app,
        base_url="https://testserver",
    )

    response = https_client.get("/test")

    assert response.status_code == 200

    assert (
        response.headers["Strict-Transport-Security"]
        == "max-age=15552000"
    )


def test_security_headers_on_error_response():
    response = client.get("/missing-page")

    assert response.status_code == 404

    assert (
        response.headers["X-Content-Type-Options"]
        == "nosniff"
    )
