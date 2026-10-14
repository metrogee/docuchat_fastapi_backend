import json

from database.models import UsageLog
from src.events import (
    event_emitter,
    EVENT_DOCUMENT_CREATED,
    EVENT_DOCUMENT_DELETED,
)


def log_document_created(
    db,
    user_id,
    document_id,
    title,
    file_size_bytes,
):
    log = UsageLog(
        user_id=user_id,
        action="document_created",
        tokens=0,
        cost_usd=0,
        details=json.dumps({
            "documentId": document_id,
            "title": title,
            "fileSizeBytes": file_size_bytes,
        }),
    )

    db.add(log)
    db.commit()


def log_document_deleted(
    db,
    deleted_by,
    document_id,
    title,
    deleted_at,
):
    log = UsageLog(
        user_id=deleted_by,
        action="document_deleted",
        tokens=0,
        cost_usd=0,
        details=json.dumps({
            "documentId": document_id,
            "title": title,
            "deletedAt": deleted_at.isoformat(),
        }),
    )

    db.add(log)
    db.commit()


event_emitter.on(
    EVENT_DOCUMENT_CREATED,
    log_document_created,
)

event_emitter.on(
    EVENT_DOCUMENT_DELETED,
    log_document_deleted,
)