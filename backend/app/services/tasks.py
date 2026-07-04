from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text
from app.core.config import settings
from app.db.models import DownloadTask, MediaFile, utc_now
from app.services.douyin.adapter import DouyinAdapterError, YtDlpAdapter, build_download_prefix

yt_dlp_adapter = YtDlpAdapter()


def run_download_task(db: Session, task: DownloadTask) -> DownloadTask:
    now = utc_now()
    task.status = "running"
    task.progress = 5
    task.started_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    try:
        if task.download_type != "video":
            raise DouyinAdapterError("download_type_not_supported", "当前手动链接下载先支持 video，音频抽取会在下一步接入")
        source = task.source_item
        if source is None or not source.detail_url:
            raise DouyinAdapterError("source_url_missing", "来源条目缺少视频链接")
        account = source.account
        if account is None:
            raise DouyinAdapterError("account_missing", "来源条目缺少账号")
        cookie = decrypt_text(account.encrypted_cookie)
        output_dir = settings.download_dir / "videos" / account.slug
        prefix = build_download_prefix(source.id, source.title)
        result = yt_dlp_adapter.download_video(url=source.detail_url, cookie=cookie, output_dir=output_dir, filename_prefix=prefix)
        relative_path = result.path.relative_to(settings.download_dir).as_posix()
        media = MediaFile(
            source_item_id=source.id,
            task_id=task.id,
            media_type="video",
            relative_path=relative_path,
            filename=result.path.name,
            file_size=result.path.stat().st_size,
            mime_type="video/mp4" if result.path.suffix.lower() == ".mp4" else None,
            duration_seconds=result.duration,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        source.title = result.title or source.title
        source.author_name = result.uploader or source.author_name
        source.platform_item_id = result.video_id or source.platform_item_id
        source.last_seen_at = utc_now()
        db.add(media)
        task.status = "succeeded"
        task.progress = 100
        task.finished_at = utc_now()
        task.updated_at = task.finished_at
        db.commit()
        db.refresh(task)
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
