
from server import allowed_origins


def test_allowed_frontend_origin(client):
    assert allowed_origins
    assert "*" not in allowed_origins

    origin = allowed_origins[0]

    response = client.get(
        "/openapi.json",
        headers={"Origin": origin},
    )

    assert response.status_code == 200

    assert (
        response.headers["access-control-allow-origin"]
        == origin
    )


def test_disallowed_frontend_origin(client):
    response = client.get(
        "/openapi.json",
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 200

    assert (
        "access-control-allow-origin"
        not in response.headers
    )


def test_allowed_preflight_request(client):
    origin = allowed_origins[0]

    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "Content-Type, Authorization"
            ),
        },
    )

    assert response.status_code == 200

    assert (
        response.headers["access-control-allow-origin"]
        == origin
    )

    assert (
        response.headers["access-control-max-age"]
        == "86400"
    )


def test_disallowed_preflight_request(client):
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400

    assert (
        "access-control-allow-origin"
        not in response.headers
    )
