from datetime import datetime, timezone

from sqlalchemy import select

from database.models import Document, Role, User, UserRole


def register_user(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_document(client, token, title):
    response = client.post(
        "/api/v1/documents",
        json={
            "title": title,
            "content": f"Content for {title}",
        },
        headers=headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_document_search_sort_and_pagination(client):
    token = register_user(
        client, "listing@example.com"
    )

    create_document(client, token, "Zebra Notes")
    create_document(client, token, "Alpha Test")
    create_document(client, token, "Another TEST")

    response = client.get(
        "/api/v1/documents",
        params={
            "status": "pending",
            "search": "test",
            "sortBy": "title",
            "sortOrder": "asc",
            "page": 1,
            "limit": 1,
        },
        headers=headers(token),
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["meta"] == {
        "page": 1,
        "limit": 1,
        "total": 2,
    }

    assert len(body["data"]) == 1
    assert body["data"][0]["title"] == "Alpha Test"


def test_deleted_documents_are_hidden(client, test_db):
    token = register_user(
        client, "soft_delete@example.com"
    )

    document_id = create_document(
        client, token, "Document To Delete"
    )

    user = test_db.scalar(
        select(User).where(
            User.email == "soft_delete@example.com"
        )
    )

    admin_role = test_db.scalar(
        select(Role).where(Role.name == "admin")
    )

    test_db.add(
        UserRole(user_id=user.id, role_id=admin_role.id)
    )
    test_db.commit()

    response = client.delete(
        f"/api/v1/documents/{document_id}",
        headers=headers(token),
    )

    assert response.status_code == 200, response.text

    test_db.expire_all()

    document = test_db.get(Document, document_id)

    assert document is not None
    assert document.deleted_at is not None
    assert document.deleted_by == user.id

    list_response = client.get(
        "/api/v1/documents",
        headers=headers(token),
    )

    assert list_response.status_code == 200
    assert list_response.json()["meta"]["total"] == 0

    get_response = client.get(
        f"/api/v1/documents/{document_id}",
        headers=headers(token),
    )

    assert get_response.status_code == 404


def test_document_list_does_not_include_another_users_documents(
    client,
):
    owner_token = register_user(
        client, "private_list_owner@example.com"
    )
    other_token = register_user(
        client, "private_list_other@example.com"
    )

    create_document(client, owner_token, "Private Document")

    response = client.get(
        "/api/v1/documents",
        headers=headers(other_token),
    )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 0


def test_invalid_sort_option_is_rejected(client):
    token = register_user(
        client, "invalid_sort@example.com"
    )

    response = client.get(
        "/api/v1/documents?sortBy=invalid",
        headers=headers(token),
    )

    assert response.status_code == 422