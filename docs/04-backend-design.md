# 后端设计

## 技术栈

```text
FastAPI
Pydantic v2
SQLAlchemy 2.x
Alembic
SQLite
```

## 目录建议

```text
backend/
  app/
    main.py
    core/
      config.py
      security.py
      paths.py
      logging.py
    api/
      routes/
        auth.py
        accounts.py
        sources.py
        media.py
        tasks.py
        settings.py
    db/
      session.py
      models.py
      migrations/
    schemas/
    services/
      douyin/
        client.py
        parser.py
        adapter.py
      download/
        queue.py
        runner.py
        media.py
      webdav/
        client.py
    workers/
      scheduler.py
```

## 鉴权

第一版：

- 单管理员密码。
- 登录后发 HttpOnly Session Cookie。
- Session 存 SQLite 或签名 Cookie。

建议：

- 首次启动时读取 `ADMIN_PASSWORD`，生成管理员密码 hash。
- 后续优先使用数据库中的密码 hash，避免每次容器重启都重置密码。
- Cookie 使用 `APP_SECRET_KEY` 签名。

## Cookie 管理

抖音 Cookie 是敏感数据。

处理规则：

- 前端新增/编辑时才传完整 Cookie。
- API 返回账号信息时不返回 Cookie 明文。
- 入库前使用应用密钥加密。
- 校验登录态时解密后使用。

## 下载队列

第一版可用内存队列 + SQLite 状态：

```text
pending -> running -> succeeded
pending -> running -> failed
pending -> canceled
```

服务启动恢复：

- `running` 改为 `failed`，原因写 `interrupted by service restart`。
- 可选：把 `pending` 重新入队。

后续可替换：

```text
Redis + Arq / Dramatiq / Celery
```

## 媒体处理

### 视频下载

下载到临时文件：

```text
tmp/{task_id}.part
```

完成后移动到：

```text
downloads/videos/{account_slug}/{video_id}-{safe_title}.mp4
```

### 音频抽取

先用 `ffprobe` 判断音轨编码：

```bash
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of json input.mp4
```

再执行：

```bash
ffmpeg -y -i input.mp4 -vn -c:a copy {output_path}
```

注意：

- `aac` 可优先输出 `.m4a`。
- `opus` 不适合强行封装为 `.m4a`，优先输出 `.opus` 或 `.ogg`。
- 如果 copy 失败，第一版不要自动重编码，记录失败原因。
- 后续可增加“兼容转码”开关。

## 路径安全

所有文件路径必须通过后端生成。

规则：

- 不接受前端传绝对路径。
- 不接受 `..`。
- 删除文件时用数据库中的 `relative_path`。
- 拼接后校验 resolved path 必须在 `DOWNLOAD_DIR` 内。

## 日志

日志分三类：

```text
app.log
download.log
task stderr 摘要入库
```

任务日志不要无限增长：

- 入库保存最近 8KB stderr。
- 完整日志可写文件，后续做轮转。
