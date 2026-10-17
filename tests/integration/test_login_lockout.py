
from unittest.mock import patch
from services.auth_service import AuthService
from routes.auth_routes import auth_service
from unittest.mock import Mock
from redis.exceptions import ConnectionError as RedisConnectionError
from utils.login_protection import LoginProtection


def test_account_lockout_after_five_failed_logins(client):
    email = "lockout-test@example.com"

    class FakeRedis:
        def __init__(self):
            self.counts = {}

        def get(self, key):
            count = self.counts.get(key, 0)
            return str(count).encode() if count else None

        def ttl(self, key):
            return 900

        def eval(self, script, numkeys, key, window, limit):
            count = self.counts.get(key, 0) + 1
            self.counts[key] = count

            return [
                1 if count <= limit else 0,
                900,
                max(0, limit - count),
            ]

        def delete(self, key):
            self.counts.pop(key, None)

    fake_redis = FakeRedis()

    with patch.object(
        auth_service,
        "login_protection",
        LoginProtection(redis_client=fake_redis),
    ):
        responses = []

        for _ in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": email,
                    "password": "IncorrectPassword123!",
                },
            )

            responses.append(response)

        assert responses[0].status_code == 401
        assert responses[1].status_code == 401
        assert responses[2].status_code == 401
        assert responses[3].status_code == 401
        assert responses[4].status_code == 429

        blocked = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "IncorrectPassword123!",
            },
        )

        assert blocked.status_code == 429
        assert blocked.headers["Retry-After"] == "900"
        assert blocked.json()["error"]["code"] == (
            "LOGIN_RATE_LIMITED"
        )


def test_successful_login_resets_failed_attempts(client):
    email = "login-reset@example.com"
    password = "TestPassword123!"

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Reset Test User",
            "email": email,
            "password": password,
        },
    )

    assert registration.status_code == 201, registration.text

    fake_redis = Mock()
    fake_redis.get.return_value = b"0"
    fake_redis.eval.return_value = [1, 900, 3]

    protection = LoginProtection(redis_client=fake_redis)

    with patch.object(
        auth_service,
        "login_protection",
        protection,
    ):
        failed = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "WrongPassword123!",
            },
        )

        assert failed.status_code == 401
        fake_redis.eval.assert_called_once()

        successful = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )

        assert successful.status_code == 200, successful.text
        assert "access_token" in successful.json()

        fake_redis.delete.assert_called_once_with(
            LoginProtection.key_for(email)
        )


def test_login_returns_503_when_redis_unavailable(client):
    fake_redis = Mock()

    fake_redis.get.side_effect = RedisConnectionError(
        "Redis connection unavailable"
    )

    protection = LoginProtection(redis_client=fake_redis)

    with patch.object(
        auth_service,
        "login_protection",
        protection,
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "redis-outage@example.com",
                "password": "TestPassword123!",
            },
        )

    assert response.status_code == 503

    assert response.json()["error"]["code"] == (
        "LOGIN_PROTECTION_UNAVAILABLE"
    )

    assert response.headers["cache-control"] == "no-store"

