
from unittest.mock import Mock

import pytest

from cache import redis_cache


def test_cache_key():
    assert (
        redis_cache.cache_key("permissions:user123")
        == "docuchat:permissions:user123"
    )


def test_hash_key_is_deterministic():
    first = redis_cache.hash_key("hello", "world")
    second = redis_cache.hash_key("hello", "world")

    assert first == second
    assert len(first) == 16


def test_hash_key_changes_with_input():
    first = redis_cache.hash_key("hello")
    second = redis_cache.hash_key("goodbye")

    assert first != second


def test_cache_set(monkeypatch):
    mock_redis = Mock()
    mock_redis.set.return_value = True

    monkeypatch.setattr(
        redis_cache,
        "cache_redis",
        mock_redis,
    )

    result = redis_cache.cache_set(
        "doc:test123",
        {"title": "My Document"},
        ttl=600,
    )

    assert result is True

    mock_redis.set.assert_called_once_with(
        "docuchat:doc:test123",
        '{"title": "My Document"}',
        ex=600,
    )


def test_cache_get(monkeypatch):
    mock_redis = Mock()

    mock_redis.get.return_value = (
        '{"title": "Cached Document"}'
    )

    monkeypatch.setattr(
        redis_cache,
        "cache_redis",
        mock_redis,
    )

    result = redis_cache.cache_get("doc:test123")

    assert result == {
        "title": "Cached Document"
    }


def test_cache_miss(monkeypatch):
    mock_redis = Mock()
    mock_redis.get.return_value = None

    monkeypatch.setattr(
        redis_cache,
        "cache_redis",
        mock_redis,
    )

    assert redis_cache.cache_get("missing") is None


def test_invalid_cache_json(monkeypatch):
    mock_redis = Mock()
    mock_redis.get.return_value = "invalid-json"

    monkeypatch.setattr(
        redis_cache,
        "cache_redis",
        mock_redis,
    )

    assert redis_cache.cache_get("bad") is None


def test_cache_delete(monkeypatch):
    mock_redis = Mock()
    mock_redis.delete.return_value = 1

    monkeypatch.setattr(
        redis_cache,
        "cache_redis",
        mock_redis,
    )

    assert redis_cache.cache_delete("doc:123") == 1

    mock_redis.delete.assert_called_once_with(
        "docuchat:doc:123"
    )


def test_cache_delete_pattern_uses_scan(monkeypatch):
    mock_redis = Mock()

    mock_redis.scan_iter.return_value = iter([
        "docuchat:doc:1",
        "docuchat:doc:2",
    ])

    mock_redis.delete.return_value = 2

    monkeypatch.setattr(
        redis_cache,
        "cache_redis",
        mock_redis,
    )

    deleted = redis_cache.cache_delete_pattern(
        "doc:*"
    )

    assert deleted == 2

    mock_redis.scan_iter.assert_called_once_with(
        match="docuchat:doc:*",
        count=100,
    )


def test_invalid_ttl():
    with pytest.raises(ValueError):
        redis_cache.cache_set(
            "test",
            {"value": 1},
            ttl=0,
        )


def test_cache_aside_hit(monkeypatch):
    monkeypatch.setattr(
        redis_cache,
        "cache_get",
        lambda key: {"cached": True},
    )

    fetch = Mock()

    result = redis_cache.cache_get_or_set(
        "test",
        60,
        fetch,
    )

    assert result == {"cached": True}
    fetch.assert_not_called()


def test_cache_aside_miss(monkeypatch):
    mock_redis = Mock()
    mock_redis.set.return_value = True
    mock_redis.eval.return_value = 1

    monkeypatch.setattr(
        redis_cache,
        "cache_redis",
        mock_redis,
    )

    monkeypatch.setattr(
        redis_cache,
        "cache_get",
        lambda key: None,
    )

    stored = Mock()

    monkeypatch.setattr(
        redis_cache,
        "cache_set",
        stored,
    )

    fetch = Mock(return_value={"fresh": True})

    result = redis_cache.cache_get_or_set(
        "test",
        60,
        fetch,
    )

    assert result == {"fresh": True}
    fetch.assert_called_once()
    stored.assert_called_once_with(
        "test",
        {"fresh": True},
        60,
    )

    mock_redis.eval.assert_called_once()
