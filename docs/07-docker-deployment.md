# Docker 部署

## 目标环境

飞牛 NAS 或其他支持 Docker 的 NAS。

第一版推荐单容器：

```text
8080 -> Web UI + API
data -> SQLite / 配置
downloads -> 视频和音频
tmp -> 临时文件
```

## 目录准备

在 NAS 上准备目录：

```text
douyin-media-depot/
  .env
  docker-compose.yml
  data/
  downloads/
  tmp/
```

## 配置 `.env`

从 `.env.example` 复制：

```text
APP_SECRET_KEY=随机长字符串
ADMIN_PASSWORD=你的管理密码
PORT=8080
```

必须修改：

```text
APP_SECRET_KEY
ADMIN_PASSWORD
```

## docker-compose

示例见根目录：

```text
docker-compose.example.yml
```

实际使用时复制为：

```text
docker-compose.yml
```

并修改镜像名：

```yaml
image: ghcr.io/your-name/douyin-media-depot:latest
```

## 启动

```bash
docker compose up -d
```

访问：

```text
http://NAS_IP:8080
```

## 数据备份

需要备份：

```text
data/app.db
downloads/
.env
```

建议定期备份：

```text
data/
downloads/
```

## 镜像构建建议

后续代码仓库可使用多阶段构建：

```text
node build frontend
python runtime backend
copy frontend/dist to backend static
install ffmpeg
```

运行镜像包含：

```text
Python runtime
FastAPI app
frontend dist
ffmpeg
ffprobe
```

## 权限

容器内建议使用非 root 用户运行。

挂载目录需要确保容器用户可写：

```text
data/
downloads/
tmp/
```

如果 NAS 权限复杂，第一版可以先用默认容器用户跑通，再收紧权限。

## 资源建议

MVP：

```text
CPU: 1-2 core
Memory: 512MB-1GB
Disk: 取决于下载量
```

下载并发建议：

```text
MAX_CONCURRENT_DOWNLOADS=1 或 2
```

NAS 环境不建议默认开高并发。

