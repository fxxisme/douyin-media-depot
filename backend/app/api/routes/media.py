from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.paths import resolve_download_path
from app.core.responses import fail, ok
from app.db.models import MediaFile, SourceItem
from app.services.pagination import paginate
from app.services.serializers import media_to_dict

router = APIRouter(prefix="/media", tags=["media"])


@router.get("")
def list_media(
    db: DbSession,
    _user: CurrentUser,
    media_type: str | None = None,
    account_id: int | None = None,
    keyword: str | None = None,
    author: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(MediaFile).join(SourceItem).options(selectinload(MediaFile.source_item)).order_by(MediaFile.created_at.desc())
    if media_type:
        stmt = stmt.where(MediaFile.media_type == media_type)
    if account_id is not None:
        stmt = stmt.where(SourceItem.account_id == account_id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(MediaFile.filename.like(like) | SourceItem.title.like(like))
    if author:
        stmt = stmt.where(SourceItem.author_name.like(f"%{author}%"))
    items, total = paginate(db, stmt, page, page_size)
    return ok({"items": [media_to_dict(item) for item in items], "page": page, "page_size": page_size, "total": total})


@router.get("/{media_id}")
def get_media(media_id: int, db: DbSession, _user: CurrentUser):
    media = db.get(MediaFile, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    return ok(media_to_dict(media))


@router.delete("/{media_id}")
def delete_media(media_id: int, response: Response, db: DbSession, _user: CurrentUser):
    media = db.get(MediaFile, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    path = resolve_download_path(media.relative_path)
    if path.exists():
        path.unlink()
    db.delete(media)
    db.commit()
    return ok({"deleted": True})


@router.get("/{media_id}/file")
def get_media_file(media_id: int, response: Response, db: DbSession, _user: CurrentUser):
    media = db.get(MediaFile, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="Media not found")
    path = resolve_download_path(media.relative_path)
    if not path.exists() or not path.is_file():
        response.status_code = 404
        return fail("media_file_missing", "数据库记录存在，但实际文件不存在")
    return FileResponse(path, media_type=media.mime_type, filename=media.filename)
