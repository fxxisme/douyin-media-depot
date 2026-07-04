from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings


def ensure_storage_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    (settings.download_dir / "videos").mkdir(parents=True, exist_ok=True)
    (settings.download_dir / "audios").mkdir(parents=True, exist_ok=True)
    (settings.download_dir / "covers").mkdir(parents=True, exist_ok=True)


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug[:48] or "account"


def safe_filename(value: str, max_length: int = 96) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", value).strip(" ._")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return (cleaned[:max_length].strip() or "untitled")


def resolve_download_path(relative_path: str) -> Path:
    if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media path")
    target = (settings.download_dir / relative_path).resolve()
    root = settings.download_dir.resolve()
    if root != target and root not in target.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid media path")
    return target
