from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.crypto import decrypt_text, encrypt_text
from app.core.paths import safe_slug
from app.core.responses import fail, ok
from app.db.models import Account, DownloadTask, SourceItem, utc_now
from app.schemas import AccountCreate, AccountUpdate, SyncRequest
from app.services.douyin.client import DouyinAdapter, DouyinAdapterError
from app.services.serializers import account_to_dict

router = APIRouter(prefix="/accounts", tags=["accounts"])
adapter = DouyinAdapter()


def _unique_slug(db: DbSession, name: str, account_id: int | None = None) -> str:
    base = safe_slug(name)
    candidate = base
    index = 2
    while True:
        stmt = select(Account).where(Account.slug == candidate)
        existing = db.scalar(stmt)
        if existing is None or existing.id == account_id:
            return candidate
        candidate = f"{base}-{index}"
        index += 1


@router.get("")
def list_accounts(db: DbSession, _user: CurrentUser):
    items = db.scalars(select(Account).order_by(Account.created_at.desc())).all()
    return ok([account_to_dict(item) for item in items])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: DbSession, _user: CurrentUser):
    now = utc_now()
    account = Account(
        name=payload.name,
        slug=_unique_slug(db, payload.name),
        encrypted_cookie=encrypt_text(payload.cookie),
        status="active",
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return ok(account_to_dict(account))


@router.patch("/{account_id}")
def update_account(account_id: int, payload: AccountUpdate, db: DbSession, _user: CurrentUser):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if payload.name is not None:
        account.name = payload.name
        account.slug = _unique_slug(db, payload.name, account_id=account.id)
    if payload.cookie is not None:
        account.encrypted_cookie = encrypt_text(payload.cookie)
        account.status = "active"
    if payload.enabled is not None:
        account.enabled = payload.enabled
        if not payload.enabled:
            account.status = "disabled"
        elif account.status == "disabled":
            account.status = "active"
    account.updated_at = utc_now()
    db.commit()
    db.refresh(account)
    return ok(account_to_dict(account))


@router.post("/{account_id}/verify")
def verify_account(account_id: int, response: Response, db: DbSession, _user: CurrentUser):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        adapter.verify_cookie(decrypt_text(account.encrypted_cookie))
        account.status = "active" if account.enabled else "disabled"
        account.last_verified_at = utc_now()
        account.updated_at = utc_now()
        db.commit()
        return ok(account_to_dict(account))
    except DouyinAdapterError as exc:
        account.status = "invalid"
        account.last_verified_at = utc_now()
        account.updated_at = utc_now()
        db.commit()
        response.status_code = 400
        return fail(exc.code, exc.message)


@router.delete("/{account_id}")
def delete_account(account_id: int, db: DbSession, _user: CurrentUser):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
    return ok({"deleted": True})


@router.post("/{account_id}/sync")
def sync_account(account_id: int, payload: SyncRequest, response: Response, db: DbSession, _user: CurrentUser):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.enabled:
        response.status_code = 400
        return fail("account_disabled", "账号已停用")
    try:
        cookie = decrypt_text(account.encrypted_cookie)
        adapter.verify_cookie(cookie)
        items = adapter.sync_items(source_type=payload.source_type, limit=payload.limit, cookie=cookie)
    except DouyinAdapterError as exc:
        account.status = "expired" if exc.code == "account_cookie_invalid" else account.status
        account.updated_at = utc_now()
        db.commit()
        response.status_code = 501
        return fail(exc.code, exc.message)

    now = utc_now()
    created = 0
    for item in items:
        platform_item_id = item["platform_item_id"]
        exists = db.scalar(
            select(SourceItem).where(
                SourceItem.account_id == account.id,
                SourceItem.source_type == payload.source_type,
                SourceItem.platform_item_id == platform_item_id,
            )
        )
        if exists:
            exists.platform = item.get("platform", exists.platform)
            exists.title = item.get("title") or exists.title
            exists.author_name = item.get("author_name") or exists.author_name
            exists.author_id = item.get("author_id") or exists.author_id
            exists.cover_url = item.get("cover_url") or exists.cover_url
            exists.detail_url = item.get("detail_url") or exists.detail_url
            exists.duration_seconds = item.get("duration_seconds") or exists.duration_seconds
            exists.published_at = item.get("published_at") or exists.published_at
            exists.raw_json = item.get("raw_json") or exists.raw_json
            exists.last_seen_at = now
            continue
        db.add(SourceItem(account_id=account.id, source_type=payload.source_type, first_seen_at=now, last_seen_at=now, **item))
        created += 1
    account.last_sync_at = now
    account.updated_at = now
    db.commit()
    total = db.scalar(select(func.count()).select_from(SourceItem).where(SourceItem.account_id == account.id)) or 0
    return ok({"created": created, "total": total})
