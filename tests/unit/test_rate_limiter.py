
from unittest.mock import Mock

import pytest

from utils.rate_limiter import (
    RedisRateLimiter,
    RateLimitExceeded,
)


def test_request_allowed():
    mock_redis = Mock()
    mock_redis.eval.return_value = [1, 59, 99]

    limiter = RedisRateLimiter(
        redis_client=mock_redis,
        max_requests=100,
    )

    result = limiter.acquire("openai")

    assert result["allowed"] is True
    assert result["remaining"] == 99
    assert result["reset_after"] == 59

    mock_redis.eval.assert_called_once()


def test_rate_limit_exceeded():
    mock_redis = Mock()
    mock_redis.eval.return_value = [0, 30, 0]

    limiter = RedisRateLimiter(
        redis_client=mock_redis,
        max_requests=100,
    )

    with pytest.raises(RateLimitExceeded) as exc:
        limiter.acquire("openai")

    assert exc.value.retry_after == 30


def test_rate_limit_retry_delay_minimum():
    mock_redis = Mock()
    mock_redis.eval.return_value = [0, 0, 0]

    limiter = RedisRateLimiter(
        redis_client=mock_redis,
    )

    with pytest.raises(RateLimitExceeded) as exc:
        limiter.acquire("openai")

    assert exc.value.retry_after == 1


def test_services_use_separate_keys():
    mock_redis = Mock()
    mock_redis.eval.return_value = [1, 60, 99]

    limiter = RedisRateLimiter(
        redis_client=mock_redis,
    )

    limiter.acquire("openai")
    limiter.acquire("stripe")

    calls = mock_redis.eval.call_args_list

    assert calls[0].args[2] == "docuchat:rate-limit:openai"
    assert calls[1].args[2] == "docuchat:rate-limit:stripe"


def test_invalid_configuration():
    with pytest.raises(ValueError):
        RedisRateLimiter(max_requests=0)

    with pytest.raises(ValueError):
        RedisRateLimiter(window_seconds=0)
