import json

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import patch

from database.models import Role, UsageLog, User, UserRole


def register_user(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Audit Test User",
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_document_event_failure_does_not_break_creation(
    client, test_db
):
    from database.models import Document
    from src.events import (
        event_emitter,
        EVENT_DOCUMENT_CREATED,
    )

    token = register_user(
        client, "document_event_failure@example.com"
    )

    listeners = event_emitter._listeners[EVENT_DOCUMENT_CREATED]
    original_listeners = listeners[:]

    def fail_logging(**kwargs):
        raise SQLAlchemyError("Simulated logging failure")

    listeners[:] = [fail_logging]

    try:
        response = client.post(
            "/api/v1/documents",
            json={
                "title": "Resilient Document",
                "content": "This should still be created",
            },
            headers=headers(token),
        )
    finally:
        listeners[:] = original_listeners

    assert response.status_code == 202, response.text

    document_id = response.json()["document"]["id"]

    test_db.expire_all()

    assert test_db.get(Document, document_id) is not None

    user = test_db.scalar(
        select(User).where(
            User.email == "document_event_failure@example.com"
        )
    )

    logs = test_db.scalars(
        select(UsageLog).where(
            UsageLog.user_id == user.id,
            UsageLog.action == "document_created",
        )
    ).all()

    assert logs == []


def test_document_deletion_creates_usage_log(client, test_db):
    token = register_user(
        client, "document_event_delete@example.com"
    )

    user = test_db.scalar(
        select(User).where(
            User.email == "document_event_delete@example.com"
        )
    )

    admin_role = test_db.scalar(
        select(Role).where(Role.name == "admin")
    )

    test_db.add(
        UserRole(
            user_id=user.id,
            role_id=admin_role.id,
        )
    )
    test_db.commit()

    create_response = client.post(
        "/api/v1/documents",
        json={
            "title": "Delete Audit Document",
            "content": "Sample content",
        },
        headers=headers(token),
    )

    assert create_response.status_code == 202
    document_id = create_response.json()["document"]["id"]

    delete_response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers=headers(token),
    )

    assert delete_response.status_code == 200

    logs = test_db.scalars(
        select(UsageLog).where(
            UsageLog.user_id == user.id,
            UsageLog.action == "document_deleted",
        )
    ).all()

    assert len(logs) == 1

    metadata = json.loads(logs[0].details)

    assert metadata["documentId"] == document_id
    assert metadata["title"] == "Delete Audit Document"
    assert metadata["deletedAt"]


def test_document_event_failure_does_not_break_creation(
    client, test_db
):
    token = register_user(
        client, "document_event_failure@example.com"
    )

    with patch(
        "src.document_events.log_document_created",
        side_effect=SQLAlchemyError("Simulated logging failure"),
    ):
        response = client.post(
            "/api/v1/documents",
            json={
                "title": "Resilient Document",
                "content": "This should still be created",
            },
            headers=headers(token),
        )

    assert response.status_code == 202

    # The document should exist even if activity logging fails.
    from database.models import Document

    assert test_db.get(
        Document, response.json()["document"]["id"]
    ) is not None

def test_document_creation_creates_usage_log(client, test_db):
    import json

    token = register_user(
        client, "document_event_create@example.com"
    )

    response = client.post(
        "/api/v1/documents",
        json={
            "title": "Audit Document",
            "content": "Hello DocuChat",
        },
        headers=headers(token),
    )

    assert response.status_code == 202, response.text

    document_id = response.json()["document"]["id"]

    user = test_db.scalar(
        select(User).where(
            User.email == "document_event_create@example.com"
        )
    )

    logs = test_db.scalars(
        select(UsageLog).where(
            UsageLog.user_id == user.id,
            UsageLog.action == "document_created",
        )
    ).all()

    assert len(logs) == 1

    metadata = json.loads(logs[0].details)

    assert metadata["documentId"] == document_id
    assert metadata["title"] == "Audit Document"
    assert metadata["fileSizeBytes"] == len(
        "Hello DocuChat".encode("utf-8")
    )