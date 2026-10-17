
import re

import bleach


SCRIPT_BLOCK_PATTERN = re.compile(
    r"<\s*(script|style)\b[^>]*>.*?"
    r"<\s*/\s*\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)


def sanitize_text(value: str) -> str:
    """
    Remove HTML tags and script/style blocks
    from plain-text fields.
    """
    without_scripts = SCRIPT_BLOCK_PATTERN.sub(
        "",
        value,
    )

    return bleach.clean(
        without_scripts,
        tags=[],
        attributes={},
        strip=True,
    )


def sanitize_value(value):
    """
    Recursively sanitize text in lists and dictionaries.

    Apply only to fields that are intended to contain
    plain text, not arbitrary credentials or documents.
    """
    if isinstance(value, str):
        return sanitize_text(value)

    if isinstance(value, list):
        return [
            sanitize_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: sanitize_value(item)
            for key, item in value.items()
        }

    return value
