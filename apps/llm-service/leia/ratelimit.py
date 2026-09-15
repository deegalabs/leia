"""In-memory per-IP rate limit for the public write routes (quiz, chat, doubt, signup, login).

One process, one dict: enough for the hackathon deployment (Railway runs a single worker). The limit is read
from RATE_LIMIT_PER_MINUTE on every call so tests and operators can change it without a restart.
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

WINDOW_SECONDS = 60.0
DETAIL = "Muitas tentativas em pouco tempo. Aguarde um minuto e tente de novo."


def _trusted_hops() -> int:
    """How many proxies of ours the request crossed. In production that is one, the platform's edge."""
    try:
        return max(0, int(os.getenv("RATE_LIMIT_PROXY_HOPS", "1")))
    except ValueError:
        return 1


def client_ip(request: Request) -> str:
    """Who to count this request against.

    X-Forwarded-For is written left to right: whatever the caller chose to put there, then one entry appended
    by each proxy it crossed. Only the entries our own proxies appended are trustworthy, and they are at the
    right. Keying the limit on the leftmost entry, which is what the caller wrote, hands every visitor an
    unlimited supply of identities and the bucket never fills.

    The socket peer is not a fallback we can trust either: uvicorn runs with --forwarded-allow-ips=*, so it
    already rewrote it from the same header. It is only used when the header is absent, which means nobody
    is in front of us."""
    hops = _trusted_hops()
    if hops:
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if parts:
            return parts[max(0, len(parts) - hops)]
    return request.client.host if request.client else "?"


class RateLimiter:
    def __init__(self, env_var: str = "RATE_LIMIT_PER_MINUTE", default: int = 30):
        self.env_var = env_var
        self.default = default
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def limit(self) -> int:
        try:
            return max(0, int(os.getenv(self.env_var, str(self.default))))
        except ValueError:
            return self.default

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def check(self, key: str) -> None:
        limit = self.limit()
        if limit <= 0:
            return
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= limit:
                retry = int(WINDOW_SECONDS - (now - hits[0])) + 1
                raise HTTPException(429, DETAIL, headers={"Retry-After": str(retry)})
            hits.append(now)
            if len(self._hits) > 10000:  # keep memory bounded when many addresses come and go
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > WINDOW_SECONDS]:
                    self._hits.pop(k, None)

    def __call__(self, request: Request) -> None:
        self.check(client_ip(request))


limiter = RateLimiter()


def rate_limit(request: Request) -> None:
    """FastAPI dependency: ``Depends(rate_limit)`` on a route."""
    limiter(request)
