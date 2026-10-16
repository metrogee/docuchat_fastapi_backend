from sqlalchemy import select

from database.models import Role, User, UserRole


def register_user(client, name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_member_can_create_and_read_document(client):
    token = register_user(
        client, "Member", "member_doc@example.com"
    )

    response = client.post(
        "/api/v1/documents",
        json={"title": "Test Document", "content": "Hello DocuChat"},
        headers=auth_headers(token),
    )
    assert response.status_code == 202

    document_id = response.json()["document"]["id"]

    response = client.get(
        f"/api/v1/documents/{document_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200


def test_member_cannot_delete_document(client):
    token = register_user(
        client, "Member", "member_delete@example.com"
    )

    response = client.delete(
        "/api/v1/documents/00000000-0000-0000-0000-000000000001",
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_non_owner_receives_404(client):
    owner_token = register_user(
        client, "Owner", "owner@example.com"
    )
    other_token = register_user(
        client, "Other", "other@example.com"
    )

    response = client.post(
        "/api/v1/documents",
        json={"title": "Private", "content": "Private content"},
        headers=auth_headers(owner_token),
    )
    assert response.status_code == 202

    document_id = response.json()["document"]["id"]

    response = client.get(
        f"/api/v1/documents/{document_id}",
        headers=auth_headers(other_token),
    )
    assert response.status_code == 404


def test_admin_can_read_other_users_document(client, test_db):
    owner_token = register_user(
        client, "Owner", "admin_owner@example.com"
    )
    admin_token = register_user(
        client, "Admin", "admin_reader@example.com"
    )

    admin = test_db.execute(
        select(User).where(User.email == "admin_reader@example.com")
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    test_db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db.commit()

    response = client.post(
        "/api/v1/documents",
        json={"title": "Owner Document", "content": "Test content"},
        headers=auth_headers(owner_token),
    )
    assert response.status_code == 202

    document_id = response.json()["document"]["id"]

    response = client.get(
        f"/api/v1/documents/{document_id}",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200


def test_unauthenticated_document_request(client):
    response = client.get("/api/v1/documents")
    assert response.status_code == 401

def test_viewer_can_read_but_cannot_create(client, test_db):
    token = register_user(
        client, "Viewer", "viewer_doc@example.com"
    )

    user = test_db.execute(
        select(User).where(User.email == "viewer_doc@example.com")
    ).scalar_one()

    member_role = test_db.execute(
        select(Role).where(Role.name == "member")
    ).scalar_one()

    viewer_role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    # Replace the default member role with viewer
    test_db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role_id == member_role.id,
    ).delete()

    test_db.add(UserRole(user_id=user.id, role_id=viewer_role.id))
    test_db.commit()

    read_response = client.get(
        "/api/v1/documents",
        headers=auth_headers(token),
    )
    assert read_response.status_code == 200

    create_response = client.post(
        "/api/v1/documents",
        json={"title": "Viewer Test", "content": "Test content"},
        headers=auth_headers(token),
    )
    assert create_response.status_code == 403


def test_viewer_cannot_delete_document(client, test_db):
    token = register_user(
        client, "Viewer", "viewer_delete@example.com"
    )

    user = test_db.execute(
        select(User).where(User.email == "viewer_delete@example.com")
    ).scalar_one()

    member_role = test_db.execute(
        select(Role).where(Role.name == "member")
    ).scalar_one()

    viewer_role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    test_db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.role_id == member_role.id,
    ).delete()

    test_db.add(UserRole(user_id=user.id, role_id=viewer_role.id))
    test_db.commit()

    response = client.delete(
        "/api/v1/documents/00000000-0000-0000-0000-000000000001",
        headers=auth_headers(token),
    )

    assert response.status_code == 403