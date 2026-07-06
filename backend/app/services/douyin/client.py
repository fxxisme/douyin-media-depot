from __future__ import annotations

import datetime as dt
import json
import mimetypes
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.core.config import settings
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

    def sync_items(self, *, source_type: str, limit: int, cookie: str, sec_user_id: str | None = None) -> list[dict]:
        self.verify_cookie(cookie)
        client = DouyinWebClient(cookie=cookie)
        if source_type == "favorite":
            return client.sync_collection(limit=limit)
        if source_type == "liked":
            resolved_sec_user_id = sec_user_id or _extract_cookie_value(cookie, "sec_user_id") or _extract_cookie_value(cookie, "SecUserId")
            if not resolved_sec_user_id:
                raise DouyinAdapterError("sec_user_id_required", "同步喜欢列表需要 sec_user_id；当前账号信息中未提供，且无法从 Cookie 推断")
            return client.sync_liked(limit=limit, sec_user_id=resolved_sec_user_id)
        raise DouyinAdapterError("source_type_not_supported", f"不支持的同步类型：{source_type}")


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


class DouyinWebClient:
    host = "https://www.douyin.com"
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    def __init__(self, *, cookie: str) -> None:
        self.cookie = cookie

    def sync_collection(self, *, limit: int) -> list[dict]:
        return self._sync_aweme_pages(
            endpoint="/aweme/v1/web/aweme/listcollection",
            method="POST",
            referer="https://www.douyin.com",
            params=_collect_params(),
            cursor_name="cursor",
            next_cursor_names=("cursor", "max_cursor"),
            limit=limit,
        )

    def sync_liked(self, *, limit: int, sec_user_id: str) -> list[dict]:
        params = _favorite_params()
        params["sec_user_id"] = sec_user_id
        return self._sync_aweme_pages(
            endpoint="/aweme/v1/web/aweme/favorite",
            method="GET",
            referer="https://www.douyin.com/user/self?showTab=like",
            params=params,
            cursor_name="max_cursor",
            next_cursor_names=("max_cursor", "cursor"),
            limit=limit,
        )

    def _sync_aweme_pages(
        self,
        *,
        endpoint: str,
        method: str,
        referer: str,
        params: dict[str, str],
        cursor_name: str,
        next_cursor_names: tuple[str, ...],
        limit: int,
    ) -> list[dict]:
        cursor = "0"
        items: list[dict] = []
        seen_ids: set[str] = set()
        while len(items) < limit:
            page_params = dict(params)
            page_params[cursor_name] = cursor
            page_params["count"] = str(min(20, max(1, limit - len(items))))
            data = self._request_json(endpoint=endpoint, method=method, params=page_params, referer=referer)
            status_code = data.get("status_code")
            if status_code not in (0, None):
                raise DouyinAdapterError("douyin_api_error", data.get("status_msg") or f"抖音接口返回状态码 {status_code}")
            aweme_list = data.get("aweme_list") or []
            if not isinstance(aweme_list, list):
                raise DouyinAdapterError("douyin_api_unexpected", "抖音接口响应缺少 aweme_list")
            for aweme in aweme_list:
                if not isinstance(aweme, dict):
                    continue
                mapped = _map_aweme(aweme)
                if mapped is None or mapped["platform_item_id"] in seen_ids:
                    continue
                items.append(mapped)
                seen_ids.add(mapped["platform_item_id"])
                if len(items) >= limit:
                    break
            has_more = int(data.get("has_more") or 0)
            next_cursor = _first_non_empty(data, *next_cursor_names)
            if has_more != 1 or not next_cursor or str(next_cursor) == cursor or not aweme_list:
                break
            cursor = str(next_cursor)
            time.sleep(0.3)
        return items

    def _request_json(self, *, endpoint: str, method: str, params: dict[str, str], referer: str) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        url = f"{self.host}{endpoint}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(
            url,
            method=method,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cookie": self.cookie,
                "Referer": referer,
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[-1024:]
            if exc.code in {401, 403}:
                raise DouyinAdapterError("account_cookie_invalid", "Cookie 已失效或无权限访问抖音接口") from exc
            raise DouyinAdapterError("douyin_http_error", f"抖音接口 HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise DouyinAdapterError("douyin_network_error", f"请求抖音接口失败：{exc.reason}") from exc
        try:
            decoded = payload.decode("utf-8")
            data = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DouyinAdapterError("douyin_response_invalid", "抖音接口返回非 JSON 数据") from exc
        if not isinstance(data, dict):
            raise DouyinAdapterError("douyin_response_invalid", "抖音接口 JSON 根节点不是对象")
        return data


class DirectDouyinDownloader:
    def download_from_source(
        self,
        *,
        source_raw_json: str | None,
        cookie: str,
        output_dir: Path,
        filename_prefix: str,
    ) -> YtDlpDownloadResult:
        source = _load_raw_aweme(source_raw_json)
        urls = _extract_download_urls(source)
        if not urls:
            raise DouyinAdapterError("download_url_missing", "来源条目缺少可下载视频 URL")
        output_dir.mkdir(parents=True, exist_ok=True)
        title = source.get("desc")
        video_id = source.get("aweme_id")
        uploader = _nested_get(source, ("author", "nickname"))
        video = source.get("video") if isinstance(source.get("video"), dict) else {}
        duration = _duration_seconds(video.get("duration"))
        last_error: DouyinAdapterError | None = None
        for index, url in enumerate(urls, start=1):
            try:
                path = self._download_once(url=url, cookie=cookie, output_dir=output_dir, filename_prefix=filename_prefix, index=index)
                return YtDlpDownloadResult(path=path, title=title, duration=duration, uploader=uploader, video_id=video_id)
            except DouyinAdapterError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise DouyinAdapterError("download_failed", "视频下载失败")

    def _download_once(self, *, url: str, cookie: str, output_dir: Path, filename_prefix: str, index: int) -> Path:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cookie": cookie,
                "Referer": "https://www.douyin.com/",
                "User-Agent": DouyinWebClient.user_agent,
            },
        )
        tmp_path = output_dir / f"{filename_prefix}.{index}.part"
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                content_type = response.headers.get("Content-Type", "")
                suffix = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".mp4"
                if suffix in {".bin", ".m4v", ".mp4v"}:
                    suffix = ".mp4"
                final_path = output_dir / f"{filename_prefix}{suffix}"
                if final_path.exists():
                    final_path.unlink()
                with tmp_path.open("wb") as file:
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        file.write(chunk)
                tmp_path.replace(final_path)
                return final_path
        except urllib.error.HTTPError as exc:
            raise DouyinAdapterError("download_http_error", f"下载 HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise DouyinAdapterError("download_network_error", f"下载失败：{exc.reason}") from exc
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


def build_download_prefix(source_id: int, title: str | None) -> str:
    return f"{source_id}-{safe_filename(title or 'douyin-video', max_length=60)}"


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


def _base_params() -> dict[str, str]:
    return {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "pc_client_type": "1",
        "pc_libra_divert": "Windows",
        "cookie_enabled": "true",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_online": "true",
        "engine_name": "Blink",
        "os_name": "Windows",
        "os_version": "10",
        "device_memory": "8",
        "platform": "PC",
        "downlink": "10",
        "effective_type": "4g",
        "round_trip_time": "0",
        "update_version_code": "170400",
        "whale_cut_token": "",
    }


def _collect_params() -> dict[str, str]:
    params = _base_params()
    params.update(
        {
            "version_code": "290100",
            "version_name": "29.1.0",
            "screen_width": "1920",
            "screen_height": "1080",
            "browser_version": "130.0.0.0",
            "engine_version": "130.0.0.0",
            "cpu_core_num": "12",
            "from_user_page": "1",
            "locate_query": "false",
            "need_time_list": "1",
            "show_live_replay_strategy": "1",
            "time_list_query": "0",
            "cursor": "0",
            "count": "18",
        }
    )
    return params


def _favorite_params() -> dict[str, str]:
    params = _base_params()
    params.update(
        {
            "version_code": "170400",
            "version_name": "17.4.0",
            "screen_width": "1536",
            "screen_height": "960",
            "browser_version": "140.0.0.0",
            "engine_version": "140.0.0.0",
            "cpu_core_num": "20",
            "support_h265": "1",
            "support_dash": "1",
            "min_cursor": "0",
            "cut_version": "1",
            "count": "18",
        }
    )
    return params


def _map_aweme(aweme: dict[str, Any]) -> dict | None:
    aweme_id = str(aweme.get("aweme_id") or "")
    if not aweme_id:
        return None
    author = aweme.get("author") if isinstance(aweme.get("author"), dict) else {}
    video = aweme.get("video") if isinstance(aweme.get("video"), dict) else {}
    create_time = aweme.get("create_time")
    return {
        "platform": "douyin",
        "platform_item_id": aweme_id,
        "title": aweme.get("desc") or aweme_id,
        "author_name": author.get("nickname"),
        "author_id": str(author.get("uid") or aweme.get("author_user_id") or "") or None,
        "cover_url": _first_image_url(video.get("cover")) or _first_image_url(video.get("origin_cover")) or _first_image_url(video.get("dynamic_cover")),
        "detail_url": f"https://www.douyin.com/video/{aweme_id}",
        "duration_seconds": _duration_seconds(video.get("duration")),
        "published_at": _timestamp_to_iso(create_time),
        "raw_json": json.dumps(aweme, ensure_ascii=False, separators=(",", ":")),
    }


def _extract_download_urls(source: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    video = source.get("video") if isinstance(source.get("video"), dict) else {}
    bit_rates = video.get("bit_rate") if isinstance(video.get("bit_rate"), list) else []
    for item in bit_rates:
        if not isinstance(item, dict):
            continue
        play_addr = item.get("play_addr") if isinstance(item.get("play_addr"), dict) else {}
        urls.extend(_string_list(play_addr.get("url_list")))
    play_addr = video.get("play_addr") if isinstance(video.get("play_addr"), dict) else {}
    urls.extend(_string_list(play_addr.get("url_list")))
    return list(dict.fromkeys(urls))


def _load_raw_aweme(raw_json: str | None) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise DouyinAdapterError("source_raw_json_invalid", "来源条目的原始 JSON 无法解析") from exc
    return data if isinstance(data, dict) else {}


def _first_image_url(image: Any) -> str | None:
    if not isinstance(image, dict):
        return None
    return _first_string(image.get("url_list"))


def _first_string(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                return item
    return value if isinstance(value, str) and value else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _duration_seconds(value: Any) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    return int(value / 1000) if value > 10000 else int(value)


def _timestamp_to_iso(value: Any) -> str | None:
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc).isoformat()


def _extract_cookie_value(cookie: str, name: str) -> str | None:
    for part in cookie.split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        if key == name and value:
            return urllib.parse.unquote(value)
    return None


def _first_non_empty(data: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return None


def _nested_get(data: dict[str, Any], path: tuple[str, ...]) -> str | None:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None
