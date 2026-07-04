# Douyin Media Depot

个人自用的抖音点赞/收藏媒体同步与本地管理工具，目标是部署到 NAS 后，把个人账号里的媒体资源备份到本地目录，并优先保留原始视频流或原音轨。

> 当前版本是本地可用 MVP。真实抖音同步/下载逻辑已经预留 adapter 边界，但尚未接入稳定的真实下载实现；不会伪造成功，也不包含绕过平台风控的逻辑。

## 功能状态

- 管理员密码登录，HttpOnly Session Cookie。
- 多抖音账号管理，支持 Cookie 保存、更新、启停、校验。
- Cookie 加密入库，API 和页面不返回明文。
- 媒体、来源、任务、设置页面。
- SQLite 数据持久化。
- 下载任务状态流转和失败原因展示。
- 媒体文件路径安全校验。
- Docker 单容器部署，镜像内自动安装 `ffmpeg` 和 `ffprobe`。

## 技术栈

前端：

```text
React + Vite + TypeScript
Tailwind CSS
TanStack Query + TanStack Router
Lucide Icons
```

后端：

```text
FastAPI
SQLAlchemy 2.x
SQLite
cryptography
ffmpeg / ffprobe
```

部署：

```text
Docker
Docker Compose
NAS volume 挂载
```

## 快速部署

### 1. 准备 `.env`

```bash
cp .env.example .env
```

必须修改：

```text
APP_SECRET_KEY=替换为随机长字符串
ADMIN_PASSWORD=替换为你的管理员密码
```

建议生产部署至少使用 32 位以上随机字符串作为 `APP_SECRET_KEY`。

### 2. 启动

```bash
docker compose up -d --build
```

访问：

```text
http://NAS_IP:3088
```

默认端口映射是 `3088:8080`：NAS 对外访问 `3088`，容器内部服务仍监听 `8080`。如需改宿主机端口，可在 `.env` 中调整 `HOST_PORT`。

### 3. ffmpeg 说明

真实 Docker 部署时不需要你在 NAS 主机上额外安装 ffmpeg。

原因：

- `Dockerfile` 使用 `apt-get install ffmpeg`。
- 构建镜像时会把 `ffmpeg` 和 `ffprobe` 安装进容器。
- `docker-compose.yml` 默认配置：

```text
FFMPEG_BIN=ffmpeg
FFPROBE_BIN=ffprobe
```

只有在本地 Windows 直接运行后端、不使用 Docker 时，才需要你自己安装 ffmpeg，或接受设置页显示“未找到”。

## 本地开发启动

### 后端

Windows PowerShell：

```powershell
cd C:\temp\workspace\douyin-media-depot
python -m venv .venv
.\.venv\Scripts\python -m pip install -r .\backend\requirements.txt

$env:APP_SECRET_KEY="dev-secret-change-me"
$env:ADMIN_PASSWORD="change-this-password"

if (-not (Test-Path .\data)) { New-Item -ItemType Directory .\data | Out-Null }
if (-not (Test-Path .\downloads)) { New-Item -ItemType Directory .\downloads | Out-Null }
if (-not (Test-Path .\tmp)) { New-Item -ItemType Directory .\tmp | Out-Null }

$env:DATA_DIR=(Resolve-Path .\data).Path
$env:DOWNLOAD_DIR=(Resolve-Path .\downloads).Path
$env:TEMP_DIR=(Resolve-Path .\tmp).Path
$env:DATABASE_URL="sqlite:///./data/app.db"

.\.venv\Scripts\python -m uvicorn app.main:app --app-dir .\backend --host 127.0.0.1 --port 8080
```

后端地址：

```text
http://127.0.0.1:8080/api/v1
```

### 前端

另开一个 PowerShell：

```powershell
cd C:\temp\workspace\douyin-media-depot\frontend
pnpm install
$env:VITE_API_BASE_URL="http://127.0.0.1:8080/api/v1"
pnpm dev
```

前端地址：

```text
http://127.0.0.1:5173
```

本地默认登录密码来自后端环境变量：

```text
change-this-password
```

Docker/域名部署时前端默认使用相对接口地址：

```text
/api/v1
```

不要在生产镜像里写死 `127.0.0.1:8080`，否则浏览器会请求访问者本机。

## 数据目录

默认只使用 clone 出来的项目目录，不需要访问 NAS 其他位置。Compose 挂载关系：

```text
./data       -> /app/data       # SQLite 数据库
./downloads  -> /app/downloads  # 视频、音频、封面
./tmp        -> /app/tmp        # 临时文件
```

也就是说，如果项目 clone 到：

```text
/volume1/docker/douyin-media-depot
```

下载文件就在：

```text
/volume1/docker/douyin-media-depot/downloads
```

仓库里保留了这些目录的 `.gitkeep` 占位文件，实际数据库、下载文件、临时文件和日志不会提交到 Git。

当前镜像默认以容器 root 用户运行，避免 NAS 挂载目录因 UID/GID 不匹配导致无法写入。

建议备份：

```text
.env
data/
downloads/
```

## API

基础路径：

```text
/api/v1
```

核心接口：

```text
POST   /auth/login
POST   /auth/logout
GET    /auth/me

GET    /accounts
POST   /accounts
PATCH  /accounts/{account_id}
POST   /accounts/{account_id}/verify
POST   /accounts/{account_id}/sync
DELETE /accounts/{account_id}

GET    /sources

POST   /tasks
GET    /tasks
POST   /tasks/{task_id}/retry
POST   /tasks/{task_id}/cancel

GET    /media
GET    /media/{media_id}
GET    /media/{media_id}/file
DELETE /media/{media_id}

GET    /settings
PATCH  /settings
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
    "code": "download_not_configured",
    "message": "真实下载适配器尚未接入",
    "detail": {}
  }
}
```

## 项目结构

```text
backend/
  app/
    api/
    core/
    db/
    services/
frontend/
  src/
docs/
docker-compose.yml
Dockerfile
```

## 当前边界

第一版不做：

- 公开分享站点。
- 多用户权限系统。
- 在线破解或绕过平台风控。
- 批量搬运能力。
- 音频增强、识曲、歌词匹配。
- 复杂媒体服务器能力。

## 合规说明

本项目定位为个人账号、个人收藏内容的自用备份工具。不要用于公开传播、批量搬运、商业用途或绕过平台访问控制。
