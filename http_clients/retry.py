
import logging
import random
import time

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from http_clients.openai_client import ExternalAPIError

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def is_retryable(error):
    if not isinstance(error, ExternalAPIError):
        return False

    if error.status_code is None:
        return True

    return error.status_code in RETRYABLE_STATUS_CODES


def get_retry_delay(retry_after, default_delay):
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except (ValueError, TypeError):
            try:
                retry_date = parsedate_to_datetime(retry_after)

                if retry_date.tzinfo is None:
                    retry_date = retry_date.replace(tzinfo=timezone.utc)

                seconds = (
                    retry_date - datetime.now(timezone.utc)
                ).total_seconds()

                return max(0.0, seconds)

            except (TypeError, ValueError, OverflowError):
                pass

    return default_delay


def with_retry(
    operation,
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    sleep=time.sleep,
):
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if base_delay < 0 or max_delay < 0:
        raise ValueError("Delays cannot be negative")

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except ExternalAPIError as exc:
            if not is_retryable(exc):
                logger.error(
                    "Permanent API error. No retry: %s",
                    exc.status_code,
                )
                raise

            if attempt == max_attempts:
                logger.error(
                    "API request failed after %s attempts",
                    max_attempts,
                )
                raise

            backoff = min(
                base_delay * (2 ** (attempt - 1)),
                max_delay,
            )

            jitter = random.uniform(0, backoff * 0.1)

            delay = get_retry_delay(
                exc.retry_after,
                backoff + jitter,
            )

            logger.warning(
                "API attempt %s/%s failed. "
                "Retrying in %.2f seconds",
                attempt,
                max_attempts,
                delay,
            )

            sleep(delay)
