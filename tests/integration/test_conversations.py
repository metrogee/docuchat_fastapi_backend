from uuid import uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import SQLAlchemyError

from database.models import (
    Conversation,
    Document,
    Message,
    UsageLog,
    User,
)
from services.conversation_service import ConversationService
from tests.conftest import TestSessionLocal


BASE_URL = "/api/v1/conversations"


def register_user(client, name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_conversation(client, token, title="Test Conversation"):
    response = client.post(
        BASE_URL,
        json={"title": title},
        headers=auth_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def send_message(client, token, conversation_id, **kwargs):
    payload = {"content": "What does this document mean?"}
    payload.update(kwargs)

    return client.post(
        f"{BASE_URL}/{conversation_id}/messages",
        json=payload,
        headers=auth_headers(token),
    )


def test_create_and_list_conversations(client):
    token = register_user(
        client, "Owner", "conversation_owner@example.com"
    )

    conversation_id = create_conversation(client, token)

    response = client.get(
        BASE_URL,
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()

    assert body["meta"] == {
        "page": 1,
        "limit": 20,
        "total": 1,
    }
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == conversation_id
    assert body["data"][0]["messageCount"] == 0
    assert body["data"][0]["lastMessage"] is None


def test_conversation_list_is_private_and_paginated(client):
    owner_token = register_user(
        client, "Owner", "list_owner@example.com"
    )
    other_token = register_user(
        client, "Other", "list_other@example.com"
    )

    for i in range(3):
        create_conversation(client, owner_token, f"Conversation {i}")

    create_conversation(client, other_token, "Private Conversation")

    response = client.get(
        f"{BASE_URL}?page=2&limit=2",
        headers=auth_headers(owner_token),
    )

    assert response.status_code == 200
    body = response.json()

    assert body["meta"]["total"] == 3
    assert body["meta"]["page"] == 2
    assert body["meta"]["limit"] == 2
    assert len(body["data"]) == 1
    assert all(
        item["title"] != "Private Conversation"
        for item in body["data"]
    )


def test_send_message_creates_messages_and_usage_log(
    client, test_db
):
    token = register_user(
        client, "Sender", "message_sender@example.com"
    )
    conversation_id = create_conversation(client, token)

    response = send_message(client, token, conversation_id)

    assert response.status_code == 201, response.text

    body = response.json()

    assert body["userMessage"]["role"] == "user"
    assert body["assistantMessage"]["role"] == "assistant"
    assert (
        body["assistantMessage"]["content"]
        == "AI response placeholder (Week 4)"
    )

    messages = test_db.scalars(
        select(Message).where(
            Message.conversation_id == conversation_id
        )
    ).all()

    assert len(messages) == 2

    conversation = test_db.get(Conversation, conversation_id)
    assert conversation is not None

    user = test_db.scalar(
        select(User).where(
            User.email == "message_sender@example.com"
        )
    )

    logs = test_db.scalars(
        select(UsageLog).where(
            UsageLog.user_id == user.id,
            UsageLog.action == "chat",
        )
    ).all()

    assert len(logs) == 1
    assert logs[0].tokens == 0

    list_response = client.get(
        BASE_URL,
        headers=auth_headers(token),
    )

    assert list_response.status_code == 200
    listed = list_response.json()["data"][0]
    assert listed["messageCount"] == 2
    assert listed["lastMessage"]["role"] == "assistant"


def test_cannot_send_message_to_another_users_conversation(
    client, test_db
):
    owner_token = register_user(
        client, "Owner", "message_owner@example.com"
    )
    other_token = register_user(
        client, "Other", "message_other@example.com"
    )

    conversation_id = create_conversation(client, owner_token)

    response = send_message(
        client, other_token, conversation_id
    )

    assert response.status_code == 404

    count = test_db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )
    assert count == 0


def test_nonexistent_document_is_rejected(client, test_db):
    token = register_user(
        client, "Sender", "missing_doc_sender@example.com"
    )
    conversation_id = create_conversation(client, token)

    response = send_message(
        client,
        token,
        conversation_id,
        document_id=str(uuid4()),
    )

    assert response.status_code == 404

    count = test_db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )
    assert count == 0


def test_soft_deleted_document_is_rejected(client, test_db):
    token = register_user(
        client, "Sender", "deleted_doc_sender@example.com"
    )
    conversation_id = create_conversation(client, token)

    document_response = client.post(
        "/api/v1/documents",
        json={
            "title": "Deleted Document",
            "content": "Document content",
        },
        headers=auth_headers(token),
    )

    assert document_response.status_code == 202

    document_id = document_response.json()["document"]["id"]
    document = test_db.get(Document, document_id)

    from datetime import datetime, timezone

    document.deleted_at = datetime.now(timezone.utc)
    test_db.commit()

    response = send_message(
        client,
        token,
        conversation_id,
        document_id=document_id,
    )

    assert response.status_code == 404

    count = test_db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )
    assert count == 0


def test_send_message_rolls_back_if_usage_insert_fails(
    client, test_db
):
    token = register_user(
        client, "Sender", "rollback_message@example.com"
    )
    conversation_id = create_conversation(client, token)

    conversation = test_db.get(Conversation, conversation_id)
    original_updated_at = conversation.updated_at

    def fail_usage_insert(mapper, connection, target):
        if target.action == "chat":
            raise SQLAlchemyError("Simulated usage insert failure")

    event.listen(UsageLog, "before_insert", fail_usage_insert)

    user_id = test_db.scalar(
        select(User.id).where(
            User.email == "rollback_message@example.com"
        )
    )

    service = ConversationService()

    try:
        with TestSessionLocal() as db:
            with pytest.raises(SQLAlchemyError):
                service.send_message(
                    db=db,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    content="Test rollback",
                )
    finally:
        event.remove(
            UsageLog, "before_insert", fail_usage_insert
        )

    test_db.expire_all()

    conversation = test_db.get(Conversation, conversation_id)
    assert conversation.updated_at == original_updated_at

    message_count = test_db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )

    assert message_count == 0

    user = test_db.scalar(
        select(User).where(
            User.email == "rollback_message@example.com"
        )
    )

    usage_count = test_db.scalar(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user.id,
            UsageLog.action == "chat",
        )
    )

    assert usage_count == 0