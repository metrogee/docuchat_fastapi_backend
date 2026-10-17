
import re


DANGEROUS_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above)",
    r"you are now",
    r"pretend (you are|to be)",
    r"system prompt:",
    r"new instructions:",
]


def detect_prompt_injection(input_text: str) -> dict:
    sanitized = input_text
    is_suspicious = False

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sanitized, re.IGNORECASE):
            is_suspicious = True

            sanitized = re.sub(
                pattern,
                "[FILTERED]",
                sanitized,
                flags=re.IGNORECASE,
            )

    return {
        "is_suspicious": is_suspicious,
        "sanitized": sanitized,
    }
