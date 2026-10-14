from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Permission, RolePermission, UserRole


def get_user_permissions(user_id: str, db: Session) -> set[str]:
    """Return all unique permissions assigned to a user through their roles."""

    statement = (
        select(Permission.name)
        .join(
            RolePermission,
            RolePermission.permission_id == Permission.id,
        )
        .join(
            UserRole,
            UserRole.role_id == RolePermission.role_id,
        )
        .where(UserRole.user_id == user_id)
    )

    permissions = db.execute(statement).scalars().all()

    return set(permissions)