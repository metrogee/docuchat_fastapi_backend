from sqlalchemy import select

from database.models import Role, User, UserRole
from rbac.service import get_user_permissions


def test_get_user_permissions_returns_member_permissions(test_db):
    # Create a temporary test user
    user = User(
        name="RBAC Member",
        email="rbac_service@example.com",
        password_hash="test-hash",
    )

    test_db.add(user)
    test_db.flush()

    # Retrieve the existing member role
    member_role = test_db.execute(
        select(Role).where(Role.name == "member")
    ).scalar_one()

    # Assign the member role to the user
    test_db.add(
        UserRole(
            user_id=user.id,
            role_id=member_role.id,
        )
    )

    test_db.flush()

    # Retrieve the user's permissions
    permissions = get_user_permissions(user.id, test_db)

    # Verify all five member permissions
    assert permissions == {
        "documents:create",
        "documents:read",
        "documents:update",
        "conversations:create",
        "conversations:read",
    }

def test_admin_permissions(test_db):
    user = User(
        name="Admin Test",
        email="admin_test@example.com",
        password_hash="test-hash",
    )
    test_db.add(user)
    test_db.flush()

    role = test_db.execute(
        select(Role).where(Role.name == "admin")
    ).scalar_one()

    test_db.add(UserRole(user_id=user.id, role_id=role.id))
    test_db.flush()

    permissions = get_user_permissions(user.id, test_db)

    assert len(permissions) == 9
    assert "roles:manage" in permissions
    assert "users:manage" in permissions


def test_viewer_permissions(test_db):
    user = User(
        name="Viewer Test",
        email="viewer_test@example.com",
        password_hash="test-hash",
    )
    test_db.add(user)
    test_db.flush()

    role = test_db.execute(
        select(Role).where(Role.name == "viewer")
    ).scalar_one()

    test_db.add(UserRole(user_id=user.id, role_id=role.id))
    test_db.flush()

    assert get_user_permissions(user.id, test_db) == {
        "documents:read",
        "conversations:read",
    }


def test_user_without_role(test_db):
    user = User(
        name="No Role Test",
        email="no_role@example.com",
        password_hash="test-hash",
    )
    test_db.add(user)
    test_db.flush()

    assert get_user_permissions(user.id, test_db) == set()

def test_multiple_roles_merge_permissions(test_db):
    user = User(
        name="Multi Role User",
        email="multi_role@example.com",
        password_hash="test-hash",
    )
    test_db.add(user)
    test_db.flush()

    roles = test_db.execute(
        select(Role).where(Role.name.in_(["member", "viewer"]))
    ).scalars().all()

    assert len(roles) == 2

    for role in roles:
        test_db.add(
            UserRole(user_id=user.id, role_id=role.id)
        )

    test_db.flush()

    permissions = get_user_permissions(user.id, test_db)

    assert permissions == {
        "documents:create",
        "documents:read",
        "documents:update",
        "conversations:create",
        "conversations:read",
    }

    assert len(permissions) == 5