from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import AppSetting, DownloadTask, utc_now
from app.db.session import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_schema_columns()
    with Session(engine) as db:
        _ensure_setting(db, "admin_password_hash", hash_password(settings.admin_password))
        _ensure_setting(db, "max_concurrent_downloads", str(settings.max_concurrent_downloads))
        _ensure_setting(db, "audio_extract_mode", settings.audio_extract_mode)
        now = utc_now()
        running_tasks = db.scalars(select(DownloadTask).where(DownloadTask.status == "running")).all()
        for task in running_tasks:
            task.status = "failed"
            task.error_code = "service_restarted"
            task.error_message = "interrupted by service restart"
            task.finished_at = now
            task.updated_at = now
        db.commit()


def _ensure_schema_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as connection:
        account_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(accounts)"))}
        if "sec_user_id" not in account_columns:
            connection.execute(text("ALTER TABLE accounts ADD COLUMN sec_user_id VARCHAR(500) NOT NULL DEFAULT ''"))


def _ensure_setting(db: Session, key: str, value: str) -> None:
    item = db.get(AppSetting, key)
    if item is None:
        db.add(AppSetting(key=key, value=value, updated_at=utc_now()))
