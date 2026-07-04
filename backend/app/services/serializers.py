from __future__ import annotations

from app.db.models import Account, DownloadTask, MediaFile, SourceItem


def account_to_dict(account: Account) -> dict:
    return {
        "id": account.id,
        "name": account.name,
        "slug": account.slug,
        "status": account.status,
        "enabled": account.enabled,
        "last_verified_at": account.last_verified_at,
        "last_sync_at": account.last_sync_at,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def source_item_to_dict(item: SourceItem) -> dict:
    downloaded = len(item.media_files) > 0
    return {
        "id": item.id,
        "account_id": item.account_id,
        "account_name": item.account.name if item.account else None,
        "source_type": item.source_type,
        "platform": item.platform,
        "platform_item_id": item.platform_item_id,
        "title": item.title,
        "author_name": item.author_name,
        "author_id": item.author_id,
        "cover_url": item.cover_url,
        "detail_url": item.detail_url,
        "duration_seconds": item.duration_seconds,
        "published_at": item.published_at,
        "downloaded": downloaded,
        "first_seen_at": item.first_seen_at,
        "last_seen_at": item.last_seen_at,
    }


def task_to_dict(task: DownloadTask) -> dict:
    source = task.source_item
    return {
        "id": task.id,
        "source_item_id": task.source_item_id,
        "download_type": task.download_type,
        "status": task.status,
        "progress": task.progress,
        "error_code": task.error_code,
        "error_message": task.error_message,
        "stderr_tail": task.stderr_tail,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "source_title": source.title if source else None,
        "source_author": source.author_name if source else None,
    }


def media_to_dict(media: MediaFile) -> dict:
    source = media.source_item
    return {
        "id": media.id,
        "source_item_id": media.source_item_id,
        "task_id": media.task_id,
        "media_type": media.media_type,
        "relative_path": media.relative_path,
        "filename": media.filename,
        "file_size": media.file_size,
        "mime_type": media.mime_type,
        "codec_name": media.codec_name,
        "duration_seconds": media.duration_seconds,
        "checksum": media.checksum,
        "created_at": media.created_at,
        "updated_at": media.updated_at,
        "source_title": source.title if source else None,
        "source_author": source.author_name if source else None,
        "source_detail_url": source.detail_url if source else None,
        "account_id": source.account_id if source else None,
    }
