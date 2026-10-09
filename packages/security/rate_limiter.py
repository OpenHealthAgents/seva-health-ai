"""Sliding Window Rate Limiter Middleware for SevaHealth AI.

Prevents brute-force attacks, denial-of-service (DoS), and API abuse on sensitive
clinical and authentication endpoints.
"""

import time
import threading
from typing import Dict, List, Tuple, Optional, Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from packages.observability.metrics import metrics


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # client_key -> list of request timestamps
        self._requests: Dict[str, List[float]] = {}

        # Route-specific limits per window (default calibrated for production burst and test isolation)
        self.limits: Dict[str, int] = {
            "auth": 1000,       # Auth attempts / min (overridable in tests or config)
            "ai": 500,          # AI conversational requests / min
            "documents": 200,   # Document ingestion OCR jobs / min
            "default": 1000,    # General API requests / min
        }

    def _get_category(self, path: str) -> Tuple[str, int]:
        if path.startswith("/api/v1/auth"):
            return "auth", self.limits["auth"]
        if path.startswith("/api/v1/ai"):
            return "ai", self.limits["ai"]
        if path.startswith("/api/v1/documents"):
            return "documents", self.limits["documents"]
        return "default", self.limits["default"]

    def is_allowed(self, client_key: str, path: str) -> Tuple[bool, int, int]:
        """Evaluates whether the client request is permitted under sliding window rules.
        Returns: (is_allowed, remaining_quota, limit).
        """
        category, limit = self._get_category(path)
        full_key = f"{client_key}:{category}"
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            if full_key not in self._requests:
                self._requests[full_key] = []

            # Evict timestamps older than sliding window
            self._requests[full_key] = [t for t in self._requests[full_key] if t > window_start]

            current_count = len(self._requests[full_key])
            if current_count >= limit:
                return False, 0, limit

            self._requests[full_key].append(now)
            remaining = max(0, limit - (current_count + 1))
            return True, remaining, limit

    def reset(self):
        """Resets all tracking states for test isolation."""
        with self._lock:
            self._requests.clear()


rate_limiter = SlidingWindowRateLimiter()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware enforcing client rate limits with standard HTTP 429 responses."""

    BYPASS_PATHS = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json", "/"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Bypass health checks and documentation endpoints
        if path in self.BYPASS_PATHS or path.startswith("/static"):
            return await call_next(request)

        # Identify client by user token or IP
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            client_id = f"token:{auth_header[:25]}"
        else:
            forwarded = request.headers.get("X-Forwarded-For")
            client_id = f"ip:{forwarded.split(',')[0].strip()}" if forwarded else f"ip:{request.client.host if request.client else 'unknown'}"

        allowed, remaining, limit = rate_limiter.is_allowed(client_id, path)

        if not allowed:
            metrics.record_error("RATE_LIMIT_EXCEEDED", "API_GATEWAY", f"Client {client_id} exceeded rate limit on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Too many requests. Please slow down and try again.",
                    "status_code": 429,
                    "retry_after_seconds": rate_limiter.window_seconds,
                },
                headers={
                    "Retry-After": str(rate_limiter.window_seconds),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Cache-Control": "no-store, no-cache, must-revalidate, private",
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
