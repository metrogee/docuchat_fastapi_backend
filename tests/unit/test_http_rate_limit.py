
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.rate_limit import APIRateLimitMiddleware


def create_test_client(redis_client):
    app = FastAPI()

    app.add_middleware(
        APIRateLimitMiddleware,
        redis_client=redis_client,
    )

    @app.post("/api/v1/auth/login")
    def login():
        return {"success": True}

    @app.get("/api/v1/documents")
    def documents():
        return {"data": []}

    return TestClient(app)


def test_request_under_limit():
    fake_redis = Mock()
    fake_redis.eval.return_value = [1, 60, 9]

    with create_test_client(fake_redis) as client:
        response = client.post("/api/v1/auth/login")

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert response.headers["X-RateLimit-Remaining"] == "9"


def test_exceeded_limit_returns_429():
    fake_redis = Mock()
    fake_redis.eval.return_value = [0, 42, 0]

    with create_test_client(fake_redis) as client:
        response = client.post("/api/v1/auth/login")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
    assert response.json()["error"]["code"] == (
        "RATE_LIMIT_EXCEEDED"
    )


def test_general_api_limit():
    fake_redis = Mock()
    fake_redis.eval.return_value = [1, 45, 99]

    with create_test_client(fake_redis) as client:
        response = client.get("/api/v1/documents")

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "100"


def test_non_api_routes_are_not_limited():
    fake_redis = Mock()

    app = FastAPI()
    app.add_middleware(
        APIRateLimitMiddleware,
        redis_client=fake_redis,
    )

    @app.get("/")
    def home():
        return {"message": "OK"}

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    fake_redis.eval.assert_not_called()


def test_different_paths_have_different_limits():
    assert APIRateLimitMiddleware.get_limit(
        "/api/v1/auth/register"
    ) == (5, 60)

    assert APIRateLimitMiddleware.get_limit(
        "/api/v1/auth/login"
    ) == (10, 60)

    assert APIRateLimitMiddleware.get_limit(
        "/api/v1/auth/refresh"
    ) == (20, 60)
