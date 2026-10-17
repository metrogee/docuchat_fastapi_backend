
from unittest.mock import Mock

import pytest
from redis.exceptions import RedisError

from rbac import service as rbac_service


def test_permission_cache_hit(monkeypatch):
    db = Mock()

    def fake_cache(key, ttl, fetch_fn):
        return ["documents:read", "documents:create"]

    monkeypatch.setattr(
        rbac_service,
        "cache_get_or_set",
        fake_cache,
    )

    result = rbac_service.get_user_permissions(
        "user-123",
        db,
    )

    assert result == {
        "documents:read",
        "documents:create",
    }

    db.execute.assert_not_called()


def test_permission_cache_miss(monkeypatch):
    db = Mock()

    db.execute.return_value.scalars.return_value.all.return_value = [
        "documents:read",
        "documents:create",
        "documents:read",
    ]

    def fake_cache(key, ttl, fetch_fn):
        assert key == "permissions:user-123"
        assert ttl == 300
        return fetch_fn()

    monkeypatch.setattr(
        rbac_service,
        "cache_get_or_set",
        fake_cache,
    )

    result = rbac_service.get_user_permissions(
        "user-123",
        db,
    )

    assert result == {
        "documents:read",
        "documents:create",
    }

    db.execute.assert_called_once()


def test_permission_cache_redis_failure(monkeypatch):
    db = Mock()

    db.execute.return_value.scalars.return_value.all.return_value = [
        "documents:read",
    ]

    def failing_cache(key, ttl, fetch_fn):
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(
        rbac_service,
        "cache_get_or_set",
        failing_cache,
    )

    result = rbac_service.get_user_permissions(
        "user-123",
        db,
    )

    assert result == {"documents:read"}
    db.execute.assert_called_once()


def test_permission_invalidation(monkeypatch):
    deleted = []

    monkeypatch.setattr(
        rbac_service,
        "cache_delete",
        deleted.append,
    )

    rbac_service.invalidate_user_permissions(
        "user-123"
    )

    assert deleted == [
        "permissions:user-123"
    ]


def test_permission_invalidation_failure(monkeypatch):
    def failing_delete(key):
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(
        rbac_service,
        "cache_delete",
        failing_delete,
    )

    with pytest.raises(RedisError):
        rbac_service.invalidate_user_permissions(
            "user-123"
        )
