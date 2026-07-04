from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.core.paths import safe_filename


class DouyinAdapterError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DouyinAdapter:
    def verify_cookie(self, cookie: str) -> None:
        if "sessionid=" not in cookie and "sid_guard=" not in cookie:
            raise DouyinAdapterError("account_cookie_invalid", "Cookie 缺少 sessionid 或 sid_guard，无法确认登录态")

    def sync_items(self, *, source_type: str, limit: int) -> list[dict]:
        raise DouyinAdapterError(
            "douyin_sync_not_configured",
            f"真实抖音 {source_type} 同步适配器尚未接入；请后续配置 yt-dlp 或专用解析器",
        )

    def download(self, *, detail_url: str | None, download_type: str) -> None:
        raise DouyinAdapterError(
            "download_not_configured",
            f"真实 {download_type} 下载适配器尚未接入；需要有效 Cookie、网络环境和下载器实现",
        )


class YtDlpDownloadResult:
    def __init__(self, path: Path, title: str | None, duration: int | None, uploader: str | None, video_id: str | None) -> None:
        self.path = path
        self.title = title
        self.duration = duration
        self.uploader = uploader
        self.video_id = video_id


class YtDlpAdapter:
    def download_video(self, *, url: str, cookie: str, output_dir: Path, filename_prefix: str) -> YtDlpDownloadResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        cookie_file = output_dir / f".{filename_prefix}.cookies.txt"
        output_template = str(output_dir / f"{filename_prefix}-%(title).80B.%(ext)s")
        try:
            cookie_file.write_text(_cookie_header_to_netscape(cookie), encoding="utf-8")
            command = [
                sys.executable,
                "-m",
                "yt_dlp",
                "--cookies",
                str(cookie_file),
                "--no-playlist",
                "--no-progress",
                "--restrict-filenames",
                "--write-info-json",
                "--paths",
                str(output_dir),
                "-o",
                output_template,
                url,
            ]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
            stderr_tail = (completed.stderr or completed.stdout or "")[-8192:]
            if completed.returncode != 0:
                raise DouyinAdapterError("yt_dlp_failed", stderr_tail or "yt-dlp 下载失败")
            info_path = _find_latest_info_json(output_dir, filename_prefix)
            info = json.loads(info_path.read_text(encoding="utf-8")) if info_path else {}
            media_path = _find_downloaded_media(output_dir, filename_prefix)
            if media_path is None:
                raise DouyinAdapterError("download_file_missing", "yt-dlp 执行完成，但未找到下载文件")
            return YtDlpDownloadResult(
                path=media_path,
                title=info.get("title"),
                duration=info.get("duration"),
                uploader=info.get("uploader") or info.get("channel"),
                video_id=info.get("id"),
            )
        finally:
            if cookie_file.exists():
                cookie_file.unlink()


def _cookie_header_to_netscape(cookie: str) -> str:
    lines = ["# Netscape HTTP Cookie File"]
    for part in cookie.split(";"):
        if "=" not in part:
            continue
        name, value = part.strip().split("=", 1)
        if not name:
            continue
        lines.append(f".douyin.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}")
    return "\n".join(lines) + "\n"


def _find_latest_info_json(output_dir: Path, filename_prefix: str) -> Path | None:
    matches = sorted(output_dir.glob(f"{filename_prefix}-*.info.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _find_downloaded_media(output_dir: Path, filename_prefix: str) -> Path | None:
    excluded_suffixes = {".json", ".part", ".ytdl"}
    candidates = [
        item
        for item in output_dir.glob(f"{filename_prefix}-*")
        if item.is_file() and not any(str(item).endswith(suffix) for suffix in excluded_suffixes)
    ]
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def build_download_prefix(source_id: int, title: str | None) -> str:
    return f"{source_id}-{safe_filename(title or 'douyin-video', max_length=60)}"
