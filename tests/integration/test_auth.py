from src.events import event_emitter, EVENT_LOGIN_FAILED

from sqlalchemy import select
from database.database import SessionLocal
from database.models import Role, User, UserRole
import pytest
from unittest.mock import patch
from sqlalchemy import select
from database.models import RefreshToken
from services.auth_service import AuthService

def test_register_successfully(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "integration_test@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert "user" in data
    assert "access_token" in data
    assert "refresh_token" in data

    assert data["user"]["name"] == "Test User"
    assert data["user"]["email"] == "integration_test@example.com"

    assert "password_hash" not in data["user"]


def test_register_with_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "not-an-email",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert "detail" in data


def test_register_duplicate_email(client):
    user_data = {
        "name": "Test User",
        "email": "duplicate@example.com",
        "password": "TestPassword123!",
    }

    first_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert second_response.status_code == 409


def test_login_successfully(client):
    user_data = {
        "name": "Login Test User",
        "email": "login@example.com",
        "password": "TestPassword123!",
    }

    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user_data["email"],
            "password": user_data["password"],
        },
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert "user" in data

    assert data["user"]["email"] == user_data["email"]


def test_login_with_wrong_password(client):
    user_data = {
        "name": "Wrong Password User",
        "email": "wrongpassword@example.com",
        "password": "TestPassword123!",
    }

    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert register_response.status_code == 201

    failed_login_events = []

    event_emitter.on(
        EVENT_LOGIN_FAILED,
        lambda email: failed_login_events.append(email),
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user_data["email"],
            "password": "WrongPassword123!",
        },
    )

    assert login_response.status_code == 401

    data = login_response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid email or password"

    assert failed_login_events == [user_data["email"]]


def test_login_with_nonexistent_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "doesnotexist@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401

    data = response.json()

    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Invalid email or password"


def test_protected_route_without_token(client):
    response = client.get("/api/v1/protected")

    assert response.status_code == 401

    data = response.json()

    assert data["detail"] == "Not authenticated"


def test_protected_route_with_valid_token(client):
    user_data = {
        "name": "Protected Test User",
        "email": "protected@example.com",
        "password": "TestPassword123!",
    }

    register_response = client.post(
        "/api/v1/auth/register",
        json=user_data,
    )

    assert register_response.status_code == 201

    access_token = register_response.json()["access_token"]

    response = client.get(
        "/api/v1/protected",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "You are authenticated"

def test_event_listener_error_does_not_stop_other_listeners():
        results = []

        def failing_listener():
            results.append("first")
            raise Exception("Listener failed")

        def successful_listener():
            results.append("second")

        test_event = "TEST_EVENT"

        event_emitter.on(test_event, failing_listener)
        event_emitter.on(test_event, successful_listener)

        event_emitter.emit(test_event)

        assert results == ["first", "second"]  


def test_register_assigns_default_member_role(client, test_db):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "RBAC Test User",
            "email": "rbac_member@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    user = test_db.execute(
        select(User).where(
            User.email == "rbac_member@example.com"
        )
    ).scalar_one()

    member_role = test_db.execute(
        select(Role).where(Role.name == "member")
    ).scalar_one()

    user_role = test_db.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == member_role.id,
        )
    ).scalar_one_or_none()

    assert user_role is not None
def test_registration_rolls_back_without_default_role(test_db):
    email = "rollback_registration@example.com"

    # Simulate a missing default role without changing seed data.
    original_execute = test_db.execute

    def execute_without_default_role(statement, *args, **kwargs):
        if "roles.is_default" in str(statement):
            class EmptyResult:
                def scalar_one_or_none(self):
                    return None

            return EmptyResult()

        return original_execute(statement, *args, **kwargs)

    service = AuthService()

    with patch.object(
        test_db,
        "execute",
        side_effect=execute_without_default_role,
    ):
        with pytest.raises(
            RuntimeError,
            match="Default role has not been configured",
        ):
            service.register(
                db=test_db,
                name="Rollback Test",
                email=email,
                password="TestPassword123!",
            )

    test_db.expire_all()

    user = test_db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    assert user is None

    # Since no user was committed, there should be no
    # refresh token associated with this registration.
    assert test_db.execute(
        select(RefreshToken)
    ).scalars().all() == []

