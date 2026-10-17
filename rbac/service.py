
import logging

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from cache.redis_cache import (
    CACHE_TTL,
    cache_get_or_set,
    cache_delete,
)
from database.models import (
    Permission,
    RolePermission,
    UserRole,
)

logger = logging.getLogger(__name__)


def get_user_permissions(
    user_id: str,
    db: Session,
) -> set[str]:
    """
    Load user permissions using cache-aside.

    Cache hit: return cached permissions.
    Cache miss: query PostgreSQL and populate Redis.
    Redis unavailable: fall back to PostgreSQL.
    """

    cache_key = f"permissions:{user_id}"

    def fetch_permissions() -> list[str]:
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

        permissions = db.execute(
            statement
        ).scalars().all()

        logger.info(
            "Permissions loaded from database for user %s",
            user_id,
        )

        return sorted(set(permissions))

    try:
        permissions = cache_get_or_set(
            key=cache_key,
            ttl=CACHE_TTL["PERMISSIONS"],
            fetch_fn=fetch_permissions,
        )

    except RedisError:
        logger.exception(
            "Permission cache unavailable for user %s",
            user_id,
        )

        permissions = fetch_permissions()

    return set(permissions)


def invalidate_user_permissions(user_id: str) -> None:
    """
    Invalidate permissions after RBAC changes.
    """
    try:
        cache_delete(f"permissions:{user_id}")

        logger.info(
            "Permission cache invalidated for user %s",
            user_id,
        )

    except RedisError:
        logger.exception(
            "Failed to invalidate permission cache "
            "for user %s",
            user_id,
        )
        raise
