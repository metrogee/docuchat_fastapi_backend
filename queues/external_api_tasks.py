
import logging

from celery.exceptions import MaxRetriesExceededError

from http_clients.circuit_breaker import call_openai
from queues.celery_app import celery_app
from utils.rate_limiter import (
    RedisRateLimiter,
    RateLimitExceeded,
)

logger = logging.getLogger(__name__)

limiter = RedisRateLimiter(
    max_requests=100,
    window_seconds=60,
)


@celery_app.task(
    bind=True,
    name="queues.external_api_tasks.generate_embedding",
    max_retries=None,
)
def generate_embedding(self, text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Embedding input cannot be empty")

    try:
        allowance = limiter.acquire("openai")

    except RateLimitExceeded as exc:
        logger.warning(
            "OpenAI rate limit reached. Retry in %ss",
            exc.retry_after,
        )

        raise self.retry(
            exc=exc,
            countdown=exc.retry_after,
        )

    logger.info(
        "OpenAI request allowance acquired. Remaining: %s",
        allowance["remaining"],
    )

    return call_openai(
        "/embeddings",
        {
            "input": text,
            "model": "text-embedding-3-small",
        },
    )
