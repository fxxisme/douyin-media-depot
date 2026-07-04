from __future__ import annotations


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
