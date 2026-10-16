
import json
import logging
from datetime import datetime, timezone

from redis import Redis

from queues.celery_app import REDIS_URL


logger = logging.getLogger(__name__)

DEAD_LETTER_QUEUE = "document-processing:dead-letter"


def get_retry_delay(retry_number: int) -> int:
    """
    Return exponential retry delay.

    Retry 1 -> 2 seconds
    Retry 2 -> 4 seconds
    """
    if retry_number < 1:
        raise ValueError("Retry number must be at least 1")

    return 2 ** retry_number


def send_to_dead_letter_queue(
    document_id: str,
    user_id: str,
    error: str,
    attempts: int,
) -> dict:
    """
    Record a permanently failed document-processing job.
    """
    payload = {
        "documentId": document_id,
        "userId": user_id,
        "error": error,
        "attempts": attempts,
        "failedAt": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    try:
        redis_client.rpush(
            DEAD_LETTER_QUEUE,
            json.dumps(payload),
        )
    finally:
        redis_client.close()

    logger.error(
        "Document %s moved to dead-letter queue after %s attempts",
        document_id,
        attempts,
    )

    return payload
