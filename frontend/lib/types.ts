export type MediaFormat = {
  id: string;
  label: string;
  kind: "video" | "audio";
  extension: string;
  width?: number;
  height?: number;
  fps?: number;
  bitrate_kbps?: number;
  filesize?: number;
  has_audio: boolean;
};

export type MediaInfo = {
  id: string;
  title: string;
  author?: string;
  duration?: number;
  thumbnail?: string;
  platform: string;
  webpage_url: string;
  formats: MediaFormat[];
};

export type JobStatus = "preparing" | "processing" | "downloading" | "completed" | "failed" | "cancelled";

export type DownloadJob = {
  id: string;
  status: JobStatus;
  progress?: number;
  stage: string;
  filename?: string;
  filesize?: number;
  error?: string;
  file_token?: string;
};

