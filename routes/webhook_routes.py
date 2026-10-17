
import json
import logging
import os

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import WebhookEvent
from queues.webhook_tasks import process_webhook
from utils.webhook_security import (
    verify_webhook_signature,
    WebhookSignatureError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)

MAX_WEBHOOK_BYTES = 1024 * 1024


@router.post("/example")
async def receive_example_webhook(
    request: Request,
    x_webhook_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    if len(raw_body) > MAX_WEBHOOK_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Webhook payload too large",
        )

    try:
        verify_webhook_signature(
            payload=raw_body,
            signature=x_webhook_signature,
            secret=os.getenv("WEBHOOK_SECRET"),
        )

    except WebhookSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    except RuntimeError:
        logger.error("Webhook secret is not configured")
        raise HTTPException(
            status_code=503,
            detail="Webhook receiver unavailable",
        )

    try:
        payload = json.loads(raw_body)

    except (ValueError, UnicodeDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Webhook payload must be an object",
        )

    event_id = payload.get("id")
    event_type = payload.get("type")

    if (
        not isinstance(event_id, str)
        or not 1 <= len(event_id) <= 200
        or not isinstance(event_type, str)
        or not 1 <= len(event_type) <= 100
    ):
        raise HTTPException(
            status_code=400,
            detail="Valid event id and type are required",
        )

    provider_event_id = f"example:{event_id}"

    statement = (
        insert(WebhookEvent)
        .values(
            id=provider_event_id,
            provider="example",
            event_type=event_type,
            payload=raw_body.decode("utf-8"),
            status="pending",
        )
        .on_conflict_do_nothing(
            index_elements=["id"]
        )
    )

    try:
        result = db.execute(statement)
        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Failed to persist webhook")
        raise HTTPException(
            status_code=503,
            detail="Webhook storage unavailable",
        )

    if result.rowcount == 0:
        existing = db.get(WebhookEvent, provider_event_id)

        if existing is None:
            raise HTTPException(
                status_code=503,
                detail="Webhook state unavailable",
            )

        # Protect against event ID reuse with different content.
        if existing.payload != raw_body.decode("utf-8"):
            raise HTTPException(
                status_code=409,
                detail="Webhook event ID conflict",
            )

        if existing.status == "processed":
            return {
                "received": True,
                "duplicate": True,
                "status": "processed",
            }

        if existing.status == "processing":
            return {
                "received": True,
                "duplicate": True,
                "status": "processing",
            }

    try:
        process_webhook.delay(provider_event_id)

    except Exception:
        logger.exception("Failed to enqueue webhook")
        raise HTTPException(
            status_code=503,
            detail="Webhook queue unavailable",
        )

    return {
        "received": True,
        "duplicate": result.rowcount == 0,
        "status": "queued",
    }
