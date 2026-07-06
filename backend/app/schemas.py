from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    cookie: str = Field(min_length=1)
    sec_user_id: str = Field(min_length=1, max_length=500)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    cookie: str | None = Field(default=None, min_length=1)
    sec_user_id: str | None = Field(default=None, min_length=1, max_length=500)
    enabled: bool | None = None


class SyncRequest(BaseModel):
    source_type: str = Field(pattern="^(liked|favorite)$")
    limit: int = Field(default=100, ge=1, le=500)


class TaskCreate(BaseModel):
    source_item_ids: list[int] = Field(min_length=1)
    download_type: str = Field(pattern="^(video|audio|both)$")


class ManualSourceCreate(BaseModel):
    account_id: int
    url: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(default=None, max_length=300)


class SettingsUpdate(BaseModel):
    max_concurrent_downloads: int | None = Field(default=None, ge=1, le=8)
    audio_extract_mode: str | None = Field(default=None, pattern="^copy$")


class Page(BaseModel):
    items: list[dict]
    page: int
    page_size: int
    total: int
