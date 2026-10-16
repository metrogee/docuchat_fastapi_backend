
from uuid import uuid4


BASE_URL = "/api/v1/documents"


def register_user(client):
    email = f"processing-{uuid4().hex}@example.com"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Processing Test User",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_document(client, token):
    response = client.post(
        BASE_URL,
        json={
            "title": "Processing Status Test",
            "content": "This document needs background processing.",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 202, response.text
    return response.json()


def test_owner_can_check_processing_status(client):
    token = register_user(client)
    payload = create_document(client, token)

    document_id = payload["document"]["id"]

    response = client.get(
        f"{BASE_URL}/{document_id}/processing-status",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["documentId"] == document_id
    assert data["status"] == "pending"
    assert data["progress"] == 0
    assert data["chunkCount"] == 0
    assert data["error"] is None


def test_other_user_cannot_check_processing_status(client):
    owner_token = register_user(client)
    other_token = register_user(client)

    payload = create_document(client, owner_token)
    document_id = payload["document"]["id"]

    response = client.get(
        f"{BASE_URL}/{document_id}/processing-status",
        headers=auth_headers(other_token),
    )

    assert response.status_code == 404


def test_processing_status_requires_authentication(client):
    token = register_user(client)
    payload = create_document(client, token)

    document_id = payload["document"]["id"]

    response = client.get(
        f"{BASE_URL}/{document_id}/processing-status",
    )

    assert response.status_code in (401, 403)


def test_nonexistent_document_returns_404(client):
    token = register_user(client)
    missing_document_id = str(uuid4())

    response = client.get(
        f"{BASE_URL}/{missing_document_id}/processing-status",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
