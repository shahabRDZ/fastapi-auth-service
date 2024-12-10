"""Custom ASGI middleware for sliding-window rate limiting via Redis."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.config import settings

RATE_LIMIT_PREFIX = "rl:"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter stored in Redis.

    Each unique IP is allowed up to `max_requests` requests per
    `window_seconds` rolling window. Exceeding the limit returns HTTP 429.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = settings.rate_limit_requests,
        window_seconds: int = settings.rate_limit_window_seconds,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health-check endpoints
        if request.url.path in ("/health", "/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{RATE_LIMIT_PREFIX}{client_ip}"

        try:
            redis = request.app.state.redis
            now = time.time()
            window_start = now - self.window_seconds

            pipe = redis.pipeline()
            # Remove entries outside the current window
            pipe.zremrangebyscore(key, "-inf", window_start)
            # Count remaining entries
            pipe.zcard(key)
            # Add current request timestamp
            pipe.zadd(key, {str(now): now})
            # Reset TTL
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()

            request_count: int = results[1]

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, self.max_requests - request_count - 1)
            )
            response.headers["X-RateLimit-Reset"] = str(int(now + self.window_seconds))

            if request_count >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                    headers={
                        "Retry-After": str(self.window_seconds),
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            return response

        except Exception:
            # If Redis is unavailable, fail open (don't block legitimate traffic)
            return await call_next(request)
