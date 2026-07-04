from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import DownloadTask, utc_now
from app.services.douyin.adapter import DouyinAdapter, DouyinAdapterError

adapter = DouyinAdapter()


def run_download_placeholder(db: Session, task: DownloadTask) -> DownloadTask:
    now = utc_now()
    task.status = "running"
    task.progress = 5
    task.started_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    try:
        adapter.download(detail_url=task.source_item.detail_url if task.source_item else None, download_type=task.download_type)
    except DouyinAdapterError as exc:
        task.status = "failed"
        task.progress = 0
        task.error_code = exc.code
        task.error_message = exc.message
        task.stderr_tail = exc.message[-8192:]
        task.finished_at = utc_now()
        task.updated_at = task.finished_at
        db.commit()
        db.refresh(task)
    return task
