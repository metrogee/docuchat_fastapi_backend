
import json
from unittest.mock import patch

import pytest

from queues.failure_handling import (
    DEAD_LETTER_QUEUE,
    get_retry_delay,
    send_to_dead_letter_queue,
)


def test_first_retry_delay():
    assert get_retry_delay(1) == 2


def test_second_retry_delay():
    assert get_retry_delay(2) == 4


def test_invalid_retry_number():
    with pytest.raises(ValueError):
        get_retry_delay(0)


def test_permanent_failure_is_sent_to_dlq():
    with patch(
        "queues.failure_handling.Redis.from_url"
    ) as mock_from_url:

        mock_redis = mock_from_url.return_value

        payload = send_to_dead_letter_queue(
            document_id="document-123",
            user_id="user-456",
            error="Processing failed",
            attempts=3,
        )

        assert payload["documentId"] == "document-123"
        assert payload["userId"] == "user-456"
        assert payload["attempts"] == 3
        assert payload["error"] == "Processing failed"
        assert "failedAt" in payload

        mock_redis.rpush.assert_called_once()

        args = mock_redis.rpush.call_args.args

        assert args[0] == DEAD_LETTER_QUEUE
        assert json.loads(args[1]) == payload

        mock_redis.close.assert_called_once()
