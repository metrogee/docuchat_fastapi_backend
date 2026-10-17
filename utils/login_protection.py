
import hashlib
import os

import redis

from utils.rate_limiter import RATE_LIMIT_SCRIPT


class LoginLockedError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = max(1, int(retry_after))
        super().__init__("Too many login attempts")


class LoginProtection:
    MAX_FAILURES = 5
    WINDOW_SECONDS = 900

    def __init__(self, redis_client=None):
        if redis_client is None:
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_RATE_LIMIT_DB", "2")),
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            
        self.redis = redis_client


    @staticmethod
    def key_for(email: str) -> str:
        normalised = email.strip().lower()

        digest = hashlib.sha256(
            normalised.encode("utf-8")
        ).hexdigest()

        return f"docuchat:login-failures:{digest}"

    def check_allowed(self, email: str) -> None:
        key = self.key_for(email)

        count = int(self.redis.get(key) or 0)

        if count >= self.MAX_FAILURES:
            ttl = self.redis.ttl(key)
            raise LoginLockedError(ttl)

    def record_failure(self, email: str) -> None:
        key = self.key_for(email)

        allowed, ttl, remaining = self.redis.eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            self.WINDOW_SECONDS,
            self.MAX_FAILURES - 1,
        )

        if not allowed:
            raise LoginLockedError(ttl)

    def reset(self, email: str) -> None:
        self.redis.delete(self.key_for(email))
