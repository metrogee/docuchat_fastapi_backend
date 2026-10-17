
import pytest
import pybreaker

from http_clients.openai_client import ExternalAPIError
from http_clients.retry import (
    is_retryable,
    with_retry,
    get_retry_delay,
)
from http_clients.circuit_breaker import (
    create_openai_breaker,
)


def test_retryable_status_codes():
    for status in (408, 429, 500, 502, 503, 504):
        assert is_retryable(
            ExternalAPIError("Temporary failure", status)
        )


def test_permanent_errors_are_not_retryable():
    for status in (400, 401, 403, 404, 422):
        assert not is_retryable(
            ExternalAPIError("Permanent failure", status)
        )


def test_network_errors_are_retryable():
    assert is_retryable(
        ExternalAPIError("Network unavailable")
    )


def test_retry_on_503_then_success():
    attempts = []

    def operation():
        attempts.append(1)

        if len(attempts) < 3:
            raise ExternalAPIError(
                "Service unavailable",
                status_code=503,
            )

        return {"success": True}

    result = with_retry(
        operation,
        max_attempts=3,
        base_delay=0,
        sleep=lambda seconds: None,
    )

    assert result == {"success": True}
    assert len(attempts) == 3


def test_no_retry_on_400():
    attempts = []

    def operation():
        attempts.append(1)
        raise ExternalAPIError(
            "Bad request",
            status_code=400,
        )

    with pytest.raises(ExternalAPIError):
        with_retry(
            operation,
            max_attempts=3,
            sleep=lambda seconds: None,
        )

    assert len(attempts) == 1


def test_retry_after_header():
    assert get_retry_delay("5", 1) == 5.0


def test_retry_after_is_honored():
    delays = []
    attempts = []

    def operation():
        attempts.append(1)

        if len(attempts) == 1:
            raise ExternalAPIError(
                "Rate limited",
                status_code=429,
                retry_after="3",
            )

        return "success"

    result = with_retry(
        operation,
        max_attempts=2,
        sleep=delays.append,
    )

    assert result == "success"
    assert delays == [3.0]


def test_retry_exhaustion():
    attempts = []

    def operation():
        attempts.append(1)
        raise ExternalAPIError(
            "Service unavailable",
            status_code=503,
        )

    with pytest.raises(ExternalAPIError):
        with_retry(
            operation,
            max_attempts=3,
            base_delay=0,
            sleep=lambda seconds: None,
        )

    assert len(attempts) == 3


def test_circuit_breaker_opens():
    breaker = create_openai_breaker()

    def failing_operation():
        raise ExternalAPIError(
            "Server error",
            status_code=503,
        )

    for _ in range(2):
        with pytest.raises(ExternalAPIError):
            breaker.call(failing_operation)

    with pytest.raises(pybreaker.CircuitBreakerError):
        breaker.call(failing_operation)

    assert breaker.current_state == "open"


def test_circuit_breaker_ignores_permanent_errors():
    breaker = create_openai_breaker()

    def bad_request():
        raise ExternalAPIError(
            "Bad request",
            status_code=400,
        )

    for _ in range(3):
        with pytest.raises(ExternalAPIError):
            breaker.call(bad_request)

    assert breaker.current_state == "closed"
