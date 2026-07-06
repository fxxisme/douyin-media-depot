from __future__ import annotations

import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_text
from app.db.models import DownloadTask, MediaFile, utc_now
from app.services.douyin.client import DirectDouyinDownloader, DouyinAdapterError, YtDlpAdapter, build_download_prefix

direct_downloader = DirectDouyinDownloader()
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
        if task.download_type not in {"video", "audio", "both"}:
            raise DouyinAdapterError("download_type_not_supported", f"不支持的下载类型：{task.download_type}")
        source = task.source_item
        if source is None or not source.detail_url:
            raise DouyinAdapterError("source_url_missing", "来源条目缺少视频链接")
        account = source.account
        if account is None:
            raise DouyinAdapterError("account_missing", "来源条目缺少账号")
        cookie = decrypt_text(account.encrypted_cookie)
        output_dir = settings.download_dir / "videos" / account.slug
        prefix = build_download_prefix(source.id, source.title)
        if source.raw_json:
            try:
                result = direct_downloader.download_from_source(
                    source_raw_json=source.raw_json,
                    cookie=cookie,
                    output_dir=output_dir,
                    filename_prefix=prefix,
                )
            except DouyinAdapterError as exc:
                if exc.code != "download_url_missing":
                    raise
                result = yt_dlp_adapter.download_video(url=source.detail_url, cookie=cookie, output_dir=output_dir, filename_prefix=prefix)
        else:
            result = yt_dlp_adapter.download_video(url=source.detail_url, cookie=cookie, output_dir=output_dir, filename_prefix=prefix)

        if task.download_type in {"video", "both"}:
            db.add(_build_media_file(task=task, media_type="video", path=result.path, duration=result.duration))
        if task.download_type in {"audio", "both"}:
            audio_path = _extract_audio(video_path=result.path, account_slug=account.slug, filename_prefix=prefix)
            db.add(_build_media_file(task=task, media_type="audio", path=audio_path, duration=result.duration))
            if task.download_type == "audio":
                result.path.unlink(missing_ok=True)

        source.title = result.title or source.title
        source.author_name = result.uploader or source.author_name
        source.platform_item_id = result.video_id or source.platform_item_id
        source.last_seen_at = utc_now()
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


def _build_media_file(*, task: DownloadTask, media_type: str, path: Path, duration: int | None) -> MediaFile:
    return MediaFile(
        source_item_id=task.source_item_id,
        task_id=task.id,
        media_type=media_type,
        relative_path=path.relative_to(settings.download_dir).as_posix(),
        filename=path.name,
        file_size=path.stat().st_size,
        mime_type=_mime_type(path, media_type),
        duration_seconds=duration,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def _extract_audio(*, video_path: Path, account_slug: str, filename_prefix: str) -> Path:
    audio_dir = settings.download_dir / "audios" / account_slug
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f"{filename_prefix}.m4a"
    tmp_path = audio_dir / f"{filename_prefix}.part.m4a"
    if audio_path.exists():
        audio_path.unlink()
    if tmp_path.exists():
        tmp_path.unlink()
    command = [
        settings.ffmpeg_bin,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-map",
        "0:a:0",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(tmp_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    if completed.returncode != 0:
        stderr_tail = (completed.stderr or completed.stdout or "")[-8192:]
        raise DouyinAdapterError("audio_extract_failed", stderr_tail or "ffmpeg 音频抽取失败")
    tmp_path.replace(audio_path)
    return audio_path


def _mime_type(path: Path, media_type: str) -> str | None:
    suffix = path.suffix.lower()
    if media_type == "video" and suffix == ".mp4":
        return "video/mp4"
    if media_type == "audio" and suffix == ".m4a":
        return "audio/mp4"
    return None
