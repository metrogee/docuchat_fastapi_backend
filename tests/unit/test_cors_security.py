
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=86400,
)


@app.get("/test")
def sample_endpoint():
    return {"status": "ok"}


client = TestClient(app)


def test_allowed_origin():
    response = client.get(
        "/test",
        headers={"Origin": "http://localhost:3001"},
    )

    assert response.status_code == 200
    assert (
        response.headers["Access-Control-Allow-Origin"]
        == "http://localhost:3001"
    )


def test_disallowed_origin():
    response = client.get(
        "/test",
        headers={"Origin": "http://evil.com"},
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_preflight_request():
    response = client.options(
        "/test",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["Access-Control-Allow-Credentials"]
        == "true"
    )
    assert (
        response.headers["Access-Control-Max-Age"]
        == "86400"
    )


def test_disallowed_preflight():
    response = client.options(
        "/test",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "Access-Control-Allow-Origin" not in response.headers
