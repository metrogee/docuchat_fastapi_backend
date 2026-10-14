from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from database.database import SessionLocal
from database.models import Permission, Role, RolePermission, User, UserRole


db = SessionLocal()

permissions = [
    ("documents", "create", "Create documents"),
    ("documents", "read", "Read documents"),
    ("documents", "update", "Update documents"),
    ("documents", "delete", "Delete documents"),
    ("conversations", "create", "Create conversations"),
    ("conversations", "read", "Read conversations"),
    ("users", "read", "Read users"),
    ("users", "manage", "Manage users"),
    ("roles", "manage", "Manage roles"),
]

for resource, action, description in permissions:
    result = db.execute(
        select(Permission).where(
            Permission.resource == resource,
            Permission.action == action,
        )
    )
    permission = result.scalar_one_or_none()

    if permission is None:
        permission = Permission(
            name=f"{resource}:{action}",
            description=description,
            resource=resource,
            action=action,
        )
        db.add(permission)

db.commit()

roles = {
    "admin": {
        "description": "Full system access",
        "is_default": False,
        "permissions": [
            "documents:create",
            "documents:read",
            "documents:update",
            "documents:delete",
            "conversations:create",
            "conversations:read",
            "users:read",
            "users:manage",
            "roles:manage",
        ],
    },
    "member": {
        "description": "Standard member access",
        "is_default": True,
        "permissions": [
            "documents:create",
            "documents:read",
            "documents:update",
            "conversations:create",
            "conversations:read",
        ],
    },
    "viewer": {
        "description": "Read-only access",
        "is_default": False,
        "permissions": [
            "documents:read",
            "conversations:read",
        ],
    },
}

role_objects = {}

for role_name, role_data in roles.items():
    result = db.execute(
        select(Role).where(Role.name == role_name)
    )
    role = result.scalar_one_or_none()

    if role is None:
        role = Role(
            name=role_name,
            description=role_data["description"],
            is_default=role_data["is_default"],
        )
        db.add(role)
    else:
        role.description = role_data["description"]
        role.is_default = role_data["is_default"]

    role_objects[role_name] = role

db.commit()

for role_name, role_data in roles.items():
    role = role_objects[role_name]

    for permission_name in role_data["permissions"]:
        permission = db.execute(
            select(Permission).where(Permission.name == permission_name)
        ).scalar_one()

        existing = db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
        ).scalar_one_or_none()

        if existing is None:
            db.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                )
            )

db.commit()

user_role_assignments = {
    "test@example.com": "admin",
    "test2@example.com": "member",
}

for email, role_name in user_role_assignments.items():
    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    role = role_objects[role_name]

    if user is None:
        print(f"User not found: {email}")
        continue

    existing = db.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
            )
        )

db.commit()

print("RBAC seed completed successfully.")
db.close()