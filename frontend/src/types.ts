export type ApiError = {
  code: string;
  message: string;
  detail: Record<string, unknown>;
};

export type ApiEnvelope<T> = {
  data: T | null;
  error: ApiError | null;
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type Account = {
  id: number;
  name: string;
  slug: string;
  sec_user_id: string;
  status: "active" | "expired" | "invalid" | "disabled";
  enabled: boolean;
  last_verified_at: string | null;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SourceItem = {
  id: number;
  account_id: number;
  account_name: string | null;
  source_type: "liked" | "favorite" | "manual";
  platform_item_id: string;
  title: string | null;
  author_name: string | null;
  cover_url: string | null;
  detail_url: string | null;
  duration_seconds: number | null;
  downloaded: boolean;
};

export type DownloadTask = {
  id: number;
  source_item_id: number;
  download_type: "video" | "audio" | "both";
  status: "pending" | "running" | "succeeded" | "failed" | "canceled";
  progress: number;
  error_code: string | null;
  error_message: string | null;
  stderr_tail: string | null;
  source_title: string | null;
  source_author: string | null;
  created_at: string;
};

export type MediaFile = {
  id: number;
  source_item_id: number;
  task_id: number | null;
  media_type: "video" | "audio";
  relative_path: string;
  filename: string;
  file_size: number | null;
  codec_name: string | null;
  duration_seconds: number | null;
  source_title: string | null;
  source_author: string | null;
  account_id: number | null;
};

export type AppSettings = {
  app_name: string;
  app_env: string;
  data_dir: string;
  download_dir: string;
  temp_dir: string;
  max_concurrent_downloads: number;
  audio_extract_mode: string;
  ffmpeg_available: boolean;
  ffprobe_available: boolean;
  webdav_enabled: boolean;
  webdav_url: string;
  webdav_remote_dir: string;
};
