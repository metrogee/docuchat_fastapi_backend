
import os

import redis
from dotenv import load_dotenv

load_dotenv()


RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])

if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local ttl = redis.call('TTL', KEYS[1])
local limit = tonumber(ARGV[2])
local remaining = math.max(0, limit - count)

if count > limit then
    return {0, ttl, remaining}
end

return {1, ttl, remaining}
"""


class RateLimitExceeded(Exception):
    def __init__(self, retry_after):
        self.retry_after = max(1, int(retry_after))
        super().__init__(
            f"Rate limit exceeded. Retry in "
            f"{self.retry_after} seconds."
        )


class RedisRateLimiter:

    def __init__(
        self,
        redis_client=None,
        max_requests=100,
        window_seconds=60,
    ):
        if max_requests < 1 or window_seconds < 1:
            raise ValueError(
                "Rate limit and window must be positive"
            )

        self.max_requests = max_requests
        self.window_seconds = window_seconds

        if redis_client is None:
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))

            redis_client = redis.Redis(
                host=host,
                port=port,
                db=0,
                socket_connect_timeout=3,
                socket_timeout=3,
            )

        self.redis = redis_client
        

    def acquire(self, service="openai"):
        key = f"docuchat:rate-limit:{service}"

        allowed, ttl, remaining = self.redis.eval(
            RATE_LIMIT_SCRIPT,
            1,
            key,
            self.window_seconds,
            self.max_requests,
        )

        if not allowed:
            raise RateLimitExceeded(ttl)

        return {
            "allowed": True,
            "remaining": remaining,
            "reset_after": max(0, ttl),
        }
