
import logging

import pybreaker

from http_clients.openai_client import OpenAIClient
from http_clients.retry import with_retry, is_retryable

logger = logging.getLogger(__name__)


class CircuitBreakerLogger(pybreaker.CircuitBreakerListener):

    def state_change(self, cb, old_state, new_state):
        logger.warning(
            "Circuit breaker %s changed from %s to %s",
            cb.name,
            old_state.name,
            new_state.name,
        )

    def failure(self, cb, exc):
        logger.error(
            "Circuit breaker %s recorded failure: %s",
            cb.name,
            type(exc).__name__,
        )

    def success(self, cb):
        logger.info(
            "Circuit breaker %s recorded success",
            cb.name,
        )


def create_openai_breaker():
    return pybreaker.CircuitBreaker(
        fail_max=3,
        reset_timeout=30,
        exclude=[
            lambda exc: (
                isinstance(exc, Exception)
                and not is_retryable(exc)
            )
        ],
        listeners=[CircuitBreakerLogger()],
        name="openai",
    )


openai_breaker = create_openai_breaker()


def call_openai(
    endpoint,
    data,
    client=None,
    breaker=None,
    max_attempts=3,
):
    breaker = breaker if breaker is not None else openai_breaker
    owned_client = client is None

    if owned_client:
        client = OpenAIClient()

    try:
        return breaker.call(
            lambda: with_retry(
                lambda: client.post(endpoint, data),
                max_attempts=max_attempts,
            )
        )

    except pybreaker.CircuitBreakerError as exc:
        logger.error("OpenAI circuit breaker is OPEN")
        raise RuntimeError(
            "OpenAI is temporarily unavailable. "
            "Please try again shortly."
        ) from exc

    finally:
        if owned_client:
            client.close()
