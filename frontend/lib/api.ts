import type { DownloadJob, MediaInfo } from "./types";

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

function apiUrl(): string {
  if (configuredApiUrl) return configuredApiUrl;
  if (typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    return "http://localhost:8000";
  }
  throw new Error("خادم التحميل لم يُربط بهذا الإصدار بعد. اضبط NEXT_PUBLIC_API_URL ثم أعد النشر.");
}

function clientId(): string {
  const key = "lood-client-id";
  let value = localStorage.getItem(key);
  if (!value) {
    value = crypto.randomUUID();
    localStorage.setItem(key, value);
  }
  return value;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("X-Client-ID", clientId());
  const response = await fetch(`${apiUrl()}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.message || body?.detail || "تعذر إكمال الطلب");
  }
  return response.json();
}

export function analyzeMedia(url: string) {
  return request<MediaInfo>("/api/media/analyze", {
    method: "POST",
    body: JSON.stringify({ url })
  });
}

export function createDownload(body: {
  url: string;
  format_id: string;
  output_type: "video" | "audio";
  audio_format?: "mp3" | "m4a" | "webm";
  authorized: boolean;
}) {
  return request<DownloadJob>("/api/downloads", { method: "POST", body: JSON.stringify(body) });
}

export function getJob(id: string) {
  return request<DownloadJob>(`/api/downloads/${id}`);
}

export function cancelJob(id: string) {
  return request<DownloadJob>(`/api/downloads/${id}`, { method: "DELETE" });
}

export function retryJob(id: string) {
  return request<DownloadJob>(`/api/downloads/${id}/retry`, { method: "POST" });
}

export function saveJobFile(job: DownloadJob) {
  if (!job.file_token) throw new Error("Missing file token");
  const anchor = document.createElement("a");
  anchor.href = `${apiUrl()}/api/downloads/${job.id}/file?token=${encodeURIComponent(job.file_token)}`;
  anchor.download = job.filename || "";
  anchor.rel = "noopener";
  anchor.click();
}
