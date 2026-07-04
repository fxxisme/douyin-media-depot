from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_name: str = os.getenv("APP_NAME", "Douyin Media Depot")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8080"))
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8080")
    data_dir: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()
    download_dir: Path = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
    temp_dir: Path = Path(os.getenv("TEMP_DIR", "./tmp")).resolve()
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    max_concurrent_downloads: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    download_retry_limit: int = int(os.getenv("DOWNLOAD_RETRY_LIMIT", "3"))
    ffmpeg_bin: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    ffprobe_bin: str = os.getenv("FFPROBE_BIN", "ffprobe")
    audio_extract_mode: str = os.getenv("AUDIO_EXTRACT_MODE", "copy")
    webdav_enabled: bool = _get_bool("WEBDAV_ENABLED", False)
    webdav_url: str = os.getenv("WEBDAV_URL", "")
    webdav_username: str = os.getenv("WEBDAV_USERNAME", "")
    webdav_password: str = os.getenv("WEBDAV_PASSWORD", "")
    webdav_remote_dir: str = os.getenv("WEBDAV_REMOTE_DIR", "/douyin-media")
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )

    def validate_required(self) -> None:
        if not self.app_secret_key:
            raise RuntimeError("APP_SECRET_KEY is required")
        if not self.admin_password:
            raise RuntimeError("ADMIN_PASSWORD is required")


settings = Settings()
