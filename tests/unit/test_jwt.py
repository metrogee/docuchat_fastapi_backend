from utils.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
)


def test_create_and_verify_access_token():
    user_id = "test-user-id"

    token = create_access_token(user_id)
    payload = verify_token(token, "access")

    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_and_verify_refresh_token():
    user_id = "test-user-id"

    token = create_refresh_token(user_id)
    payload = verify_token(token, "refresh")

    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"
    assert "jti" in payload
    assert "exp" in payload


def test_access_token_rejected_as_refresh_token():
    token = create_access_token("test-user-id")

    try:
        verify_token(token, "refresh")
        assert False
    except Exception:
        assert True


def test_refresh_token_rejected_as_access_token():
    token = create_refresh_token("test-user-id")

    try:
        verify_token(token, "access")
        assert False
    except Exception:
        assert True