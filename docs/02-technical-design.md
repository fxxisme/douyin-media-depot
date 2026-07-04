# 技术架构设计

## 总体架构

```text
Browser / Mobile PWA
        |
        v
React Frontend
        |
        v
FastAPI REST API
        |
        +-- SQLite
        +-- Download Queue
        +-- Douyin Adapter
        +-- ffmpeg / ffprobe
        +-- Local Storage
        +-- Optional WebDAV
```

## 第一版部署形态

第一版使用单容器：

```text
FastAPI 服务
+ 静态托管 frontend/dist
+ 内置 ffmpeg
+ 内置下载适配器
+ SQLite 数据库
```

原因：

- 飞牛 NAS 部署简单。
- 少维护 Redis、PostgreSQL、Nginx。
- MVP 资源占用低。
- 后续仍可拆分 worker。

## 后续可拆分形态

```text
frontend
api
worker
redis
postgres
```

拆分触发条件：

- 下载任务量明显增加。
- 需要多 worker 并发。
- SQLite 写锁成为瓶颈。
- 需要多用户或远程访问。

## 技术选型

### 前端

```text
React
Vite
TypeScript
Tailwind CSS
shadcn/ui
TanStack Query
TanStack Router
Zod
```

理由：

- React 生态最大，后续插件和示例最多。
- shadcn/ui 是可复制代码组件，不强绑定企业后台视觉。
- Tailwind 适合做移动端优先的响应式界面。
- TanStack Query 适合接口缓存、刷新、错误状态。
- TanStack Router 类型友好，后续页面扩展清晰。

### 后端

```text
FastAPI
Pydantic v2
SQLAlchemy 2.x
Alembic
SQLite
```

理由：

- FastAPI 对 API 文档和类型约束友好。
- SQLite 适合单机 NAS。
- SQLAlchemy/Alembic 保留迁移到 PostgreSQL 的空间。

### 下载与媒体处理

```text
yt-dlp
自定义 Douyin Adapter
ffmpeg
ffprobe
```

设计原则：

- 下载逻辑通过 adapter 隔离。
- 不把第三方下载器输出直接耦合到业务表。
- 音频抽取优先 `-c:a copy`。
- 失败时记录具体命令、退出码、stderr 摘要。

## 存储目录

容器内：

```text
/app/data       # SQLite、配置、缓存
/app/downloads  # 视频、音频
/app/tmp        # 临时文件
```

建议结构：

```text
downloads/
  videos/
    {account_slug}/
      {video_id}-{safe_title}.mp4
  audios/
    {account_slug}/
      {video_id}-{safe_title}.m4a
  covers/
    {video_id}.jpg
```

## 安全边界

- Cookie 加密后入库。
- `APP_SECRET_KEY` 必须由用户配置。
- 下载路径必须限制在 `DOWNLOAD_DIR` 下。
- 删除文件只允许删除数据库登记过的媒体文件。
- 禁止用户传入任意 shell 片段。
- ffmpeg 参数由后端白名单构造。

## 性能策略

- SQLite 开启 WAL。
- 下载并发默认 2。
- 列表接口分页。
- 大文件不走 API 内存读，使用静态文件或流式响应。
- 视频列表封面懒加载。
- 前端媒体列表使用虚拟列表预留。

## 失败恢复

- 任务状态持久化。
- 服务启动时把 `running` 任务恢复为 `failed` 或 `pending`。
- 临时文件用 `.part` 后缀。
- 下载完成后原子 rename。
- 媒体抽取失败不影响原视频保留。

