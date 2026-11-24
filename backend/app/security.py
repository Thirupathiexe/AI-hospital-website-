"""Login tokens, role checks, rate limiting and security headers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections import defaultdict, deque
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from . import config
from .rules import Actor

COOKIE_NAME = "netracare_session"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def make_token(actor: Actor) -> str:
    payload = {"role": actor.role, "sub": actor.id, "name": actor.name,
               "exp": int(time.time()) + config.TOKEN_TTL_MINUTES * 60}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(config.SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(token: str) -> Optional[Actor]:
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(config.SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(body))
        if payload["exp"] < time.time() or payload["role"] not in ("patient", "staff", "doctor"):
            return None
        return Actor(role=payload["role"], id=payload["sub"], name=payload.get("name", ""))
    except Exception:
        return None


def current_actor(request: Request) -> Actor:
    """Who is calling? Read from the HttpOnly cookie (website) or a Bearer header (API/agent)."""
    token = request.cookies.get(COOKIE_NAME)
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    actor = read_token(token) if token else None
    if not actor:
        raise HTTPException(status_code=401, detail={"code": "NOT_LOGGED_IN", "message": "Please log in again."})
    return actor


def require(*roles: str) -> Callable[[Actor], Actor]:
    def dep(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "You don't have access to this."})
        return actor
    return dep


def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ---------- middleware ----------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding window per client IP. Tighter limits on login and the AI assistant."""
    LIMITS = {"/api/login": (10, 60), "/api/assistant": (20, 60)}
    DEFAULT = (120, 60)

    def __init__(self, app):
        super().__init__(app)
        self.hits: dict[tuple[str, str], deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api"):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        bucket = next((p for p in self.LIMITS if request.url.path.startswith(p)), "*")
        limit, window = self.LIMITS.get(bucket, self.DEFAULT)
        q = self.hits[(ip, bucket)]
        now = time.monotonic()
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return JSONResponse({"detail": {"code": "TOO_MANY_REQUESTS", "message": "Too many requests. Please wait a minute."}},
                                status_code=429, headers={"Retry-After": str(window)})
        q.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.url.path.startswith("/api"):
            h["Cache-Control"] = "no-store"
            if not request.url.path.startswith(("/api/docs", "/api/openapi")):
                h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        else:
            h["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
                "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if config.COOKIE_SECURE:
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    MAX = 16 * 1024

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > self.MAX:
            return JSONResponse({"detail": {"code": "TOO_LARGE", "message": "Request is too large."}}, status_code=413)
        return await call_next(request)
