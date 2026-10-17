
import logging

from sqlalchemy import event
from sqlalchemy.orm import Session

from database.models import UserRole
from rbac.service import invalidate_user_permissions

logger = logging.getLogger(__name__)

PENDING_KEY = "_rbac_cache_invalidation_users"


@event.listens_for(Session, "after_flush")
def collect_role_changes(session, flush_context):
    affected_users = session.info.setdefault(
        PENDING_KEY,
        set(),
    )

    for obj in session.new.union(session.deleted):
        if isinstance(obj, UserRole):
            affected_users.add(obj.user_id)

    for obj in session.dirty:
        if isinstance(obj, UserRole):
            affected_users.add(obj.user_id)


@event.listens_for(Session, "after_commit")
def invalidate_committed_roles(session):
    affected_users = session.info.pop(
        PENDING_KEY,
        set(),
    )

    for user_id in affected_users:
        invalidate_user_permissions(user_id)

        logger.info(
            "RBAC cache invalidated after commit: %s",
            user_id,
        )


@event.listens_for(Session, "after_rollback")
def discard_rolled_back_changes(session):
    session.info.pop(PENDING_KEY, None)
