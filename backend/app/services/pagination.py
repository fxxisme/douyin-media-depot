from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> tuple[list, int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return items, total
