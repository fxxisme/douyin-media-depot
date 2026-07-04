from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.responses import ok
from app.db.models import SourceItem
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
