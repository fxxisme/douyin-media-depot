import {
  createRootRoute,
  createRoute,
  createRouter,
  Link,
  Outlet,
  RouterProvider,
  useNavigate,
} from "@tanstack/react-router";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Database,
  Download,
  FileAudio,
  Film,
  HardDrive,
  Loader2,
  LogOut,
  RefreshCw,
  Search,
  ScrollText,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  UserRound,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { FormEvent, ReactNode, useMemo, useState } from "react";

import { api, ApiClientError } from "./api";
import type { Account, DownloadTask, MediaFile, SourceItem } from "./types";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 10_000,
    },
  },
});

const PAGE_SIZE = 24;

function CleanWorkbenchApp() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

function Root() {
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  if (me.isLoading) return <CenteredMessage text="正在连接媒体库" />;
  if (me.error instanceof ApiClientError && me.error.status === 401) return <LoginPage />;
  if (me.error) return <CenteredMessage text={errorMessage(me.error)} />;
  return <Shell />;
}

function Shell() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const logout = useMutation({
    mutationFn: api.logout,
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      void navigate({ to: "/media" });
    },
  });
  const nav = [
    { to: "/media", label: "素材", icon: Film },
    { to: "/tasks", label: "任务", icon: Clock3 },
    { to: "/logs", label: "执行日志", icon: ScrollText },
    { to: "/accounts", label: "账号", icon: UserRound },
    { to: "/settings", label: "系统", icon: Settings },
  ] as const;

  return (
    <div className="app-shell">
      <aside className="studio-rail">
        <Link to="/media" className="brand-lockup">
          <Archive size={19} />
          <span>Depot</span>
        </Link>
        <nav className="rail-nav">
          {nav.map((item) => (
          <Link key={item.to} to={item.to} className="rail-link" activeProps={{ className: "is-active" }} title={item.label}>
              <item.icon size={19} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <button className="rail-logout" onClick={() => logout.mutate()} title="退出登录">
          <LogOut size={18} />
        </button>
      </aside>
      <main className="studio-main">
        <Outlet />
      </main>
      <nav className="mobile-tabbar">
        {nav.map((item) => (
          <Link key={item.to} to={item.to} className="mobile-tab" activeProps={{ className: "is-active" }}>
            <item.icon size={19} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}

function LoginPage() {
  const [password, setPassword] = useState("");
  const queryClient = useQueryClient();
  const login = useMutation({
    mutationFn: api.login,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate(password);
  };

  return (
    <div className="login-screen">
      <form className="login-panel" onSubmit={onSubmit}>
        <div className="login-mark">
          <ShieldCheck size={22} />
        </div>
        <p className="eyebrow">Douyin Media Depot</p>
        <h1>素材调度台</h1>
        <p className="muted">输入管理密码后进入本地媒体库。</p>
        <label className="field-label">管理密码</label>
        <input className="input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoFocus />
        <ErrorLine error={login.error} />
        <button className="btn btn-primary w-full" disabled={!password || login.isPending}>
          {login.isPending && <Loader2 className="spin" size={16} />}
          登录
        </button>
      </form>
    </div>
  );
}

function MediaPage() {
  const [mediaType, setMediaType] = useState<"audio" | "video">("audio");
  const [keyword, setKeyword] = useState("");
  const [author, setAuthor] = useState("");
  const [accountId, setAccountId] = useState("");
  const [manualUrl, setManualUrl] = useState("");
  const [manualTitle, setManualTitle] = useState("");
  const [manualAccountId, setManualAccountId] = useState("");
  const [sourceDownloadedFilter, setSourceDownloadedFilter] = useState<"all" | "pending" | "downloaded">("pending");
  const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);
  const [mediaPage, setMediaPage] = useState(1);
  const [sourcePage, setSourcePage] = useState(1);
  const queryClient = useQueryClient();

  const accounts = useQuery({ queryKey: ["accounts"], queryFn: api.accounts });
  const media = useQuery({
    queryKey: ["media", mediaType, keyword, author, accountId, mediaPage],
    queryFn: () =>
      api.media({
        media_type: mediaType,
        keyword,
        author,
        account_id: accountId ? Number(accountId) : undefined,
        page: mediaPage,
        page_size: PAGE_SIZE,
      }),
  });
  const sources = useQuery({
    queryKey: ["sources", keyword, accountId, sourceDownloadedFilter, sourcePage],
    queryFn: () =>
      api.sources({
        keyword,
        account_id: accountId ? Number(accountId) : undefined,
        downloaded: sourceDownloadedFilter === "all" ? undefined : sourceDownloadedFilter === "downloaded",
        page: sourcePage,
        page_size: PAGE_SIZE,
      }),
  });
  const deleteMedia = useMutation({
    mutationFn: api.deleteMedia,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["media"] }),
  });
  const createTasks = useMutation({
    mutationFn: (sourceIds: number[]) => api.createTasks(sourceIds, mediaType),
    onSuccess: async () => {
      setSelectedSourceIds([]);
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["media"] });
    },
  });
  const createManualDownload = useMutation({
    mutationFn: async () => {
      const source = await api.createManualSource({
        account_id: Number(manualAccountId),
        url: manualUrl,
        title: manualTitle || undefined,
      });
      await api.createTasks([source.id], mediaType);
      return source;
    },
    onSuccess: async () => {
      setManualUrl("");
      setManualTitle("");
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      await queryClient.invalidateQueries({ queryKey: ["media"] });
    },
  });

  const visibleSources = sources.data?.items ?? [];
  const selectedSourceIdSet = useMemo(() => new Set(selectedSourceIds), [selectedSourceIds]);
  const selectableSourceIds = visibleSources.filter((source) => !source.downloaded).map((source) => source.id);
  const selectedCount = selectedSourceIds.length;
  const accountOptions = accounts.data ?? [];
  const resetPages = () => {
    setMediaPage(1);
    setSourcePage(1);
    setSelectedSourceIds([]);
  };
  const toggleSourceSelection = (sourceId: number) => {
    setSelectedSourceIds((ids) => (ids.includes(sourceId) ? ids.filter((id) => id !== sourceId) : [...ids, sourceId]));
  };
  const selectVisibleSources = () => {
    setSelectedSourceIds((ids) => Array.from(new Set([...ids, ...selectableSourceIds])));
  };

  return (
    <section className="workbench-page">
      <PageHeader eyebrow="Media bench" title="素材工作台" description="同步后的点赞或收藏先进入素材带，勾选后再下载视频或抽取音频。" />
      <div className="command-deck">
        <div className="search-pack">
          <Search size={17} />
          <input
            value={keyword}
            onChange={(event) => {
              setKeyword(event.target.value);
              resetPages();
            }}
            placeholder="搜索标题或文件名"
          />
        </div>
        <input
          className="input compact"
          value={author}
          onChange={(event) => {
            setAuthor(event.target.value);
            setMediaPage(1);
          }}
          placeholder="作者"
        />
        <select
          className="input compact"
          value={accountId}
          onChange={(event) => {
            setAccountId(event.target.value);
            resetPages();
          }}
        >
          <option value="">全部账号</option>
          {accountOptions.map((account) => (
            <option value={account.id} key={account.id}>
              {account.name}
            </option>
          ))}
        </select>
        <Segmented
          value={mediaType}
          options={[
            { value: "audio", label: "音频" },
            { value: "video", label: "视频" },
          ]}
          onChange={(value) => {
            setMediaType(value as "audio" | "video");
            setMediaPage(1);
          }}
        />
      </div>
      <form
        className="manual-strip"
        onSubmit={(event) => {
          event.preventDefault();
          createManualDownload.mutate();
        }}
      >
        <select className="input compact" value={manualAccountId} onChange={(event) => setManualAccountId(event.target.value)}>
          <option value="">手动链接账号</option>
          {accountOptions.map((account) => (
            <option value={account.id} key={account.id}>
              {account.name}
            </option>
          ))}
        </select>
        <input className="input compact wide" placeholder="粘贴抖音视频链接" value={manualUrl} onChange={(event) => setManualUrl(event.target.value)} />
        <input className="input compact" placeholder="标题，可选" value={manualTitle} onChange={(event) => setManualTitle(event.target.value)} />
        <button className="btn btn-copper" disabled={!manualAccountId || !manualUrl || createManualDownload.isPending}>
          {createManualDownload.isPending && <Loader2 className="spin" size={16} />}
          添加并下载
        </button>
        <ErrorLine error={createManualDownload.error} />
      </form>
      <div className="bench-grid">
        <section className="desk-panel source-panel">
          <PanelHeader icon={Film} title="可下载视频" meta={sources.data ? `${sources.data.total} 条` : undefined} />
          <div className="panel-toolbar">
            <Segmented
              value={sourceDownloadedFilter}
              options={[
                { value: "pending", label: "未下载" },
                { value: "downloaded", label: "已下载" },
                { value: "all", label: "全部" },
              ]}
              onChange={(value) => {
                setSourceDownloadedFilter(value as "all" | "pending" | "downloaded");
                setSourcePage(1);
                setSelectedSourceIds([]);
              }}
            />
            <div className="toolbar-actions">
              <button className="btn btn-small" type="button" disabled={!selectableSourceIds.length} onClick={selectVisibleSources}>
                全选未下载
              </button>
              <button className="btn btn-small" type="button" disabled={!selectedCount} onClick={() => setSelectedSourceIds([])}>
                清空
              </button>
              <button className="btn btn-primary btn-small" type="button" disabled={!selectedCount || createTasks.isPending} onClick={() => createTasks.mutate(selectedSourceIds)}>
                {createTasks.isPending && <Loader2 className="spin" size={15} />}
                下载所选{selectedCount ? `(${selectedCount})` : ""}
              </button>
            </div>
            <ErrorLine error={createTasks.error} />
          </div>
          {sources.isLoading ? (
            <LoadingBlock />
          ) : visibleSources.length ? (
            <>
              <div className="film-strip">
                {visibleSources.map((source) => (
                  <SourceRow
                    key={source.id}
                    source={source}
                    selected={selectedSourceIdSet.has(source.id)}
                    disabled={source.downloaded}
                    mediaType={mediaType}
                    pending={createTasks.isPending}
                    onToggle={() => toggleSourceSelection(source.id)}
                    onDownload={() => createTasks.mutate([source.id])}
                  />
                ))}
              </div>
              <Pager
                page={sources.data.page}
                pageSize={sources.data.page_size}
                total={sources.data.total}
                onPageChange={setSourcePage}
              />
            </>
          ) : (
            <EmptyState text="暂无来源。先到账号页同步点赞或收藏。" />
          )}
        </section>
        <section className="desk-panel library-panel">
          <PanelHeader icon={mediaType === "audio" ? FileAudio : HardDrive} title={mediaType === "audio" ? "本地音频" : "本地视频"} meta={media.data ? `${media.data.total} 个文件` : undefined} />
          {media.isLoading ? (
            <LoadingBlock />
          ) : media.data?.items.length ? (
            <>
              <div className="media-ledger">
                {media.data.items.map((item) => (
                  <MediaRow key={item.id} item={item} onDelete={() => deleteMedia.mutate(item.id)} />
                ))}
              </div>
              <Pager page={media.data.page} pageSize={media.data.page_size} total={media.data.total} onPageChange={setMediaPage} />
            </>
          ) : (
            <EmptyState text="还没有本地媒体文件。" />
          )}
        </section>
      </div>
    </section>
  );
}

function SourceRow({
  source,
  selected,
  disabled,
  mediaType,
  pending,
  onToggle,
  onDownload,
}: {
  source: SourceItem;
  selected: boolean;
  disabled: boolean;
  mediaType: "audio" | "video";
  pending: boolean;
  onToggle: () => void;
  onDownload: () => void;
}) {
  return (
    <article className={`source-row ${source.downloaded ? "is-downloaded" : ""}`}>
      <label className="source-check">
        <input type="checkbox" checked={selected} disabled={disabled} onChange={onToggle} aria-label={`选择 ${source.title ?? source.platform_item_id}`} />
      </label>
      <div className="thumb-frame">{source.cover_url ? <img src={source.cover_url} alt="" loading="lazy" /> : <Film size={20} />}</div>
      <div className="source-copy">
        <div className="source-title-line">
          <h3 title={source.title ?? source.platform_item_id}>{source.title ?? source.platform_item_id}</h3>
          <StatusPill status={source.downloaded ? "已下载" : "未下载"} tone={source.downloaded ? "good" : "neutral"} />
        </div>
        <p>
          {source.author_name ?? "未知作者"} · {sourceTypeLabel(source.source_type)}
        </p>
        <button className="btn btn-small" type="button" disabled={source.downloaded || pending} onClick={onDownload}>
          <Download size={15} />
          下载{mediaType === "audio" ? "音频" : "视频"}
        </button>
      </div>
    </article>
  );
}

function MediaRow({ item, onDelete }: { item: MediaFile; onDelete: () => void }) {
  return (
    <article className="media-row">
      <div className="media-glyph">{item.media_type === "audio" ? <FileAudio size={18} /> : <Film size={18} />}</div>
      <div className="media-copy">
        <h3 title={item.source_title ?? item.filename}>{item.source_title ?? item.filename}</h3>
        <p>
          {item.source_author ?? "未知作者"} · {item.file_size ? formatBytes(item.file_size) : "未知大小"}
        </p>
        <p className="path-text" title={item.relative_path}>
          {item.relative_path}
        </p>
      </div>
      <button className="icon-danger" title="删除文件" onClick={onDelete}>
        <Trash2 size={16} />
      </button>
    </article>
  );
}

function TasksPage() {
  const [status, setStatus] = useState("");
  const queryClient = useQueryClient();
  const tasks = useQuery({
    queryKey: ["tasks", status],
    queryFn: () => api.tasks(status || undefined),
    refetchInterval: 4000,
  });
  const retry = useMutation({ mutationFn: api.retryTask, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }) });
  const cancel = useMutation({ mutationFn: api.cancelTask, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }) });

  return (
    <section className="workbench-page">
      <PageHeader eyebrow="Transfer queue" title="下载任务" description="查看正在处理的下载、抽音频和失败原因。" />
      <div className="status-strip">
        {["", "pending", "running", "succeeded", "failed", "canceled"].map((item) => (
          <button key={item || "all"} className={`chip ${status === item ? "is-active" : ""}`} onClick={() => setStatus(item)}>
            {taskStatusLabel(item)}
          </button>
        ))}
      </div>
      <section className="desk-panel">
        {tasks.isLoading ? (
          <LoadingBlock />
        ) : tasks.data?.items.length ? (
          <div className="task-list">
            {tasks.data.items.map((task) => (
              <TaskRow key={task.id} task={task} onRetry={() => retry.mutate(task.id)} onCancel={() => cancel.mutate(task.id)} />
            ))}
          </div>
        ) : (
          <EmptyState text="暂无下载任务。" />
        )}
      </section>
    </section>
  );
}

