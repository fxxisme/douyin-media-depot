from __future__ import annotations

import subprocess
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.crypto import decrypt_text
from app.db.models import DownloadTask, MediaFile, SourceItem, utc_now
from app.db.session import SessionLocal
from app.services.douyin.client import DirectDouyinDownloader, DouyinAdapterError, YtDlpAdapter, build_download_prefix

direct_downloader = DirectDouyinDownloader()
yt_dlp_adapter = YtDlpAdapter()

_executor = ThreadPoolExecutor(max_workers=max(1, settings.max_concurrent_downloads))
_scheduler_lock = threading.Lock()
_active_task_ids: set[int] = set()
_cancel_events: dict[int, threading.Event] = {}


class TaskCanceled(RuntimeError):
    pass


def schedule_download_tasks() -> None:
    with _scheduler_lock:
        capacity = max(0, settings.max_concurrent_downloads - len(_active_task_ids))
        if capacity == 0:
            return
        with SessionLocal() as db:
            tasks = db.scalars(
                select(DownloadTask)
                .where(DownloadTask.status == "pending")
                .order_by(DownloadTask.created_at.asc(), DownloadTask.id.asc())
                .limit(capacity)
            ).all()
            now = utc_now()
            task_ids: list[int] = []
            for task in tasks:
                if task.id in _active_task_ids:
                    continue
                task.status = "running"
                task.progress = 5
                task.started_at = task.started_at or now
                task.updated_at = now
                _active_task_ids.add(task.id)
                _cancel_events[task.id] = threading.Event()
                task_ids.append(task.id)
            db.commit()
        for task_id in task_ids:
            _executor.submit(run_download_task_by_id, task_id)


def request_cancel_task(task_id: int) -> None:
    event = _cancel_events.get(task_id)
    if event is not None:
        event.set()


def run_download_task_by_id(task_id: int) -> None:
    try:
        with SessionLocal() as db:
            task = db.scalar(
                select(DownloadTask)
                .options(selectinload(DownloadTask.source_item).selectinload(SourceItem.account))
                .where(DownloadTask.id == task_id)
            )
            if task is not None:
                run_download_task(db, task, cancel_event=_cancel_events.get(task_id))
    finally:
        with _scheduler_lock:
            _active_task_ids.discard(task_id)
            _cancel_events.pop(task_id, None)
        schedule_download_tasks()


def run_download_task(db: Session, task: DownloadTask, cancel_event: threading.Event | None = None) -> DownloadTask:
    now = utc_now()
    if task.status == "canceled":
        return task
    if task.status == "pending":
        task.status = "running"
        task.progress = 5
        task.started_at = now
        task.updated_at = now
        db.commit()
        db.refresh(task)
    try:
        _raise_if_canceled(db, task, cancel_event)
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
                    cancel_event=cancel_event,
                )
            except DouyinAdapterError as exc:
                if exc.code == "task_canceled":
                    raise TaskCanceled("任务已取消") from exc
                if exc.code != "download_url_missing":
                    raise
                result = yt_dlp_adapter.download_video(
                    url=source.detail_url,
                    cookie=cookie,
                    output_dir=output_dir,
                    filename_prefix=prefix,
                    cancel_event=cancel_event,
                )
        else:
            result = yt_dlp_adapter.download_video(
                url=source.detail_url,
                cookie=cookie,
                output_dir=output_dir,
                filename_prefix=prefix,
                cancel_event=cancel_event,
            )

        _raise_if_canceled(db, task, cancel_event)
        if task.download_type in {"video", "both"}:
            db.add(_build_media_file(task=task, media_type="video", path=result.path, duration=result.duration))
        if task.download_type in {"audio", "both"}:
            audio_path = _extract_audio(video_path=result.path, account_slug=account.slug, filename_prefix=prefix, cancel_event=cancel_event)
            _raise_if_canceled(db, task, cancel_event)
            db.add(_build_media_file(task=task, media_type="audio", path=audio_path, duration=result.duration))
            if task.download_type == "audio":
                result.path.unlink(missing_ok=True)

        source.title = result.title or source.title
        source.author_name = result.uploader or source.author_name
        source.platform_item_id = result.video_id or source.platform_item_id
        source.last_seen_at = utc_now()
        _raise_if_canceled(db, task, cancel_event)
        task.status = "succeeded"
        task.progress = 100
        task.finished_at = utc_now()
        task.updated_at = task.finished_at
        db.commit()
        db.refresh(task)
    except TaskCanceled:
        db.rollback()
        db.refresh(task)
        task.status = "canceled"
        task.finished_at = task.finished_at or utc_now()
        task.updated_at = task.finished_at
        task.error_code = task.error_code or "task_canceled"
        task.error_message = task.error_message or "任务已取消"
        db.commit()
        db.refresh(task)
    except DouyinAdapterError as exc:
        if exc.code == "task_canceled":
            db.rollback()
            db.refresh(task)
            task.status = "canceled"
            task.finished_at = task.finished_at or utc_now()
            task.updated_at = task.finished_at
            task.error_code = task.error_code or "task_canceled"
            task.error_message = task.error_message or "任务已取消"
            db.commit()
            db.refresh(task)
        else:
            db.rollback()
            _mark_task_failed(db, task, exc.code, exc.message, exc.message)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        stderr_tail = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        _mark_task_failed(db, task, "unexpected_error", stderr_tail or "下载任务执行异常", traceback.format_exc())
    return task


def _raise_if_canceled(db: Session, task: DownloadTask, cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise TaskCanceled("任务已取消")
    db.refresh(task)
    if task.status == "canceled":
        raise TaskCanceled("任务已取消")


def _mark_task_failed(db: Session, task: DownloadTask, code: str, message: str, stderr_tail: str | None = None) -> None:
    db.refresh(task)
    if task.status == "canceled":
        return
    task.status = "failed"
    task.progress = 0
    task.error_code = code
    task.error_message = message
    task.stderr_tail = (stderr_tail or message)[-8192:]
    task.finished_at = utc_now()
    task.updated_at = task.finished_at
    db.commit()
    db.refresh(task)


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


def _extract_audio(*, video_path: Path, account_slug: str, filename_prefix: str, cancel_event: threading.Event | None = None) -> Path:
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
    completed = _run_process(command=command, timeout_seconds=600, cancel_event=cancel_event, timeout_code="audio_extract_timeout", cancel_message="音频抽取已取消")
    if completed.returncode != 0:
        stderr_tail = (completed.stderr or completed.stdout or "")[-8192:]
        raise DouyinAdapterError("audio_extract_failed", stderr_tail or "ffmpeg 音频抽取失败")
    tmp_path.replace(audio_path)
    return audio_path


def _run_process(*, command: list[str], timeout_seconds: int, cancel_event: threading.Event | None, timeout_code: str, cancel_message: str) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    started = time.monotonic()
    try:
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                _terminate_process(process)
                raise TaskCanceled(cancel_message)
            if time.monotonic() - started > timeout_seconds:
                _terminate_process(process)
                raise DouyinAdapterError(timeout_code, f"命令执行超时：{timeout_seconds} 秒")
            time.sleep(0.5)
        stdout, stderr = process.communicate()
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except Exception:
        if process.poll() is None:
            _terminate_process(process)
        raise


def _terminate_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _mime_type(path: Path, media_type: str) -> str | None:
    suffix = path.suffix.lower()
    if media_type == "video" and suffix == ".mp4":
        return "video/mp4"
    if media_type == "audio" and suffix == ".m4a":
        return "audio/mp4"
    return None
