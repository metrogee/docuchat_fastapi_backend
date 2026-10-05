from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from database.database import get_db
from repositories.user_repository import UserRepository
from utils.jwt import verify_token
from utils.errors import UnauthorizedError, ForbiddenError

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