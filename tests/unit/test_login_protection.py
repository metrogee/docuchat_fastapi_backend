
from unittest.mock import Mock

import pytest

from utils.login_protection import (
    LoginProtection,
    LoginLockedError,
)


def test_email_key_is_normalised():
    first = LoginProtection.key_for(
        "User@Example.com"
    )

    second = LoginProtection.key_for(
        " user@example.com "
    )

    assert first == second
    assert "user@example.com" not in first


def test_login_allowed_under_limit():
    fake_redis = Mock()
    fake_redis.get.return_value = b"3"

    protection = LoginProtection(fake_redis)

    protection.check_allowed(
        "user@example.com"
    )

    fake_redis.get.assert_called_once()


def test_login_locked_after_five_failures():
    fake_redis = Mock()
    fake_redis.get.return_value = b"5"
    fake_redis.ttl.return_value = 600

    protection = LoginProtection(fake_redis)

    with pytest.raises(LoginLockedError) as exc:
        protection.check_allowed(
            "user@example.com"
        )

    assert exc.value.retry_after == 600


def test_fifth_failure_triggers_lockout():
    fake_redis = Mock()
    fake_redis.eval.return_value = [0, 900, 0]

    protection = LoginProtection(fake_redis)

    with pytest.raises(LoginLockedError) as exc:
        protection.record_failure(
            "user@example.com"
        )

    assert exc.value.retry_after == 900


def test_successful_login_resets_counter():
    fake_redis = Mock()

    protection = LoginProtection(fake_redis)

    protection.reset("user@example.com")

    fake_redis.delete.assert_called_once_with(
        LoginProtection.key_for(
            "user@example.com"
        )
    )

# def test_successful_login_clears_failed_attempts():
#     fake_redis = Mock()
#     fake_redis.get.return_value = b"3"

#     protection = LoginProtection(fake_redis)

#     protection.check_allowed("user@example.com")
#     protection.reset("user@example.com")

#     fake_redis.delete.assert_called_once_with(
#         LoginProtection.key_for("user@example.com")
#     )