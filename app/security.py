from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from fastapi import Request


CSRF_COOKIE_NAME = "csrf_token"


def generate_csrf_token() -> str:
    # URL-safe, short enough for cookie + form field.
    return secrets.token_urlsafe(32)


def get_csrf_cookie(request: Request) -> str | None:
    return request.cookies.get(CSRF_COOKIE_NAME)


def get_csrf_header(request: Request) -> str | None:
    return request.headers.get("x-csrf-token")


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_in_s: int


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter for single-node deployments.
    For multi-node, replace with Redis-backed limiter (planned later).
    """

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str, limit: int, window_s: int) -> RateLimitResult:
        now = time.time()
        bucket = self._buckets.get(key) or []
        cutoff = now - window_s
        bucket = [t for t in bucket if t >= cutoff]

        allowed = len(bucket) < limit
        if allowed:
            bucket.append(now)
        self._buckets[key] = bucket

        remaining = max(0, limit - len(bucket))
        reset_in = int(max(0, (bucket[0] + window_s) - now)) if bucket else window_s
        return RateLimitResult(allowed=allowed, remaining=remaining, reset_in_s=reset_in)


rate_limiter = InMemoryRateLimiter()

