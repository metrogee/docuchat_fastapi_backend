
import pytest

from utils.webhook_security import (
    generate_signature,
    verify_webhook_signature,
    WebhookSignatureError,
)


SECRET = "test-webhook-secret"

PAYLOAD = b'{"id":"evt_123","type":"document.imported"}'


def test_valid_signature():
    signature = generate_signature(PAYLOAD, SECRET)

    assert verify_webhook_signature(
        PAYLOAD,
        signature,
        SECRET,
    ) is True


def test_invalid_signature():
    signature = "a" * 64

    with pytest.raises(WebhookSignatureError):
        verify_webhook_signature(
            PAYLOAD,
            signature,
            SECRET,
        )


def test_missing_signature():
    with pytest.raises(
        WebhookSignatureError,
        match="Missing",
    ):
        verify_webhook_signature(
            PAYLOAD,
            None,
            SECRET,
        )


def test_modified_payload():
    signature = generate_signature(PAYLOAD, SECRET)

    modified = (
        b'{"id":"evt_123","type":"payment.succeeded"}'
    )

    with pytest.raises(WebhookSignatureError):
        verify_webhook_signature(
            modified,
            signature,
            SECRET,
        )


def test_missing_secret():
    with pytest.raises(RuntimeError):
        verify_webhook_signature(
            PAYLOAD,
            "a" * 64,
            "",
        )


def test_malformed_signature():
    with pytest.raises(WebhookSignatureError):
        verify_webhook_signature(
            PAYLOAD,
            "not-a-hex-signature",
            SECRET,
        )
