from __future__ import annotations

import shutil

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.responses import ok
from app.db.models import AppSetting, utc_now
from app.schemas import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_value(db: DbSession, key: str, fallback: str) -> str:
    item = db.scalar(select(AppSetting).where(AppSetting.key == key))
    return item.value if item else fallback


def _set_value(db: DbSession, key: str, value: str) -> None:
    item = db.get(AppSetting, key)
    if item is None:
        db.add(AppSetting(key=key, value=value, updated_at=utc_now()))
    else:
        item.value = value
        item.updated_at = utc_now()


@router.get("")
def get_settings(db: DbSession, _user: CurrentUser):
    return ok(
        {
            "app_name": settings.app_name,
            "app_env": settings.app_env,
            "public_base_url": settings.public_base_url,
            "data_dir": str(settings.data_dir),
            "download_dir": str(settings.download_dir),
            "temp_dir": str(settings.temp_dir),
            "max_concurrent_downloads": int(_get_value(db, "max_concurrent_downloads", str(settings.max_concurrent_downloads))),
            "audio_extract_mode": _get_value(db, "audio_extract_mode", settings.audio_extract_mode),
            "ffmpeg_available": shutil.which(settings.ffmpeg_bin) is not None,
            "ffprobe_available": shutil.which(settings.ffprobe_bin) is not None,
            "webdav_enabled": settings.webdav_enabled,
            "webdav_url": settings.webdav_url,
            "webdav_remote_dir": settings.webdav_remote_dir,
        }
    )


@router.patch("")
def update_settings(payload: SettingsUpdate, db: DbSession, _user: CurrentUser):
    if payload.max_concurrent_downloads is not None:
        _set_value(db, "max_concurrent_downloads", str(payload.max_concurrent_downloads))
    if payload.audio_extract_mode is not None:
        _set_value(db, "audio_extract_mode", payload.audio_extract_mode)
    db.commit()
    return get_settings(db, _user)
