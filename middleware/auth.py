from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from database.database import get_db
from repositories.user_repository import UserRepository
from utils.jwt import verify_token
from utils.errors import UnauthorizedError, ForbiddenError
from rbac.service import get_user_permissions

security = HTTPBearer()

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = verify_token(token, "access")

    except ExpiredSignatureError:
        raise UnauthorizedError("Token expired")
    except (InvalidTokenError, ValueError):
        raise UnauthorizedError("Invalid token")

    user_id = payload.get("sub")

    if not user_id:
        raise UnauthorizedError("Invalid token")

    user_repository = UserRepository()

    user = user_repository.find_by_id(
        db=db,
        user_id=user_id,
    )

    if not user:
        raise UnauthorizedError("Invalid token")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive")
    return user


def require_role(required_role: str):
    async def role_checker(
        user=Depends(require_auth),
    ):
        if user.role != required_role:
            raise ForbiddenError("Insufficient permissions")

        return user
    return role_checker

def require_tier(required_tier: str):
    async def tier_checker(
        user=Depends(require_auth),
    ):
        if user.tier != required_tier:
            raise ForbiddenError("Insufficient tier permissions")

        return user

    return tier_checker

def require_permission(*required_permissions: str):
    async def permission_checker(
        user=Depends(require_auth),
        db: Session = Depends(get_db),
    ):
        user_permissions = get_user_permissions(user.id, db)

        if not all(
            permission in user_permissions
            for permission in required_permissions
        ):
            raise ForbiddenError("Insufficient permissions")

        return user

    return permission_checker