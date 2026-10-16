import pytest

from utils.chunker import (
    split_into_chunks,
    estimate_tokens,
)


def test_splits_text_into_chunks():
    text = " ".join(["word"] * 1200)

    chunks = split_into_chunks(text)

    assert len(chunks) == 3
    assert [len(chunk.split()) for chunk in chunks] == [
        500, 500, 200
    ]


def test_preserves_word_order():
    chunks = split_into_chunks(
        "one two three four five",
        max_words_per_chunk=2,
    )

    assert chunks == [
        "one two",
        "three four",
        "five",
    ]


def test_empty_text():
    assert split_into_chunks("") == []
    assert split_into_chunks("   ") == []


def test_estimates_tokens():
    assert estimate_tokens("one two three") == 4


def test_invalid_chunk_size():
    with pytest.raises(ValueError):
        split_into_chunks("Hello", max_words_per_chunk=0)