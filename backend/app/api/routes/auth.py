from __future__ import annotations

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.responses import ok
from app.core.security import SESSION_COOKIE_NAME, create_session_cookie, verify_password
from app.db.models import AppSetting
from app.schemas import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: DbSession):
    setting = db.scalar(select(AppSetting).where(AppSetting.key == "admin_password_hash"))
    if setting is None or not verify_password(payload.password, setting.value):
        response.status_code = 401
        return {"data": None, "error": {"code": "invalid_credentials", "message": "密码错误", "detail": {}}}
    response.set_cookie(
        SESSION_COOKIE_NAME,
        create_session_cookie(),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 14,
    )
    return ok({"authenticated": True})


@router.post("/logout")
def logout(response: Response, _user: CurrentUser):
    response.delete_cookie(SESSION_COOKIE_NAME)
    return ok({"authenticated": False})


@router.get("/me")
def me(user: CurrentUser):
    return ok({"authenticated": True, "user": user["sub"]})
