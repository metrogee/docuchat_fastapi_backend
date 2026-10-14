from sqlalchemy import select

from database.models import User, Role, UserRole
from database.models import AuditLog
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from fastapi.testclient import TestClient
from server import app
from sqlalchemy import event


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


def test_admin_can_list_roles(client, test_db):
    token = register_user(
        client, "Admin", "admin_roles@example.com"
    )

    admin = test_db.execute(
        select(User).where(User.email == "admin_roles@example.com")
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    test_db.add(
        UserRole(user_id=admin.id, role_id=admin_role.id)
    )
    test_db.commit()

    response = client.get(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True

    roles = {role["name"]: role for role in data["data"]}

    assert {"admin", "member", "viewer"} <= roles.keys()
    assert len(roles["admin"]["permissions"]) == 9
    assert len(roles["member"]["permissions"]) == 5
    assert len(roles["viewer"]["permissions"]) == 2
    assert roles["admin"]["userCount"] >= 1


def test_member_cannot_list_roles(client):
    token = register_user(
        client, "Member", "member_roles@example.com"
    )

    response = client.get(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_unauthenticated_cannot_list_roles(client):
    response = client.get("/api/v1/admin/roles")

    assert response.status_code == 401

def test_admin_can_assign_role(client, test_db):
    admin_token = register_user(
        client, "Admin", "assign_admin@example.com"
    )
    register_user(
        client, "Target", "assign_target@example.com"
    )

    admin = test_db.execute(
        select(User).where(User.email == "assign_admin@example.com")
    ).scalar_one()

    target = test_db.execute(
        select(User).where(User.email == "assign_target@example.com")
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    viewer_role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    test_db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db.commit()

    url = f"/api/v1/admin/users/{target.id}/roles"
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.post(
        url,
        json={"roleName": "viewer"},
        headers=headers,
    )

    assert response.status_code == 200

    assignment = test_db.get(
        UserRole, (target.id, viewer_role.id)
    )

    assert assignment is not None
    assert assignment.assigned_by == admin.id

    # Assigning the same role again must not create a duplicate.
    response = client.post(
        url,
        json={"roleName": "viewer"},
        headers=headers,
    )

    assert response.status_code == 200

    assignments = test_db.execute(
        select(UserRole).where(
            UserRole.user_id == target.id,
            UserRole.role_id == viewer_role.id,
        )
    ).scalars().all()

    assert len(assignments) == 1


def test_member_cannot_assign_role(client, test_db):
    member_token = register_user(
        client, "Member", "assign_member@example.com"
    )

    member = test_db.execute(
        select(User).where(User.email == "assign_member@example.com")
    ).scalar_one()

    response = client.post(
        f"/api/v1/admin/users/{member.id}/roles",
        json={"roleName": "admin"},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert response.status_code == 403

def test_assign_role_to_nonexistent_user(client, test_db):
    token = register_user(
        client, "Admin", "missing_user_admin@example.com"
    )

    admin = test_db.execute(
        select(User).where(
            User.email == "missing_user_admin@example.com"
        )
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    test_db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db.commit()

    response = client.post(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000001/roles",
        json={"roleName": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404


def test_assign_nonexistent_role(client, test_db):
    token = register_user(
        client, "Admin", "missing_role_admin@example.com"
    )

    admin = test_db.execute(
        select(User).where(
            User.email == "missing_role_admin@example.com"
        )
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    test_db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db.commit()

    response = client.post(
        f"/api/v1/admin/users/{admin.id}/roles",
        json={"roleName": "nonexistent_role"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404

def test_admin_can_revoke_role(client, test_db):
    admin_token = register_user(
        client, "Admin", "revoke_admin@example.com"
    )
    register_user(
        client, "Target", "revoke_target@example.com"
    )

    admin = test_db.execute(
        select(User).where(
            User.email == "revoke_admin@example.com"
        )
    ).scalar_one()

    target = test_db.execute(
        select(User).where(
            User.email == "revoke_target@example.com"
        )
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    viewer_role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    test_db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db.add(UserRole(user_id=target.id, role_id=viewer_role.id))
    test_db.commit()

    url = f"/api/v1/admin/users/{target.id}/roles/viewer"
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.delete(url, headers=headers)

    assert response.status_code == 200
    assert test_db.get(UserRole, (target.id, viewer_role.id)) is None

    # Revoking the same role again should be safe.
    response = client.delete(url, headers=headers)

    assert response.status_code == 200


def test_member_cannot_revoke_role(client):
    token = register_user(
        client, "Member", "revoke_member@example.com"
    )

    response = client.delete(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000001/roles/viewer",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 403

def test_role_assignment_creates_audit_log(client, test_db):
    admin_token = register_user(
        client, "Admin", "audit_admin@example.com"
    )
    register_user(
        client, "Target", "audit_target@example.com"
    )

    admin = test_db.execute(
        select(User).where(User.email == "audit_admin@example.com")
    ).scalar_one()

    target = test_db.execute(
        select(User).where(User.email == "audit_target@example.com")
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    test_db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db.commit()

    url = f"/api/v1/admin/users/{target.id}/roles"
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.post(
        url,
        json={"roleName": "viewer"},
        headers=headers,
    )

    assert response.status_code == 200

    logs = test_db.execute(
        select(AuditLog).where(
            AuditLog.target_user_id == target.id,
            AuditLog.action == "role_assigned",
        )
    ).scalars().all()

    assert len(logs) == 1
    assert logs[0].actor_user_id == admin.id
    assert logs[0].role_name == "viewer"
    assert logs[0].created_at is not None

    # A duplicate request shouldn't create another audit record.
    response = client.post(
        url,
        json={"roleName": "viewer"},
        headers=headers,
    )

    assert response.status_code == 200

    logs = test_db.execute(
        select(AuditLog).where(
            AuditLog.target_user_id == target.id,
            AuditLog.action == "role_assigned",
        )
    ).scalars().all()

    assert len(logs) == 1


def test_role_revocation_creates_audit_log(client, test_db):
    admin_token = register_user(
        client, "Admin", "audit_revoke_admin@example.com"
    )
    register_user(
        client, "Target", "audit_revoke_target@example.com"
    )

    admin = test_db.execute(
        select(User).where(
            User.email == "audit_revoke_admin@example.com"
        )
    ).scalar_one()

    target = test_db.execute(
        select(User).where(
            User.email == "audit_revoke_target@example.com"
        )
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    viewer_role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    test_db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    test_db.add(UserRole(user_id=target.id, role_id=viewer_role.id))
    test_db.commit()

    url = f"/api/v1/admin/users/{target.id}/roles/viewer"
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.delete(url, headers=headers)

    assert response.status_code == 200

    logs = test_db.execute(
        select(AuditLog).where(
            AuditLog.target_user_id == target.id,
            AuditLog.action == "role_revoked",
        )
    ).scalars().all()

    assert len(logs) == 1
    assert logs[0].actor_user_id == admin.id
    assert logs[0].role_name == "viewer"
    assert logs[0].created_at is not None

    # Repeated revocation shouldn't produce another audit record.
    response = client.delete(url, headers=headers)

    assert response.status_code == 200

    logs = test_db.execute(
        select(AuditLog).where(
            AuditLog.target_user_id == target.id,
            AuditLog.action == "role_revoked",
        )
    ).scalars().all()

    assert len(logs) == 1

def test_role_assignment_rolls_back_if_audit_fails(
    client, test_db
):
    admin_token = register_user(
        client, "Admin", "rollback_admin@example.com"
    )
    register_user(
        client, "Target", "rollback_target@example.com"
    )

    admin = test_db.execute(
        select(User).where(
            User.email == "rollback_admin@example.com"
        )
    ).scalar_one()

    target = test_db.execute(
        select(User).where(
            User.email == "rollback_target@example.com"
        )
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    viewer_role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    test_db.add(UserRole(
        user_id=admin.id,
        role_id=admin_role.id,
    ))
    test_db.commit()

    # Force audit insertion to fail without changing the database.
    from database.models import AuditLog as AuditLogModel

    original_init = AuditLogModel.__init__

    def fail_audit(self, *args, **kwargs):
        raise SQLAlchemyError("Simulated audit failure")

    with patch.object(AuditLogModel, "__init__", fail_audit):
        with TestClient(
            app,
            raise_server_exceptions=False,
        ) as error_client:
            response = error_client.post(
                f"/api/v1/admin/users/{target.id}/roles",
                json={"roleName": "viewer"},
                headers={
                    "Authorization": f"Bearer {admin_token}"
                },
            )

    assert response.status_code == 500

    test_db.expire_all()

    assignment = test_db.get(
        UserRole,
        (target.id, viewer_role.id),
    )

    assert assignment is None

def test_role_assignment_rolls_back_on_database_failure(client, test_db):
    admin_token = register_user(
        client, "Admin", "db_failure_admin@example.com"
    )
    register_user(
        client, "Target", "db_failure_target@example.com"
    )

    admin = test_db.execute(
        select(User).where(
            User.email == "db_failure_admin@example.com"
        )
    ).scalar_one()

    target = test_db.execute(
        select(User).where(
            User.email == "db_failure_target@example.com"
        )
    ).scalar_one()

    admin_role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    viewer_role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    test_db.add(
        UserRole(user_id=admin.id, role_id=admin_role.id)
    )
    test_db.commit()

    from tests.conftest import TestSessionLocal

    def fail_audit_insert(mapper, connection, target):
        if target.action == "role_assigned":
            raise SQLAlchemyError("Simulated audit insert failure")

    event.listen(AuditLog, "before_insert", fail_audit_insert)

    try:
        with TestClient(app, raise_server_exceptions=False) as error_client:
            response = error_client.post(
                f"/api/v1/admin/users/{target.id}/roles",
                json={"roleName": "viewer"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
    finally:
        event.remove(AuditLog, "before_insert", fail_audit_insert)

    assert response.status_code == 500

    test_db.expire_all()

    assert test_db.get(
        UserRole, (target.id, viewer_role.id)
    ) is None

    logs = test_db.execute(
        select(AuditLog).where(
            AuditLog.target_user_id == target.id,
            AuditLog.action == "role_assigned",
        )
    ).scalars().all()

    assert logs == []

