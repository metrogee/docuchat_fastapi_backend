from unittest.mock import Mock

import pytest

from services.user_service import UserService


def test_get_user_by_email():
    repository = Mock()
    expected_user = Mock()

    repository.find_by_email.return_value = expected_user

    service = UserService()
    service.repository = repository

    result = service.get_user_by_email(
        Mock(),
        "test@example.com",
    )

    assert result is expected_user

    repository.find_by_email.assert_called_once_with(
        service.repository.find_by_email.call_args.args[0],
        "test@example.com",
    )


def test_create_user_successfully():
    repository = Mock()
    expected_user = Mock()

    repository.find_by_email.return_value = None
    repository.create.return_value = expected_user

    service = UserService()
    service.repository = repository

    result = service.create_user(
        Mock(),
        "Test User",
        "test@example.com",
        "hashed-password",
    )

    assert result is expected_user

    repository.find_by_email.assert_called_once()
    repository.create.assert_called_once()


def test_create_user_rejects_duplicate_email():
    repository = Mock()
    existing_user = Mock()

    repository.find_by_email.return_value = existing_user

    service = UserService()
    service.repository = repository

    with pytest.raises(
        ValueError,
        match="Email already registered",
    ):
        service.create_user(
            Mock(),
            "Test User",
            "test@example.com",
            "hashed-password",
        )

    repository.create.assert_not_called()