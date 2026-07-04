# 前端设计

## 技术栈

```text
React + Vite + TypeScript
Tailwind CSS
shadcn/ui
TanStack Query
TanStack Router
Zod
```

## 产品气质

不是企业后台，而是个人媒体库工具。

界面关键词：

```text
移动端优先
安静
音乐感
文件管理清晰
任务状态明确
```

避免：

- 典型 SaaS 大卡片堆叠。
- Ant Design 式企业表格感。
- 过度渐变和装饰。
- 只适配桌面的左侧菜单后台。

## 页面结构

移动端使用底部导航：

```text
媒体
任务
账号
设置
```

桌面端使用窄侧栏：

```text
┌──────────┬────────────────────────┐
│ nav      │ content                │
│          │                        │
└──────────┴────────────────────────┘
```

## 页面清单

### 1. 登录页

- 密码输入。
- 登录按钮。
- 错误提示。

### 2. 媒体页

默认展示音频，因为最终目标是播放。

功能：

- 音频/视频切换。
- 搜索。
- 来源账号筛选。
- 作者筛选。
- 文件状态。
- 删除。
- 查看来源。

移动端布局：

```text
[搜索]
[音频 | 视频]
[筛选]

媒体条目
媒体条目
媒体条目
```

桌面端布局：

```text
工具栏
媒体表格 / 密集列表
详情抽屉
```

### 3. 任务页

- 当前下载任务。
- 历史任务。
- 失败任务重试。
- 任务日志摘要。

状态颜色要克制：

| 状态 | 视觉 |
|---|---|
| pending | neutral |
| running | accent |
| succeeded | green |
| failed | red |
| canceled | muted |

### 4. 账号页

- 账号列表。
- 新增账号。
- Cookie 编辑。
- 校验登录态。
- 启用/停用。
- 同步点赞/收藏。

Cookie 输入建议使用弹窗，不在列表页直接展示完整值。

### 5. 设置页

- 下载并发数。
- 文件命名规则。
- WebDAV 配置。
- 数据备份。
- 系统信息。

## 组件策略

使用 shadcn/ui 基础组件：

```text
Button
Input
Dialog
Drawer
Sheet
Tabs
Badge
Table
DropdownMenu
Toast
Progress
```

移动端关键组件：

- `Drawer`：媒体详情。
- `Sheet`：筛选。
- `Tabs`：音频/视频切换。
- `DropdownMenu`：条目操作。
- `Progress`：下载进度。

## 响应式规则

断点：

```text
sm: 640px
md: 768px
lg: 1024px
xl: 1280px
```

原则：

- 默认写移动端样式。
- `md` 以上增强桌面布局。
- 表格只用于桌面端。
- 移动端用列表，不横向滚动表格。
- 操作按钮使用图标 + tooltip，移动端保留文字。

## 数据请求

TanStack Query key 示例：

```text
["accounts"]
["media", filters]
["tasks", status]
["settings"]
```

规则：

- 列表接口分页。
- 任务页短轮询，默认 2-5 秒。
- 下载进度可后续切换 SSE/WebSocket。
- 修改操作成功后 invalidate 相关 query。

