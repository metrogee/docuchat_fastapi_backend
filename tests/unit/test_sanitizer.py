
from utils.sanitizer import (
    sanitize_text,
    sanitize_value,
)


def test_removes_script_from_document_title():
    value = "<script>alert('xss')</script>My Doc"

    assert sanitize_text(value) == "My Doc"


def test_removes_html_tags():
    value = "<b>Important</b> Document"

    assert sanitize_text(value) == (
        "Important Document"
    )


def test_removes_style_blocks():
    value = "<style>body{color:red}</style>Report"

    assert sanitize_text(value) == "Report"


def test_sanitizes_nested_dictionary():
    data = {
        "title": "<script>alert(1)</script>My Doc",
        "tags": [
            "<b>finance</b>",
            "<i>reports</i>",
        ],
    }

    result = sanitize_value(data)

    assert result == {
        "title": "My Doc",
        "tags": [
            "finance",
            "reports",
        ],
    }


def test_plain_text_remains_unchanged():
    value = "My Financial Report 2026"

    assert sanitize_text(value) == value
