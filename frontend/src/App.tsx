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
  CircleHelp,
  CircleAlert,
  Database,
  Download,
  FileAudio,
  ListMusic,
  Loader2,
  LogOut,
  MoreHorizontal,
  RefreshCw,
  Settings,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { api, ApiClientError } from "./api";
import type { Account, DownloadTask } from "./types";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 10_000,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

function Root() {
  const me = useQuery({ queryKey: ["me"], queryFn: api.me });
  if (me.isLoading) {
    return <CenteredMessage text="正在连接媒体库" />;
  }
  if (me.error instanceof ApiClientError && me.error.status === 401) {
    return <LoginPage />;
  }
  if (me.error) {
    return <CenteredMessage text={errorMessage(me.error)} />;
  }
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
    { to: "/media", label: "媒体", icon: ListMusic },
    { to: "/tasks", label: "任务", icon: Download },
    { to: "/accounts", label: "账号", icon: UserRound },
    { to: "/settings", label: "设置", icon: Settings },
  ] as const;

  return (
    <div className="min-h-screen bg-paper text-ink">
      <div className="mx-auto flex min-h-screen max-w-7xl">
        <aside className="hidden w-20 border-r border-line bg-white/80 md:flex md:flex-col md:items-center md:py-5">
          <div className="mb-7 grid h-11 w-11 place-items-center rounded-md bg-ink text-white">
            <Archive size={22} />
          </div>
          <nav className="flex flex-1 flex-col gap-2">
            {nav.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="grid h-12 w-12 place-items-center rounded-md text-ink/60 transition hover:bg-paper hover:text-ink [&.active]:bg-lake [&.active]:text-white"
                title={item.label}
              >
                <item.icon size={20} />
              </Link>
            ))}
          </nav>
          <button className="btn h-12 w-12 px-0" onClick={() => logout.mutate()} title="退出登录">
            <LogOut size={18} />
          </button>
        </aside>
        <main className="w-full px-4 pb-24 pt-4 md:px-8 md:pb-10 md:pt-8">
          <Outlet />
        </main>
        <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t border-line bg-white md:hidden">
          {nav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="flex h-16 flex-col items-center justify-center gap-1 text-xs text-ink/60 [&.active]:text-lake"
            >
              <item.icon size={20} />
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
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
    <div className="grid min-h-screen place-items-center bg-paper px-4 text-ink">
      <form className="panel w-full max-w-sm p-5" onSubmit={onSubmit}>
        <div className="mb-6 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-md bg-lake text-white">
            <ShieldCheck size={21} />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Douyin Media Depot</h1>
            <p className="text-sm text-ink/55">输入管理员密码进入媒体库</p>
          </div>
        </div>
        <label className="mb-2 block text-sm font-medium">管理员密码</label>
        <input className="input" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoFocus />
        <ErrorLine error={login.error} />
        <button className="btn btn-primary mt-4 w-full" disabled={!password || login.isPending}>
          {login.isPending && <Loader2 className="animate-spin" size={16} />}
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
  const queryClient = useQueryClient();
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: api.accounts });
  const media = useQuery({
    queryKey: ["media", mediaType, keyword, author, accountId],
    queryFn: () => api.media({ media_type: mediaType, keyword, author, account_id: accountId ? Number(accountId) : undefined }),
  });
  const sources = useQuery({
    queryKey: ["sources", keyword, accountId, sourceDownloadedFilter],
    queryFn: () =>
      api.sources({
        keyword,
        account_id: accountId ? Number(accountId) : undefined,
        downloaded: sourceDownloadedFilter === "all" ? undefined : sourceDownloadedFilter === "downloaded",
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
      await api.createTasks([source.id], "video");
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
  const toggleSourceSelection = (sourceId: number) => {
    setSelectedSourceIds((ids) => (ids.includes(sourceId) ? ids.filter((id) => id !== sourceId) : [...ids, sourceId]));
  };

  return (
    <section>
      <PageHeader title="媒体" description="默认看音频；来源列表用于把已同步条目加入下载任务。" />
      <form
        className="panel mb-4 grid gap-3 p-4 md:grid-cols-[180px_1fr_180px_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          createManualDownload.mutate();
        }}
      >
        <select className="input" value={manualAccountId} onChange={(event) => setManualAccountId(event.target.value)}>
          <option value="">选择账号</option>
          {(accounts.data ?? []).map((account) => (
            <option value={account.id} key={account.id}>
              {account.name}
            </option>
          ))}
        </select>
        <input className="input" placeholder="粘贴抖音视频链接" value={manualUrl} onChange={(event) => setManualUrl(event.target.value)} />
        <input className="input" placeholder="标题，可选" value={manualTitle} onChange={(event) => setManualTitle(event.target.value)} />
        <button className="btn btn-primary" disabled={!manualAccountId || !manualUrl || createManualDownload.isPending}>
          {createManualDownload.isPending && <Loader2 className="animate-spin" size={16} />}
          添加并下载
        </button>
        {createManualDownload.error && <div className="md:col-span-4"><ErrorLine error={createManualDownload.error} /></div>}
      </form>
      <div className="mb-4 grid gap-3 md:grid-cols-[1fr_160px_160px_160px]">
        <input className="input" placeholder="搜索标题或文件名" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
        <input className="input" placeholder="作者" value={author} onChange={(event) => setAuthor(event.target.value)} />
        <select className="input" value={accountId} onChange={(event) => setAccountId(event.target.value)}>
          <option value="">全部账号</option>
          {(accounts.data ?? []).map((account) => (
            <option value={account.id} key={account.id}>
              {account.name}
            </option>
          ))}
        </select>
        <div className="grid grid-cols-2 rounded-md border border-line bg-white p-1">
          <button className={`rounded px-3 text-sm ${mediaType === "audio" ? "bg-lake text-white" : ""}`} onClick={() => setMediaType("audio")}>
            音频
          </button>
          <button className={`rounded px-3 text-sm ${mediaType === "video" ? "bg-lake text-white" : ""}`} onClick={() => setMediaType("video")}>
            视频
          </button>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="panel overflow-hidden">
          <SectionTitle icon={mediaType === "audio" ? FileAudio : Database} title={mediaType === "audio" ? "音频文件" : "视频文件"} />
          {media.isLoading ? (
            <LoadingRow />
          ) : media.data?.items.length ? (
            <div className="divide-y divide-line">
              {media.data.items.map((item) => (
                <div className="flex items-center justify-between gap-3 p-4" key={item.id}>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{item.source_title ?? item.filename}</p>
                    <p className="truncate text-sm text-ink/55">
                      {item.source_author ?? "未知作者"} · {item.codec_name ?? "未知编码"} · {item.relative_path}
                    </p>
                  </div>
                  <button className="btn btn-danger h-9 px-2" title="删除文件" onClick={() => deleteMedia.mutate(item.id)}>
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState text="还没有本地媒体文件" />
          )}
        </div>
        <div className="panel overflow-hidden">
          <div className="border-b border-line p-4">
            <div className="flex items-center gap-2">
              <MoreHorizontal size={18} className="text-lake" />
              <h2 className="font-semibold">可下载视频</h2>
            </div>
            <div className="mt-3 grid grid-cols-3 rounded-md border border-line bg-paper p-1">
              {[
                ["pending", "未下载"],
                ["downloaded", "已下载"],
                ["all", "全部"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={`rounded px-2 py-1 text-sm ${sourceDownloadedFilter === value ? "bg-lake text-white" : "text-ink/65"}`}
                  onClick={() => {
                    setSourceDownloadedFilter(value as "all" | "pending" | "downloaded");
                    setSelectedSourceIds([]);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn h-9" disabled={!selectableSourceIds.length} onClick={() => setSelectedSourceIds(selectableSourceIds)}>
                全选未下载
              </button>
              <button className="btn h-9" disabled={!selectedCount} onClick={() => setSelectedSourceIds([])}>
                清空
              </button>
              <button className="btn btn-primary h-9" disabled={!selectedCount || createTasks.isPending} onClick={() => createTasks.mutate(selectedSourceIds)}>
                {createTasks.isPending && <Loader2 className="animate-spin" size={16} />}
                下载所选 {selectedCount ? `(${selectedCount})` : ""}
              </button>
            </div>
            <ErrorLine error={createTasks.error} />
          </div>
          {sources.isLoading ? (
            <LoadingRow />
          ) : visibleSources.length ? (
            <div className="divide-y divide-line">
              {visibleSources.map((source) => (
                <div className="grid grid-cols-[auto_1fr] gap-3 p-4" key={source.id}>
                  <input
                    className="mt-1 h-4 w-4"
                    type="checkbox"
                    checked={selectedSourceIdSet.has(source.id)}
                    disabled={source.downloaded}
                    onChange={() => toggleSourceSelection(source.id)}
                    aria-label={`选择 ${source.title ?? source.platform_item_id}`}
                  />
                  <div className="min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className="line-clamp-2 font-medium">{source.title ?? source.platform_item_id}</p>
                      <span
                        className={`badge shrink-0 ${
                          source.downloaded ? "border-green-600/25 bg-green-600/10 text-green-700" : "border-line bg-paper text-ink/60"
                        }`}
                      >
                        {source.downloaded ? "已下载" : "未下载"}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-sm text-ink/55">
                      {source.author_name ?? "未知作者"} · {source.source_type === "liked" ? "点赞" : source.source_type === "favorite" ? "收藏" : "手动"}
                    </p>
                    <button className="btn mt-3 h-9" disabled={source.downloaded || createTasks.isPending} onClick={() => createTasks.mutate([source.id])}>
                      <Download size={16} />
                      下载{mediaType === "audio" ? "音频" : "视频"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState text="暂无来源条目。先到账号页触发同步。" />
          )}
        </div>
      </div>
    </section>
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
    <section>
      <PageHeader title="任务" description="下载队列和失败原因集中在这里。" />
      <div className="mb-4 flex gap-2 overflow-x-auto">
        {["", "pending", "running", "succeeded", "failed", "canceled"].map((item) => (
          <button key={item || "all"} className={`btn h-9 whitespace-nowrap ${status === item ? "btn-primary" : ""}`} onClick={() => setStatus(item)}>
            {item || "全部"}
          </button>
        ))}
      </div>
      <div className="panel overflow-hidden">
        {tasks.isLoading ? (
          <LoadingRow />
        ) : tasks.data?.items.length ? (
          <div className="divide-y divide-line">
            {tasks.data.items.map((task) => (
              <TaskRow key={task.id} task={task} onRetry={() => retry.mutate(task.id)} onCancel={() => cancel.mutate(task.id)} />
            ))}
          </div>
        ) : (
          <EmptyState text="暂无下载任务" />
        )}
      </div>
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
      selected
        ? api.updateAccount(selected.id, { name, cookie, sec_user_id: secUserId })
        : api.createAccount({ name, cookie, sec_user_id: secUserId }),
    onSuccess: () => {
      setName("");
      setCookie("");
      setSecUserId("");
      setEditingId("");
      invalidate();
    },
  });
  const verify = useMutation({ mutationFn: api.verifyAccount, onSuccess: invalidate });
  const sync = useMutation({
    mutationFn: ({ id, sourceType }: { id: number; sourceType: "liked" | "favorite" }) => api.syncAccount(id, sourceType),
    onSuccess: invalidate,
  });
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
    <section>
      <PageHeader title="账号" description="Cookie 只在新增或更新时传输，列表不会展示明文。" />
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <form
          className="panel p-4"
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
        >
          <SectionTitle icon={UserRound} title={selected ? "编辑账号" : "新增账号"} compact />
          <button className="btn mb-4 h-9 w-full" type="button" onClick={() => setShowCookieGuide((value) => !value)}>
            <CircleHelp size={16} />
            获取 Cookie 指引
          </button>
          {showCookieGuide && <CookieGuide />}
          <label className="mb-2 block text-sm font-medium">选择已有账号</label>
          <select className="input mb-3" value={editingId} onChange={(event) => onEditChange(event.target.value)}>
            <option value="">新增账号</option>
            {(accounts.data ?? []).map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
          <label className="mb-2 block text-sm font-medium">账号名称</label>
          <input className="input mb-3" value={name} onChange={(event) => setName(event.target.value)} placeholder="我的抖音" />
          <label className="mb-2 block text-sm font-medium">sec_user_id</label>
          <input className="input mb-3" value={secUserId} onChange={(event) => setSecUserId(event.target.value)} placeholder="MS4wLjABAAAA..." />
          <label className="mb-2 block text-sm font-medium">Cookie</label>
          <textarea className="textarea" value={cookie} onChange={(event) => setCookie(event.target.value)} placeholder="sessionid=..." />
          <CookieCheckView result={cookieCheck} />
          <ErrorLine error={save.error ?? verify.error ?? sync.error ?? toggle.error ?? remove.error} />
          <button className="btn btn-primary mt-4 w-full" disabled={!name || !cookie || !secUserId || save.isPending}>
            保存
          </button>
        </form>
        <div className="panel overflow-hidden">
          <SectionTitle icon={Database} title="账号列表" />
          {accounts.isLoading ? (
            <LoadingRow />
          ) : accounts.data?.length ? (
            <div className="divide-y divide-line">
              {accounts.data.map((account) => (
                <div className="p-4" key={account.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{account.name}</p>
                      <p className="text-sm text-ink/55">{account.slug}</p>
                      <p className="mt-1 max-w-md truncate text-xs text-ink/45">sec_user_id: {account.sec_user_id || "未填写"}</p>
                    </div>
                    <StatusBadge status={account.status} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button className="btn h-9" onClick={() => verify.mutate(account.id)}>
                      <CheckCircle2 size={16} />
                      校验
                    </button>
                    <button className="btn h-9" onClick={() => sync.mutate({ id: account.id, sourceType: "liked" })}>
                      同步点赞
                    </button>
                    <button className="btn h-9" onClick={() => sync.mutate({ id: account.id, sourceType: "favorite" })}>
                      同步收藏
                    </button>
                    <button className="btn h-9" onClick={() => toggle.mutate(account)}>
                      {account.enabled ? "停用" : "启用"}
                    </button>
                    <button className="btn btn-danger h-9" onClick={() => remove.mutate(account.id)}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState text="还没有账号" />
          )}
        </div>
      </div>
    </section>
  );
}

function inspectCookie(value: string) {
  const trimmed = value.trim();
  const hasCookieShape = /(^|;\s*)[A-Za-z0-9_.-]+=/.test(trimmed);
  const hasSessionid = /(^|;\s*)sessionid=/.test(trimmed);
  const hasSidGuard = /(^|;\s*)sid_guard=/.test(trimmed);
  if (!trimmed) {
    return { level: "empty", message: "粘贴 Cookie 后会自动检查关键字段。", hasSessionid, hasSidGuard };
  }
  if (!hasCookieShape) {
    return { level: "bad", message: "这段内容看起来不像 Cookie。", hasSessionid, hasSidGuard };
  }
  if (hasSessionid && hasSidGuard) {
    return { level: "good", message: "格式看起来可用，建议保存后再点校验。", hasSessionid, hasSidGuard };
  }
  return { level: "warn", message: "缺少关键字段，允许保存，但后续校验可能失败。", hasSessionid, hasSidGuard };
}

function CookieCheckView({ result }: { result: ReturnType<typeof inspectCookie> }) {
  const tone =
    result.level === "good"
      ? "border-green-600/20 bg-green-600/10 text-green-700"
      : result.level === "bad"
        ? "border-ember/20 bg-ember/10 text-ember"
        : "border-line bg-paper text-ink/65";
  return (
    <div className={`mt-3 rounded-md border px-3 py-2 text-sm ${tone}`}>
      <p>{result.message}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <span className="badge bg-white">sessionid: {result.hasSessionid ? "已检测到" : "缺少"}</span>
        <span className="badge bg-white">sid_guard: {result.hasSidGuard ? "已检测到" : "缺少"}</span>
      </div>
    </div>
  );
}

function CookieGuide() {
  return (
    <div className="mb-4 rounded-md border border-line bg-paper p-3 text-sm text-ink/70">
      <p className="font-medium text-ink">Chrome / Edge 获取方式</p>
      <ol className="mt-2 list-decimal space-y-1 pl-5">
        <li>在浏览器打开抖音网页版并完成登录。</li>
        <li>按 F12 打开开发者工具，进入 Network。</li>
        <li>
          刷新页面，点任意 <code>douyin.com</code> 请求。
        </li>
        <li>在 Headers 里复制 Request Headers 下的 Cookie。</li>
        <li>
          粘贴到这里，确认包含 <code>sessionid</code> 或 <code>sid_guard</code>。
        </li>
        <li>
          同一个请求的 URL、Payload 或响应中通常能找到 <code>sec_user_id</code>，复制后填入账号表单。
        </li>
      </ol>
      <p className="mt-2 text-ember">Cookie 等同登录态，不要发给别人，也不要提交到 Git。</p>
    </div>
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
    <section>
      <PageHeader title="设置" description="本地路径、下载并发和系统能力。" />
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <form
          className="panel p-4"
          onSubmit={(event) => {
            event.preventDefault();
            update.mutate();
          }}
        >
          <SectionTitle icon={Settings} title="下载配置" compact />
          <label className="mb-2 block text-sm font-medium">下载并发</label>
          <input className="input" type="number" min={1} max={8} value={concurrency} onChange={(event) => setConcurrency(event.target.value)} />
          <p className="mt-2 text-sm text-ink/55">音频抽取模式固定为 copy，不主动重编码。</p>
          <ErrorLine error={update.error} />
          <button className="btn btn-primary mt-4 w-full">保存设置</button>
        </form>
        <div className="panel p-4">
          <SectionTitle icon={Database} title="系统信息" compact />
          {settings.isLoading ? (
            <LoadingRow />
          ) : data ? (
            <dl className="grid gap-3 text-sm">
              <InfoRow label="运行环境" value={data.app_env} />
              <InfoRow label="数据目录" value={data.data_dir} />
              <InfoRow label="下载目录" value={data.download_dir} />
              <InfoRow label="临时目录" value={data.temp_dir} />
              <InfoRow label="ffmpeg" value={data.ffmpeg_available ? "可用" : "未找到"} />
              <InfoRow label="ffprobe" value={data.ffprobe_available ? "可用" : "未找到"} />
              <InfoRow label="WebDAV" value={data.webdav_enabled ? data.webdav_url : "未启用"} />
            </dl>
          ) : (
            <EmptyState text="无法读取设置" />
          )}
        </div>
      </div>
    </section>
  );
}

function TaskRow({ task, onRetry, onCancel }: { task: DownloadTask; onRetry: () => void; onCancel: () => void }) {
  return (
    <div className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium">{task.source_title ?? `来源 #${task.source_item_id}`}</p>
          <p className="text-sm text-ink/55">
            {task.download_type} · {task.source_author ?? "未知作者"}
          </p>
        </div>
        <StatusBadge status={task.status} />
      </div>
      <div className="mt-3 h-2 rounded-full bg-line">
        <div className="h-2 rounded-full bg-lake" style={{ width: `${task.progress}%` }} />
      </div>
      {task.error_message && <p className="mt-3 rounded-md bg-ember/10 px-3 py-2 text-sm text-ember">{task.error_message}</p>}
      <div className="mt-3 flex gap-2">
        {task.status === "failed" && (
          <button className="btn h-9" onClick={onRetry}>
            <RefreshCw size={16} />
            重试
          </button>
        )}
        {(task.status === "pending" || task.status === "running") && (
          <button className="btn h-9" onClick={onCancel}>
            取消
          </button>
        )}
      </div>
    </div>
  );
}

function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <header className="mb-5">
      <p className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-moss">Depot</p>
      <h1 className="text-2xl font-semibold md:text-3xl">{title}</h1>
      <p className="mt-1 max-w-2xl text-sm text-ink/60">{description}</p>
    </header>
  );
}

function SectionTitle({ icon: Icon, title, compact = false }: { icon: typeof Archive; title: string; compact?: boolean }) {
  return (
    <div className={`flex items-center gap-2 border-b border-line ${compact ? "mb-4 border-b-0 p-0" : "p-4"}`}>
      <Icon size={18} className="text-lake" />
      <h2 className="font-semibold">{title}</h2>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "active" || status === "succeeded"
      ? "border-green-600/25 bg-green-600/10 text-green-700"
      : status === "failed" || status === "invalid" || status === "expired"
        ? "border-ember/25 bg-ember/10 text-ember"
        : status === "running"
          ? "border-lake/25 bg-lake/10 text-lake"
          : "border-line bg-paper text-ink/60";
  return <span className={`badge ${tone}`}>{status}</span>;
}

function ErrorLine({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p className="mt-3 flex items-start gap-2 rounded-md bg-ember/10 px-3 py-2 text-sm text-ember">
      <CircleAlert className="mt-0.5 shrink-0" size={15} />
      {errorMessage(error)}
    </p>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="p-8 text-center text-sm text-ink/55">{text}</div>;
}

function LoadingRow() {
  return (
    <div className="flex items-center gap-2 p-4 text-sm text-ink/55">
      <Loader2 className="animate-spin" size={16} />
      加载中
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 border-b border-line pb-3 md:grid-cols-[110px_1fr]">
      <dt className="text-ink/55">{label}</dt>
      <dd className="break-all font-medium">{value}</dd>
    </div>
  );
}

function CenteredMessage({ text }: { text: string }) {
  return <div className="grid min-h-screen place-items-center bg-paper px-4 text-center text-sm text-ink/60">{text}</div>;
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
const accountsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/accounts", component: AccountsPage });
const settingsRoute = createRoute({ getParentRoute: () => rootRoute, path: "/settings", component: SettingsPage });
const routeTree = rootRoute.addChildren([mediaRoute, mediaAliasRoute, tasksRoute, accountsRoute, settingsRoute]);
const router = createRouter({ routeTree, defaultPreload: "intent" });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export default App;
