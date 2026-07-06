import type { Account, ApiEnvelope, AppSettings, DownloadTask, MediaFile, Page, SourceItem } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiClientError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });
  const envelope = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || envelope.error) {
    throw new ApiClientError(envelope.error?.message ?? "请求失败", envelope.error?.code ?? "http_error", response.status);
  }
  return envelope.data as T;
}

const params = (values: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
};

export const api = {
  me: () => request<{ authenticated: boolean; user: string }>("/auth/me"),
  login: (password: string) => request<{ authenticated: boolean }>("/auth/login", { method: "POST", body: JSON.stringify({ password }) }),
  logout: () => request<{ authenticated: boolean }>("/auth/logout", { method: "POST" }),
  accounts: () => request<Account[]>("/accounts"),
  createAccount: (payload: { name: string; cookie: string; sec_user_id: string }) =>
    request<Account>("/accounts", { method: "POST", body: JSON.stringify(payload) }),
  updateAccount: (id: number, payload: Partial<{ name: string; cookie: string; sec_user_id: string; enabled: boolean }>) =>
    request<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteAccount: (id: number) => request<{ deleted: boolean }>(`/accounts/${id}`, { method: "DELETE" }),
  verifyAccount: (id: number) => request<Account>(`/accounts/${id}/verify`, { method: "POST" }),
  syncAccount: (id: number, source_type: "liked" | "favorite") =>
    request<{ created: number; total: number }>(`/accounts/${id}/sync`, {
      method: "POST",
      body: JSON.stringify({ source_type, limit: 100 }),
    }),
  createManualSource: (payload: { account_id: number; url: string; title?: string }) =>
    request<SourceItem>("/sources/manual", { method: "POST", body: JSON.stringify(payload) }),
  sources: (filters: { account_id?: number; source_type?: string; keyword?: string; downloaded?: boolean; page?: number; page_size?: number }) =>
    request<Page<SourceItem>>(`/sources${params({ ...filters, page: filters.page ?? 1, page_size: filters.page_size ?? 50 })}`),
  tasks: (status?: string) => request<Page<DownloadTask>>(`/tasks${params({ status, page: 1, page_size: 50 })}`),
  createTasks: (source_item_ids: number[], download_type: "video" | "audio" | "both") =>
    request<DownloadTask[]>("/tasks", { method: "POST", body: JSON.stringify({ source_item_ids, download_type }) }),
  retryTask: (id: number) => request<DownloadTask>(`/tasks/${id}/retry`, { method: "POST" }),
  cancelTask: (id: number) => request<DownloadTask>(`/tasks/${id}/cancel`, { method: "POST" }),
  media: (filters: { media_type?: string; keyword?: string; author?: string; account_id?: number; page?: number; page_size?: number }) =>
    request<Page<MediaFile>>(`/media${params({ ...filters, page: filters.page ?? 1, page_size: filters.page_size ?? 50 })}`),
  deleteMedia: (id: number) => request<{ deleted: boolean }>(`/media/${id}`, { method: "DELETE" }),
  settings: () => request<AppSettings>("/settings"),
  updateSettings: (payload: Partial<Pick<AppSettings, "max_concurrent_downloads" | "audio_extract_mode">>) =>
    request<AppSettings>("/settings", { method: "PATCH", body: JSON.stringify(payload) }),
};
