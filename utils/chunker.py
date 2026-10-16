import math


def split_into_chunks(
    text: str,
    max_words_per_chunk: int = 500,
) -> list[str]:
    if max_words_per_chunk < 1:
        raise ValueError("max_words_per_chunk must be positive")

    words = text.split()

    if not words:
        return []

    chunks = []

    for index in range(0, len(words), max_words_per_chunk):
        chunk = " ".join(
            words[index:index + max_words_per_chunk]
        )
        chunks.append(chunk)

    return chunks


def estimate_tokens(text: str) -> int:
    word_count = len(text.split())

    return math.ceil(word_count * 1.33)