function LogsPage() {
  const [status, setStatus] = useState("");
  const logs = useQuery({
    queryKey: ["task-logs", status],
    queryFn: () => api.tasks(status || undefined),
    refetchInterval: 4000,
  });

  return (
    <section className="workbench-page">
      <PageHeader eyebrow="Execution log" title="执行日志" description="查看任务卡住、失败、取消和下载链路的错误来源。" />
      <div className="status-strip">
        {["", "pending", "running", "succeeded", "failed", "canceled"].map((item) => (
          <button key={item || "all"} className={`chip ${status === item ? "is-active" : ""}`} onClick={() => setStatus(item)}>
            {taskStatusLabel(item)}
          </button>
        ))}
      </div>
      <section className="desk-panel">
        {logs.isLoading ? (
          <LoadingBlock />
        ) : logs.data?.items.length ? (
          <div className="log-list">
            {logs.data.items.map((task) => (
              <TaskLogRow key={task.id} task={task} />
            ))}
          </div>
        ) : (
          <EmptyState text="暂无执行日志。" />
        )}
      </section>
    </section>
  );
}

function AccountsPage() {
  const [name, setName] = useState("");
  const [cookie, setCookie] = useState("");
  const [secUserId, setSecUserId] = useState("");
  const [editingId, setEditingId] = useState("");
  const [showCookieGuide, setShowCookieGuide] = useState(false);
  const queryClient = useQueryClient();
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: api.accounts });
  const selected = useMemo(() => accounts.data?.find((item) => String(item.id) === editingId), [accounts.data, editingId]);
  const cookieCheck = useMemo(() => inspectCookie(cookie), [cookie]);
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["accounts"] });
  const save = useMutation({
    mutationFn: () =>
      selected ? api.updateAccount(selected.id, { name, cookie, sec_user_id: secUserId }) : api.createAccount({ name, cookie, sec_user_id: secUserId }),
    onSuccess: () => {
      setName("");
      setCookie("");
      setSecUserId("");
      setEditingId("");
      invalidate();
    },
  });
  const verify = useMutation({ mutationFn: api.verifyAccount, onSuccess: invalidate });
  const sync = useMutation({ mutationFn: ({ id, sourceType }: { id: number; sourceType: "liked" | "favorite" }) => api.syncAccount(id, sourceType), onSuccess: invalidate });
  const toggle = useMutation({ mutationFn: (account: Account) => api.updateAccount(account.id, { enabled: !account.enabled }), onSuccess: invalidate });
  const remove = useMutation({ mutationFn: api.deleteAccount, onSuccess: invalidate });

  const onEditChange = (value: string) => {
    setEditingId(value);
    const account = accounts.data?.find((item) => String(item.id) === value);
    setName(account?.name ?? "");
    setCookie("");
    setSecUserId(account?.sec_user_id ?? "");
  };

  return (
    <section className="workbench-page">
      <PageHeader eyebrow="Identity" title="账号与同步" description="账号负责拉取点赞、收藏列表；Cookie 和 sec_user_id 都需要填写。" />
      <div className="account-grid">
        <form
          className="desk-panel form-panel"
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
        >
          <PanelHeader icon={UserRound} title={selected ? "编辑账号" : "新增账号"} />
          <button className="btn btn-small" type="button" onClick={() => setShowCookieGuide((value) => !value)}>
            <ShieldCheck size={15} />
            获取 Cookie 指引
          </button>
          {showCookieGuide && <CookieGuide />}
          <Field label="选择账号">
            <select className="input" value={editingId} onChange={(event) => onEditChange(event.target.value)}>
              <option value="">新增账号</option>
              {(accounts.data ?? []).map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="账号名称">
            <input className="input" value={name} onChange={(event) => setName(event.target.value)} placeholder="我的抖音" />
          </Field>
          <Field label="sec_user_id">
            <input className="input mono" value={secUserId} onChange={(event) => setSecUserId(event.target.value)} placeholder="MS4wLjABAAAA..." />
          </Field>
          <Field label="Cookie">
            <textarea className="textarea mono" value={cookie} onChange={(event) => setCookie(event.target.value)} placeholder="sessionid=..." />
          </Field>
          <CookieCheckView result={cookieCheck} />
          <ErrorLine error={save.error ?? verify.error ?? sync.error ?? toggle.error ?? remove.error} />
          <button className="btn btn-primary w-full" disabled={!name || !cookie || !secUserId || save.isPending}>
            保存账号
          </button>
        </form>
        <section className="desk-panel">
          <PanelHeader icon={Database} title="账号列表" meta={`${accounts.data?.length ?? 0} 个`} />
          {accounts.isLoading ? (
            <LoadingBlock />
          ) : accounts.data?.length ? (
            <div className="account-list">
              {accounts.data.map((account) => (
                <AccountRow
                  key={account.id}
                  account={account}
                  onVerify={() => verify.mutate(account.id)}
                  onSyncLiked={() => sync.mutate({ id: account.id, sourceType: "liked" })}
                  onSyncFavorite={() => sync.mutate({ id: account.id, sourceType: "favorite" })}
                  onToggle={() => toggle.mutate(account)}
                  onDelete={() => remove.mutate(account.id)}
                />
              ))}
            </div>
          ) : (
            <EmptyState text="还没有账号。" />
          )}
        </section>
      </div>
    </section>
  );
}

