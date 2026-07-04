from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.responses import ok
from app.db.models import Account, SourceItem, utc_now
from app.schemas import ManualSourceCreate
from app.services.pagination import paginate
from app.services.serializers import source_item_to_dict

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(
    db: DbSession,
    _user: CurrentUser,
    account_id: int | None = None,
    source_type: str | None = None,
    keyword: str | None = None,
    downloaded: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt: Select = select(SourceItem).options(selectinload(SourceItem.account), selectinload(SourceItem.media_files))
    if account_id is not None:
        stmt = stmt.where(SourceItem.account_id == account_id)
    if source_type:
        stmt = stmt.where(SourceItem.source_type == source_type)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(SourceItem.title.like(like) | SourceItem.author_name.like(like))
    stmt = stmt.order_by(SourceItem.last_seen_at.desc())
    items, total = paginate(db, stmt, page, page_size)
    rows = [source_item_to_dict(item) for item in items]
    if downloaded is not None:
        rows = [row for row in rows if row["downloaded"] is downloaded]
    return ok({"items": rows, "page": page, "page_size": page_size, "total": total})


@router.post("/manual")
def create_manual_source(payload: ManualSourceCreate, db: DbSession, _user: CurrentUser):
    account = db.get(Account, payload.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    now = utc_now()
    existing = db.scalar(
        select(SourceItem).where(
            SourceItem.account_id == payload.account_id,
            SourceItem.source_type == "manual",
            SourceItem.detail_url == payload.url,
        )
    )
    if existing:
        return ok(source_item_to_dict(existing))
    item = SourceItem(
        account_id=payload.account_id,
        source_type="manual",
        platform="douyin",
        platform_item_id=payload.url,
        title=payload.title or "手动添加的视频",
        detail_url=payload.url,
        first_seen_at=now,
        last_seen_at=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(source_item_to_dict(item))
