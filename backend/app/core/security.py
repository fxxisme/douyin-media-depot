from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.config import settings

SESSION_COOKIE_NAME = "dmd_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return "pbkdf2_sha256$260000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _sign(payload_b64: str) -> str:
    return hmac.new(
        settings.app_secret_key.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def create_session_cookie() -> str:
    payload = {"sub": "admin", "iat": int(time.time()), "exp": int(time.time()) + SESSION_TTL_SECONDS}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode("ascii")
    return f"{payload_b64}.{_sign(payload_b64)}"


def read_session(value: str | None) -> dict[str, Any] | None:
    if not value or "." not in value:
        return None
    payload_b64, signature = value.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(payload_b64)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode())
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def require_auth(request: Request) -> dict[str, Any]:
    payload = read_session(request.cookies.get(SESSION_COOKIE_NAME))
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return payload