function AccountRow({
  account,
  onVerify,
  onSyncLiked,
  onSyncFavorite,
  onToggle,
  onDelete,
}: {
  account: Account;
  onVerify: () => void;
  onSyncLiked: () => void;
  onSyncFavorite: () => void;
  onToggle: () => void;
  onDelete: () => void;
}) {
  return (
    <article className="account-row">
      <div>
        <div className="row-title-line">
          <h3>{account.name}</h3>
          <StatusBadge status={account.status} />
        </div>
        <p>{account.slug}</p>
        <p className="mono small-text">sec_user_id: {account.sec_user_id || "未填写"}</p>
      </div>
      <div className="row-actions">
        <button className="btn btn-small" onClick={onVerify}>
          <CheckCircle2 size={15} />
          校验
        </button>
        <button className="btn btn-small" onClick={onSyncLiked}>
          同步点赞
        </button>
        <button className="btn btn-small" onClick={onSyncFavorite}>
          同步收藏
        </button>
        <button className="btn btn-small" onClick={onToggle}>
          {account.enabled ? "停用" : "启用"}
        </button>
        <button className="icon-danger" onClick={onDelete} title="删除账号">
          <Trash2 size={16} />
        </button>
      </div>
    </article>
  );
}

function SettingsPage() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const [concurrency, setConcurrency] = useState("2");
  const update = useMutation({
    mutationFn: () => api.updateSettings({ max_concurrent_downloads: Number(concurrency), audio_extract_mode: "copy" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });
  const data = settings.data;

  return (
    <section className="workbench-page">
      <PageHeader eyebrow="Machine room" title="系统设置" description="控制下载并发和确认本机运行能力。" />
      <div className="account-grid">
        <form
          className="desk-panel form-panel"
          onSubmit={(event) => {
            event.preventDefault();
            update.mutate();
          }}
        >
          <PanelHeader icon={SlidersHorizontal} title="下载设置" />
          <Field label="下载并发">
            <input className="input" type="number" min={1} max={8} value={concurrency} onChange={(event) => setConcurrency(event.target.value)} />
          </Field>
          <p className="muted">音频抽取固定为 copy，不主动重编码。</p>
          <ErrorLine error={update.error} />
          <button className="btn btn-primary w-full">保存设置</button>
        </form>
        <section className="desk-panel">
          <PanelHeader icon={HardDrive} title="运行信息" />
          {settings.isLoading ? (
            <LoadingBlock />
          ) : data ? (
            <dl className="info-grid">
              <InfoRow label="环境" value={data.app_env} />
              <InfoRow label="数据目录" value={data.data_dir} />
              <InfoRow label="下载目录" value={data.download_dir} />
              <InfoRow label="临时目录" value={data.temp_dir} />
              <InfoRow label="ffmpeg" value={data.ffmpeg_available ? "可用" : "未找到"} />
              <InfoRow label="ffprobe" value={data.ffprobe_available ? "可用" : "未找到"} />
              <InfoRow label="WebDAV" value={data.webdav_enabled ? data.webdav_url : "未启用"} />
            </dl>
          ) : (
            <EmptyState text="无法读取设置。" />
          )}
        </section>
      </div>
    </section>
  );
}

function TaskLogRow({ task }: { task: DownloadTask }) {
  return (
    <article className="log-card">
      <div className="row-title-line">
        <div>
          <h3>{task.source_title ?? `来源 #${task.source_item_id}`}</h3>
          <p>
            {downloadTypeLabel(task.download_type)} · {task.source_author ?? "未知作者"}
          </p>
        </div>
        <StatusBadge status={task.status} />
      </div>
      <div className="log-meta">
        <span>创建：{formatDateTime(task.created_at)}</span>
        <span>开始：{formatDateTime(task.started_at)}</span>
        <span>结束：{formatDateTime(task.finished_at)}</span>
        <span>更新：{formatDateTime(task.updated_at)}</span>
      </div>
      <div className="progress-track">
        <span style={{ width: `${task.progress}%` }} />
      </div>
      <p className="log-source">来源判断：{taskErrorSource(task.error_code)}</p>
      {task.error_code && <p className="mono small-text">error_code: {task.error_code}</p>}
      {task.error_message && <p className="error-box">{task.error_message}</p>}
      {task.stderr_tail && <pre className="log-tail">{task.stderr_tail}</pre>}
    </article>
  );
}

function TaskRow({ task, onRetry, onCancel }: { task: DownloadTask; onRetry: () => void; onCancel: () => void }) {
  return (
    <article className="task-row">
      <div>
        <div className="row-title-line">
          <h3>{task.source_title ?? `来源 #${task.source_item_id}`}</h3>
          <StatusBadge status={task.status} />
        </div>
        <p>
          {downloadTypeLabel(task.download_type)} · {task.source_author ?? "未知作者"}
        </p>
      </div>
      <div className="progress-track">
        <span style={{ width: `${task.progress}%` }} />
      </div>
      {task.error_message && <p className="error-box">{task.error_message}</p>}
      <div className="row-actions">
        {task.status === "failed" && (
          <button className="btn btn-small" onClick={onRetry}>
            <RefreshCw size={15} />
            重试
          </button>
        )}
        {(task.status === "pending" || task.status === "running") && (
          <button className="btn btn-small" onClick={onCancel}>
            取消
          </button>
        )}
      </div>
    </article>
  );
}

function CookieGuide() {
  return (
    <div className="note-box">
      <p>打开抖音网页版并登录，进入浏览器开发者工具的 Network 面板。</p>
      <p>刷新页面，选择任意 douyin.com 请求，复制 Request Headers 里的 Cookie。</p>
      <p>同一个请求的 URL、Payload 或响应里通常能找到 sec_user_id。</p>
    </div>
  );
}

function CookieCheckView({ result }: { result: ReturnType<typeof inspectCookie> }) {
  return (
    <div className={`cookie-check ${result.level}`}>
      <p>{result.message}</p>
      <span>sessionid: {result.hasSessionid ? "已检测" : "缺少"}</span>
      <span>sid_guard: {result.hasSidGuard ? "已检测" : "缺少"}</span>
    </div>
  );
}

function inspectCookie(value: string) {
  const trimmed = value.trim();
  const hasCookieShape = /(^|;\s*)[A-Za-z0-9_.-]+=/.test(trimmed);
  const hasSessionid = /(^|;\s*)sessionid=/.test(trimmed);
  const hasSidGuard = /(^|;\s*)sid_guard=/.test(trimmed);
  if (!trimmed) return { level: "empty", message: "粘贴 Cookie 后会自动检查关键字段。", hasSessionid, hasSidGuard };
  if (!hasCookieShape) return { level: "bad", message: "这段内容看起来不像 Cookie。", hasSessionid, hasSidGuard };
  if (hasSessionid && hasSidGuard) return { level: "good", message: "格式看起来可用，保存后再校验。", hasSessionid, hasSidGuard };
  return { level: "warn", message: "缺少关键字段，后续校验可能失败。", hasSessionid, hasSidGuard };
}

function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="page-header">
      <p>{eyebrow}</p>
      <h1>{title}</h1>
      <span>{description}</span>
    </header>
  );
}

