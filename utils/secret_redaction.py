
import re


SENSITIVE_FIELDS = {
    "password",
    "secret",
    "client_secret",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "database_url",
    "private_key",
}

PATTERNS = [
    (
        re.compile(
            r"Bearer\s+[A-Za-z0-9._~+/-]+=*",
            re.IGNORECASE,
        ),
        "Bearer [REDACTED]",
    ),
    (
        re.compile(
            r"\bsk-[A-Za-z0-9_-]{16,}\b"
        ),
        "[REDACTED]",
    ),
    (
        re.compile(
            r"(?i)\b(password|api_key|secret)"
            r"\s*[:=]\s*"
            r"(['\"]?)([^\s,'\"}]+)\2"
        ),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(
            r"(?i)\b(postgresql(?:\+\w+)?|redis)"
            r"://[^\s'\"<>]+"
        ),
        "[REDACTED_CONNECTION_URL]",
    ),
]


def redact_text(value: str) -> str:
    result = value

    for pattern, replacement in PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def redact_sensitive_data(value):
    """
    Redact sensitive information recursively.
    """
    if isinstance(value, str):
        return redact_text(value)

    if isinstance(value, list):
        return [
            redact_sensitive_data(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return tuple(
            redact_sensitive_data(item)
            for item in value
        )

    if isinstance(value, dict):
        cleaned = {}

        for key, item in value.items():
            key_name = str(key).lower()

            if key_name in SENSITIVE_FIELDS:
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = redact_sensitive_data(item)

        return cleaned

    return value
