
import hashlib
import json
import logging
import os
import time
import uuid

from typing import Any, Callable, TypeVar

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

T = TypeVar("T")

CACHE_TTL = {
    "PERMISSIONS": 300,
    "DOCUMENT": 600,
    "CONVERSATION_LIST": 120,
    "EMBEDDING": 604800,
    "RAG_RESULT": 3600,
}

CACHE_PREFIX = "docuchat:"

# Separate Redis client and logical database for caching.
cache_redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_CACHE_DB", "1")),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    health_check_interval=30,
)

RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


def cache_key(key: str) -> str:
    return f"{CACHE_PREFIX}{key}"


def cache_get(key: str) -> Any | None:
    raw = cache_redis.get(cache_key(key))

    if raw is None:
        return None

    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid cache JSON for key: %s", key)
        return None


def cache_set(key: str, value: Any, ttl: int) -> bool:
    if ttl <= 0:
        raise ValueError("Cache TTL must be positive")

    serialized = json.dumps(value)

    return bool(
        cache_redis.set(
            cache_key(key),
            serialized,
            ex=ttl,
        )
    )


def cache_delete(key: str) -> int:
    return cache_redis.delete(cache_key(key))


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete matching keys using SCAN rather than KEYS.
    """
    full_pattern = cache_key(pattern)
    deleted = 0
    batch = []

    for key in cache_redis.scan_iter(
        match=full_pattern,
        count=100,
    ):
        batch.append(key)

        if len(batch) >= 100:
            deleted += cache_redis.delete(*batch)
            batch.clear()

    if batch:
        deleted += cache_redis.delete(*batch)

    return deleted


def hash_key(*parts: str) -> str:
    serialized = json.dumps(
        parts,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:16]


def cache_get_or_set(
    key: str,
    ttl: int,
    fetch_fn: Callable[[], T],
    lock_timeout: int = 5,
    wait_timeout: float = 1.0,
) -> T:
    """
    Cache-aside with short-lived distributed locking.

    The lock is token-owned to prevent one request
    from accidentally releasing another request's lock.
    """
    cached = cache_get(key)

    if cached is not None:
        return cached

    lock_key = cache_key(f"lock:{key}")
    token = uuid.uuid4().hex

    acquired = cache_redis.set(
        lock_key,
        token,
        nx=True,
        ex=lock_timeout,
    )

    if acquired:
        try:
            # Double-check after acquiring the lock.
            cached = cache_get(key)

            if cached is not None:
                return cached

            value = fetch_fn()
            cache_set(key, value, ttl)
            return value

        finally:
            cache_redis.eval(
                RELEASE_LOCK_SCRIPT,
                1,
                lock_key,
                token,
            )

    # Another worker owns the lock.
    deadline = time.monotonic() + wait_timeout

    while time.monotonic() < deadline:
        time.sleep(0.05)

        cached = cache_get(key)

        if cached is not None:
            return cached

    # Fallback if the cache still has no result.
    return fetch_fn()