function PanelHeader({ icon: Icon, title, meta }: { icon: LucideIcon; title: string; meta?: string }) {
  return (
    <div className="panel-header">
      <div>
        <Icon size={18} />
        <h2>{title}</h2>
      </div>
      {meta && <span>{meta}</span>}
    </div>
  );
}

function Segmented({ value, options, onChange }: { value: string; options: { value: string; label: string }[]; onChange: (value: string) => void }) {
  return (
    <div className="segmented">
      {options.map((option) => (
        <button key={option.value} className={value === option.value ? "is-active" : ""} type="button" onClick={() => onChange(option.value)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function StatusPill({ status, tone = "neutral" }: { status: string; tone?: "neutral" | "good" | "bad" | "live" }) {
  return <span className={`status-pill ${tone}`}>{status}</span>;
}

function StatusBadge({ status }: { status: string }) {
  const tone = status === "active" || status === "succeeded" ? "good" : status === "failed" || status === "invalid" || status === "expired" ? "bad" : status === "running" ? "live" : "neutral";
  return <StatusPill status={statusLabel(status)} tone={tone} />;
}

function Pager({ page, pageSize, total, onPageChange }: { page: number; pageSize: number; total: number; onPageChange: (page: number) => void }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);
  return (
    <div className="pager">
      <span>
        {start}-{end} / {total}
      </span>
      <div>
        <button className="btn btn-small" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          上一页
        </button>
        <button className="btn btn-small" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          下一页
        </button>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="info-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function ErrorLine({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p className="error-line">
      <CircleAlert size={15} />
      {errorMessage(error)}
    </p>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function LoadingBlock() {
  return (
    <div className="loading-block">
      <Loader2 className="spin" size={17} />
      加载中
    </div>
  );
}

function CenteredMessage({ text }: { text: string }) {
  return <div className="center-message">{text}</div>;
}

function sourceTypeLabel(value: SourceItem["source_type"]) {
  if (value === "liked") return "点赞";
  if (value === "favorite") return "收藏";
  return "手动";
}

function downloadTypeLabel(value: DownloadTask["download_type"]) {
  if (value === "audio") return "音频";
  if (value === "video") return "视频";
  return "视频 + 音频";
}

function taskErrorSource(code: string | null) {
  if (!code) return "暂无错误信息";
  if (code === "task_canceled") return "用户取消";
  if (code === "service_restarted") return "服务重启";
  if (code === "unexpected_error") return "程序异常";
  if (code.endsWith("_timeout")) return "超时";
  if (code.startsWith("account_") || code.startsWith("douyin_") || code === "sec_user_id_required") return "抖音接口 / Cookie";
  if (code.startsWith("download_")) return "网络下载";
  if (code.startsWith("yt_dlp_")) return "yt-dlp";
  if (code.startsWith("audio_extract_")) return "ffmpeg";
  return "其他错误";
}

function formatDateTime(value: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function taskStatusLabel(value: string) {
  if (!value) return "全部";
  if (value === "pending") return "等待中";
  if (value === "running") return "运行中";
  if (value === "succeeded") return "已完成";
  if (value === "failed") return "失败";
  if (value === "canceled") return "已取消";
  return value;
}

function statusLabel(value: string) {
  if (value === "active") return "正常";
  if (value === "expired") return "过期";
  if (value === "invalid") return "无效";
  if (value === "disabled") return "停用";
  return taskStatusLabel(value);
}

function formatBytes(value: number) {
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function errorMessage(error: unknown) {
  if (error instanceof ApiClientError) return error.message;
  if (error instanceof Error) return error.message;
  return "操作失败";
}

const rootRoute = createRootRoute({ component: Root });
const mediaRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", component: MediaPage });
const mediaAliasRoute = createRoute({ getParentRoute: () => rootRoute, path: "/media", component: MediaPage });
const tasksRoute = createRoute({ getParentRoute: () => rootRoute, path: "/tasks", component: TasksPage });
const logsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/logs", component: LogsPage });
const accountsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/accounts", component: AccountsPage });
const settingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings", component: SettingsPage });
const routeTree = rootRoute.addChildren([mediaRoute, mediaAliasRoute, tasksRoute, logsRoute, accountsRoute, settingsRoute]);
const router = createRouter({ routeTree, defaultPreload: "intent" });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export default CleanWorkbenchApp;
