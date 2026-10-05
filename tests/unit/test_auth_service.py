from unittest.mock import Mock, patch

import pytest

from services.auth_service import AuthService
from utils.errors import ConflictError, UnauthorizedError


def test_register_creates_user_successfully():
    service = AuthService()

    user = Mock()
    user.id = "user-123"
    user.email = "test@example.com"

    service.user_repository = Mock()
    service.refresh_token_repository = Mock()

    service.user_repository.find_by_email.return_value = None
    service.user_repository.create.return_value = user
    service.refresh_token_repository.create.return_value = Mock()

    with patch(
        "services.auth_service.hash_password",
        return_value="hashed-password",
    ), patch(
        "services.auth_service.create_access_token",
        return_value="access-token",
    ), patch(
        "services.auth_service.create_refresh_token",
        return_value="refresh-token",
    ), patch(
        "services.auth_service.hash_refresh_token",
        return_value="refresh-hash",
    ), patch(
        "services.auth_service.event_emitter.emit",
    ) as emit:

        result = service.register(
            Mock(),
            "Test User",
            "test@example.com",
            "TestPassword123!",
        )

    assert result["user"] is user
    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"

    service.user_repository.create.assert_called_once()
    service.refresh_token_repository.create.assert_called_once()

    emit.assert_called_once()


def test_register_rejects_duplicate_email():
    service = AuthService()

    existing_user = Mock()

    service.user_repository = Mock()
    service.refresh_token_repository = Mock()

    service.user_repository.find_by_email.return_value = existing_user

    with pytest.raises(
        ConflictError,
        match="Email already registered",
    ):
        service.register(
            Mock(),
            "Test User",
            "test@example.com",
            "TestPassword123!",
        )

    service.user_repository.create.assert_not_called()
    service.refresh_token_repository.create.assert_not_called()


def test_login_accepts_valid_credentials():
    service = AuthService()

    user = Mock()
    user.id = "user-123"
    user.email = "test@example.com"
    user.password_hash = "hashed-password"

    service.user_repository = Mock()
    service.refresh_token_repository = Mock()

    service.user_repository.find_by_email.return_value = user
    service.refresh_token_repository.create.return_value = Mock()

    with patch(
        "services.auth_service.verify_password",
        return_value=True,
    ), patch(
        "services.auth_service.create_access_token",
        return_value="access-token",
    ), patch(
        "services.auth_service.create_refresh_token",
        return_value="refresh-token",
    ), patch(
        "services.auth_service.hash_refresh_token",
        return_value="refresh-hash",
    ), patch(
        "services.auth_service.event_emitter.emit",
    ) as emit:

        result = service.login(
            Mock(),
            "test@example.com",
            "TestPassword123!",
        )

    assert result["user"] is user
    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"

    emit.assert_called_once()


def test_login_rejects_wrong_password():
    service = AuthService()

    user = Mock()
    user.password_hash = "hashed-password"

    service.user_repository = Mock()
    service.user_repository.find_by_email.return_value = user

    with patch(
        "services.auth_service.verify_password",
        return_value=False,
    ):
        with pytest.raises(
            UnauthorizedError,
            match="Invalid email or password",
        ):
            service.login(
                Mock(),
                "test@example.com",
                "WrongPassword123!",
            )


def test_login_rejects_nonexistent_email():
    service = AuthService()

    service.user_repository = Mock()
    service.user_repository.find_by_email.return_value = None

    with pytest.raises(
        UnauthorizedError,
        match="Invalid email or password",
    ):
        service.login(
            Mock(),
            "doesnotexist@example.com",
            "TestPassword123!",
        )