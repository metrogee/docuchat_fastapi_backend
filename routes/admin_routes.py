from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Role, UserRole
from middleware.auth import require_permission
from pydantic import BaseModel
from database.models import User, Role, UserRole
from utils.errors import NotFoundError
from database.models import AuditLog
from src.events import (
    event_emitter,
    EVENT_ADMIN_ROLE_ASSIGNED,
    EVENT_ADMIN_ROLE_REVOKED,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

class AssignRoleRequest(BaseModel):
    roleName: str

@router.get("/roles")
async def list_roles(
    user=Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
):
    roles = db.execute(
        select(Role).order_by(Role.name)
    ).scalars().all()

    role_counts = dict(
        db.execute(
            select(UserRole.role_id, func.count(UserRole.user_id))
            .group_by(UserRole.role_id)
        ).all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "isDefault": role.is_default,
                "userCount": role_counts.get(role.id, 0),
                "permissions": sorted(
                    rp.permission.name
                    for rp in role.permissions
                ),
            }
            for role in roles
        ],
    }

@router.post("/users/{user_id}/roles")
async def assign_role(
    user_id: str,
    data: AssignRoleRequest,
    admin=Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)

    if user is None:
        raise NotFoundError("User not found")

    role = db.execute(
        select(Role).where(Role.name == data.roleName)
    ).scalar_one_or_none()

    if role is None:
        raise NotFoundError("Role not found")

    existing = db.get(
        UserRole,
        (user_id, role.id),
    )

    if existing is None:
        assignment = UserRole(
            user_id=user_id,
            role_id=role.id,
            assigned_by=admin.id,
        )

        db.add(assignment)

        db.add(
            AuditLog(
                actor_user_id=admin.id,
                target_user_id=user_id,
                action="role_assigned",
                role_name=role.name,
            )
        )

        db.commit()

        event_emitter.emit(
            EVENT_ADMIN_ROLE_ASSIGNED,
            actor_user_id=admin.id,
            target_user_id=user_id,
            role_name=role.name,
        )

    return {
        "success": True,
        "data": {
            "message": f"Role '{role.name}' assigned to user",
        },
    }

@router.delete("/users/{user_id}/roles/{role_name}")
async def revoke_role(
    user_id: str,
    role_name: str,
    admin=Depends(require_permission("roles:manage")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)

    if user is None:
        raise NotFoundError("User not found")

    role = db.execute(
        select(Role).where(Role.name == role_name)
    ).scalar_one_or_none()

    if role is None:
        raise NotFoundError("Role not found")

    assignment = db.get(
        UserRole,
        (user_id, role.id),
    )

    if assignment is not None:
        db.delete(assignment)

        db.add(
            AuditLog(
                actor_user_id=admin.id,
                target_user_id=user_id,
                action="role_revoked",
                role_name=role.name,
            )
        )

        db.commit()

        event_emitter.emit(
            EVENT_ADMIN_ROLE_REVOKED,
            actor_user_id=admin.id,
            target_user_id=user_id,
            role_name=role.name,
        )

    return {
        "success": True,
        "data": {
            "message": f"Role '{role.name}' revoked",
        },
    }