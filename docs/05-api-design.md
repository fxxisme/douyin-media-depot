# API 设计

基础路径：

```text
/api/v1
```

响应格式：

```json
{
  "data": {},
  "error": null
}
```

错误格式：

```json
{
  "data": null,
  "error": {
    "code": "account_cookie_invalid",
    "message": "Cookie 已失效",
    "detail": {}
  }
}
```

## Auth

### POST `/auth/login`

```json
{
  "password": "string"
}
```

### POST `/auth/logout`

无请求体。

### GET `/auth/me`

返回当前登录状态。

## Accounts

### GET `/accounts`

返回账号列表，不返回 Cookie 明文。

### POST `/accounts`

```json
{
  "name": "我的抖音",
  "cookie": "sessionid=..."
}
```

### PATCH `/accounts/{account_id}`

```json
{
  "name": "新名称",
  "cookie": "sessionid=...",
  "enabled": true
}
```

### POST `/accounts/{account_id}/verify`

校验 Cookie 是否可用。

### DELETE `/accounts/{account_id}`

删除账号。默认不删除已下载媒体。

## Sources

### POST `/accounts/{account_id}/sync`

```json
{
  "source_type": "liked",
  "limit": 100
}
```

`source_type`：

```text
liked
favorite
```

### GET `/sources`

查询已同步的视频来源列表。

Query：

```text
account_id
source_type
keyword
downloaded
page
page_size
```

## Download Tasks

### POST `/tasks`

```json
{
  "source_item_ids": [1, 2, 3],
  "download_type": "audio"
}
```

`download_type`：

```text
video
audio
both
```

### GET `/tasks`

Query：

```text
status
page
page_size
```

### POST `/tasks/{task_id}/retry`

重试失败任务。

### POST `/tasks/{task_id}/cancel`

取消 pending/running 任务。

## Media

### GET `/media`

Query：

```text
media_type
account_id
keyword
author
page
page_size
```

`media_type`：

```text
video
audio
```

### GET `/media/{media_id}`

返回媒体详情。

### DELETE `/media/{media_id}`

删除数据库记录和实际文件。

### GET `/media/{media_id}/file`

下载或播放文件。

## Settings

### GET `/settings`

返回脱敏后的系统设置。

### PATCH `/settings`

更新可变配置。

第一版可变配置：

```json
{
  "max_concurrent_downloads": 2,
  "audio_extract_mode": "copy"
}
```

