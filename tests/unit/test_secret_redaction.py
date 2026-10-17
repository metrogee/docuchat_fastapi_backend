
from utils.secret_redaction import (
    redact_text,
    redact_sensitive_data,
)


def test_redacts_bearer_token():
    value = "Authorization: Bearer abc.def.ghi"

    result = redact_text(value)

    assert "abc.def.ghi" not in result
    assert "Bearer [REDACTED]" in result


def test_redacts_api_key():
    value = "Key: sk-abcdefghijklmnopqrstuvwxyz123456"

    result = redact_text(value)

    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in result


def test_redacts_password():
    value = "password=SuperSecret123"

    result = redact_text(value)

    assert "SuperSecret123" not in result


def test_redacts_database_connection():
    value = (
        "Connection failed: "
        "postgresql://admin:secretpass@localhost:5432/docuchat"
    )

    result = redact_text(value)

    assert "secretpass" not in result
    assert "[REDACTED_CONNECTION_URL]" in result


def test_redacts_nested_secrets():
    data = {
        "user": "test@example.com",
        "password": "Secret123",
        "tokens": {
            "access_token": "abc.def.ghi",
            "refresh_token": "refresh-secret",
        },
    }

    result = redact_sensitive_data(data)

    assert result["password"] == "[REDACTED]"
    assert result["tokens"]["access_token"] == "[REDACTED]"
    assert result["tokens"]["refresh_token"] == "[REDACTED]"
    assert result["user"] == "test@example.com"


def test_preserves_safe_values():
    data = {
        "status": "ok",
        "count": 5,
    }

    assert redact_sensitive_data(data) == data
