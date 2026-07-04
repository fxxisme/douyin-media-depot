from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.responses import fail, ok
from app.db.models import DownloadTask, SourceItem, utc_now
from app.schemas import TaskCreate
from app.services.pagination import paginate
from app.services.serializers import task_to_dict
from app.services.tasks import run_download_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("")
def create_tasks(payload: TaskCreate, db: DbSession, _user: CurrentUser):
    created: list[DownloadTask] = []
    for source_item_id in payload.source_item_ids:
        source = db.get(SourceItem, source_item_id)
        if source is None:
            raise HTTPException(status_code=404, detail=f"Source item {source_item_id} not found")
        task = DownloadTask(
            source_item_id=source_item_id,
            download_type=payload.download_type,
            status="pending",
            progress=0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(task)
        created.append(task)
    db.commit()
    for task in created:
        task = db.scalar(
            select(DownloadTask)
            .options(selectinload(DownloadTask.source_item).selectinload(SourceItem.account))
            .where(DownloadTask.id == task.id)
        )
        if task is None:
            continue
        run_download_task(db, task)
    return ok([task_to_dict(task) for task in created])


@router.get("")
def list_tasks(
    db: DbSession,
    _user: CurrentUser,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(DownloadTask).options(selectinload(DownloadTask.source_item).selectinload(SourceItem.account)).order_by(DownloadTask.created_at.desc())
    if status:
        stmt = stmt.where(DownloadTask.status == status)
    items, total = paginate(db, stmt, page, page_size)
    return ok({"items": [task_to_dict(item) for item in items], "page": page, "page_size": page_size, "total": total})


@router.post("/{task_id}/retry")
def retry_task(task_id: int, response: Response, db: DbSession, _user: CurrentUser):
    task = db.get(DownloadTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "failed":
        response.status_code = 400
        return fail("task_not_failed", "只有 failed 任务可以重试")
    task.status = "pending"
    task.progress = 0
    task.error_code = None
    task.error_message = None
    task.stderr_tail = None
    task.started_at = None
    task.finished_at = None
    task.updated_at = utc_now()
    db.commit()
    db.refresh(task)
    run_download_task(db, task)
    return ok(task_to_dict(task))


@router.post("/{task_id}/cancel")
def cancel_task(task_id: int, response: Response, db: DbSession, _user: CurrentUser):
    task = db.get(DownloadTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in {"pending", "running"}:
        response.status_code = 400
        return fail("task_not_cancelable", "只有 pending/running 任务可以取消")
    task.status = "canceled"
    task.finished_at = utc_now()
    task.updated_at = task.finished_at
    db.commit()
    db.refresh(task)
    return ok(task_to_dict(task))
