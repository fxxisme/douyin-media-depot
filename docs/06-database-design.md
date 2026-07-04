# 数据库设计

数据库：

```text
SQLite
```

建议：

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
```

## accounts

抖音账号。

```sql
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  encrypted_cookie TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  enabled INTEGER NOT NULL DEFAULT 1,
  last_verified_at TEXT,
  last_sync_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

## source_items

从点赞/收藏同步到的抖音视频条目。

```sql
CREATE TABLE source_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  source_type TEXT NOT NULL,
  platform TEXT NOT NULL DEFAULT 'douyin',
  platform_item_id TEXT NOT NULL,
  title TEXT,
  author_name TEXT,
  author_id TEXT,
  cover_url TEXT,
  detail_url TEXT,
  duration_seconds INTEGER,
  published_at TEXT,
  raw_json TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
  UNIQUE(account_id, source_type, platform_item_id)
);
```

## download_tasks

下载任务。

```sql
CREATE TABLE download_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_item_id INTEGER NOT NULL,
  download_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  progress INTEGER NOT NULL DEFAULT 0,
  error_code TEXT,
  error_message TEXT,
  stderr_tail TEXT,
  started_at TEXT,
  finished_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (source_item_id) REFERENCES source_items(id) ON DELETE CASCADE
);
```

## media_files

已下载文件。

```sql
CREATE TABLE media_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_item_id INTEGER NOT NULL,
  task_id INTEGER,
  media_type TEXT NOT NULL,
  relative_path TEXT NOT NULL UNIQUE,
  filename TEXT NOT NULL,
  file_size INTEGER,
  mime_type TEXT,
  codec_name TEXT,
  duration_seconds INTEGER,
  checksum TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (source_item_id) REFERENCES source_items(id) ON DELETE CASCADE,
  FOREIGN KEY (task_id) REFERENCES download_tasks(id) ON DELETE SET NULL
);
```

## app_settings

可变配置。

```sql
CREATE TABLE app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

## indexes

```sql
CREATE INDEX idx_source_items_account_source
  ON source_items(account_id, source_type);

CREATE INDEX idx_source_items_author
  ON source_items(author_name);

CREATE INDEX idx_download_tasks_status
  ON download_tasks(status);

CREATE INDEX idx_media_files_type
  ON media_files(media_type);
```

## 迁移策略

- 所有表结构变更通过 Alembic。
- 不直接在启动时隐式改表。
- 镜像升级前提示备份 `data/app.db`。

