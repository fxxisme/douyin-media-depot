from __future__ import annotations

from typing import Any


def ok(data: Any = None) -> dict[str, Any]:
    return {"data": data, "error": None}


def fail(code: str, message: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": None, "error": {"code": code, "message": message, "detail": detail or {}}}
