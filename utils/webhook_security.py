
import hashlib
import hmac
import os


class WebhookSignatureError(Exception):
    pass


def generate_signature(payload: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(
    payload: bytes,
    signature: str | None,
    secret: str | None = None,
) -> bool:
    if secret is None:
        secret = os.getenv("WEBHOOK_SECRET")

    if not secret:
        raise RuntimeError("WEBHOOK_SECRET is not configured")

    if not signature:
        raise WebhookSignatureError(
            "Missing webhook signature"
        )

    # Only accept a plain SHA-256 hexadecimal digest.
    if len(signature) != 64:
        raise WebhookSignatureError(
            "Invalid webhook signature"
        )

    try:
        bytes.fromhex(signature)
    except ValueError as exc:
        raise WebhookSignatureError(
            "Invalid webhook signature"
        ) from exc

    expected = generate_signature(payload, secret)

    if not hmac.compare_digest(
        expected,
        signature.lower(),
    ):
        raise WebhookSignatureError(
            "Invalid webhook signature"
        )

    return True
