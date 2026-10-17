
import json
import logging

from datetime import datetime, timezone

from sqlalchemy import update

from database.database import SessionLocal
from database.models import WebhookEvent
from queues.celery_app import celery_app
from datetime import timedelta
from sqlalchemy import select, or_


logger = logging.getLogger(__name__)


def process_webhook_event(event_type, payload):
    """
    Route verified events to their business handlers.
    No external side effects are enabled yet.
    """
    if event_type == "document.imported":
        logger.info(
            "Received document.imported event: %s",
            payload.get("id"),
        )
        # Future integration: validate document ownership
        # and trigger the existing document-processing task.

    else:
        logger.info(
            "No handler configured for event type: %s",
            event_type,
        )


@celery_app.task(
    bind=True,
    name="queues.webhook_tasks.process_webhook",
    max_retries=3,
)
def process_webhook(self, event_id):
    db = SessionLocal()

    try:
        # Claim the event atomically.
        result = db.execute(
            update(WebhookEvent)
            .where(
                WebhookEvent.id == event_id,
                WebhookEvent.status == "pending",
            )
            .values(
                status="processing",
                processing_started_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

        if result.rowcount == 0:
            logger.info(
                "Webhook already claimed or completed: %s",
                event_id,
            )
            return {"status": "skipped"}

        event = db.get(WebhookEvent, event_id)

        if event is None:
            return {"status": "not_found"}

        payload = json.loads(event.payload)

        process_webhook_event(
            event.event_type,
            payload,
        )

        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.processing_started_at = None

        db.commit()

        logger.info("Webhook processed: %s", event_id)

        return {"status": "processed", "event_id": event_id}

    except Exception as exc:
        db.rollback()

        event = db.get(WebhookEvent, event_id)

        if event is not None and event.status == "processing":
            event.status = "pending"
            event.processing_started_at = None
            db.commit()

        logger.exception("Webhook processing failed: %s", event_id)

        raise self.retry(
            exc=exc,
            countdown=min(2 ** self.request.retries, 30),
        )

    finally:
        db.close()


@celery_app.task(
    name="queues.webhook_tasks.recover_webhooks",
)
def recover_webhooks():
    """
    Requeue pending events and recover processing
    attempts abandoned for more than 5 minutes.
    """
    db = SessionLocal()
    recovered = 0
    queued = 0

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=5
        )

        # Return stale processing events to pending.
        stale_events = db.execute(
            update(WebhookEvent)
            .where(
                WebhookEvent.status == "processing",
                or_(
                    WebhookEvent.processing_started_at < cutoff,
                    WebhookEvent.processing_started_at.is_(None),
                ),
            )
            .values(
                status="pending",
                processing_started_at=None,
            )
            .returning(WebhookEvent.id)
        ).scalars().all()

        recovered = len(stale_events)
        db.commit()

        # Requeue outstanding events.
        pending_ids = db.execute(
            select(WebhookEvent.id)
            .where(WebhookEvent.status == "pending")
            .order_by(WebhookEvent.received_at)
            .limit(100)
        ).scalars().all()

        for event_id in pending_ids:
            try:
                process_webhook.delay(event_id)
                queued += 1
            except Exception:
                logger.exception(
                    "Recovery could not enqueue webhook: %s",
                    event_id,
                )

        logger.info(
            "Webhook recovery completed: "
            "%s stale reset, %s queued",
            recovered,
            queued,
        )

        return {
            "recovered": recovered,
            "queued": queued,
        }

    finally:
        db.close()

