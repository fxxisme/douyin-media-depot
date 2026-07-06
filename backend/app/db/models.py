from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    encrypted_cookie: Mapped[str] = mapped_column(Text, nullable=False)
    sec_user_id: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_verified_at: Mapped[str | None] = mapped_column(String(40))
    last_sync_at: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)

    source_items: Mapped[list["SourceItem"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class SourceItem(Base):
    __tablename__ = "source_items"
    __table_args__ = (UniqueConstraint("account_id", "source_type", "platform_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False, default="douyin")
    platform_item_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    author_name: Mapped[str | None] = mapped_column(String(160))
    author_id: Mapped[str | None] = mapped_column(String(120))
    cover_url: Mapped[str | None] = mapped_column(Text)
    detail_url: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[str | None] = mapped_column(String(40))
    raw_json: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)
    last_seen_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)

    account: Mapped[Account] = relationship(back_populates="source_items")
    tasks: Mapped[list["DownloadTask"]] = relationship(back_populates="source_item", cascade="all, delete-orphan")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="source_item", cascade="all, delete-orphan")


class DownloadTask(Base):
    __tablename__ = "download_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_item_id: Mapped[int] = mapped_column(ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False)
    download_type: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    stderr_tail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str | None] = mapped_column(String(40))
    finished_at: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)

    source_item: Mapped[SourceItem] = relationship(back_populates="tasks")
    media_files: Mapped[list["MediaFile"]] = relationship(back_populates="task")


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_item_id: Mapped[int] = mapped_column(ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("download_tasks.id", ondelete="SET NULL"))
    media_type: Mapped[str] = mapped_column(String(24), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    codec_name: Mapped[str | None] = mapped_column(String(80))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)

    source_item: Mapped[SourceItem] = relationship(back_populates="media_files")
    task: Mapped[DownloadTask | None] = relationship(back_populates="media_files")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default=utc_now)
