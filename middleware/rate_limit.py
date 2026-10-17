
import hashlib
import logging
import os

import redis
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from utils.rate_limiter import (
    RATE_LIMIT_SCRIPT,
)

logger = logging.getLogger(__name__)


class APIRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_client=None):
        super().__init__(app)

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
    def get_limit(path: str):
        if path == "/api/v1/auth/login":
            return 10, 60

        if path == "/api/v1/auth/register":
            return 5, 60

        if path == "/api/v1/auth/refresh":
            return 20, 60

        if path.startswith("/api/v1/"):
            return 100, 60

        return None

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        rule = self.get_limit(request.url.path)

        if rule is None:
            return await call_next(request)

        limit, window = rule

        # Use the direct peer address.
        # Do not trust client-controlled X-Forwarded-For headers.
        client_ip = (
            request.client.host
            if request.client is not None
            else "unknown"
        )

        identifier = hashlib.sha256(
            client_ip.encode("utf-8")
        ).hexdigest()

        bucket = (
            f"docuchat:http-rate-limit:"
            f"{request.url.path}:{identifier}"
        )

        try:
            allowed, ttl, remaining = self.redis.eval(
                RATE_LIMIT_SCRIPT,
                1,
                bucket,
                window,
                limit,
            )

        except redis.RedisError:
            logger.exception(
                "Redis unavailable during HTTP rate limiting"
            )

            # Keep ordinary API requests available if Redis fails.
            # Authentication-sensitive routes fail closed.
            if request.url.path.startswith("/api/v1/auth/"):
                return JSONResponse(
                    status_code=503,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_UNAVAILABLE",
                            "message": "Service temporarily unavailable",
                        },
                    },
                    headers={"Cache-Control": "no-store"},
                )

            return await call_next(request)

        ttl = max(1, int(ttl))
        remaining = max(0, int(remaining))

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(ttl),
        }

        if not allowed:
            headers["Retry-After"] = str(ttl)

            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Try again later.",
                    },
                },
                headers=headers,
            )

        response = await call_next(request)
        response.headers.update(headers)

        return response
