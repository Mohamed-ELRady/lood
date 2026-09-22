from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Platform(StrEnum):
    youtube = "youtube"
    facebook = "facebook"
    instagram = "instagram"
    tiktok = "tiktok"
    x = "x"
    vimeo = "vimeo"
    soundcloud = "soundcloud"


class MediaFormat(BaseModel):
    id: str
    label: str
    kind: str
    extension: str
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    bitrate_kbps: float | None = None
    filesize: int | None = None
    has_audio: bool = False


class MediaInfo(BaseModel):
    id: str
    title: str
    author: str | None = None
    duration: float | None = None
    thumbnail: str | None = None
    platform: Platform
    webpage_url: str
    formats: list[MediaFormat]


class AnalyzeRequest(BaseModel):
    url: HttpUrl


class OutputType(StrEnum):
    video = "video"
    audio = "audio"


class AudioFormat(StrEnum):
    mp3 = "mp3"
    m4a = "m4a"
    webm = "webm"


class DownloadRequest(BaseModel):
    url: HttpUrl
    format_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    output_type: OutputType
    audio_format: AudioFormat | None = None
    authorized: bool

    @field_validator("authorized")
    @classmethod
    def require_authorization(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must confirm that you are allowed to download this media")
        return value


class JobStatus(StrEnum):
    preparing = "preparing"
    processing = "processing"
    downloading = "downloading"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class DownloadJob(BaseModel):
    id: str
    status: JobStatus
    progress: float | None = None
    stage: str
    filename: str | None = None
    filesize: int | None = None
    error: str | None = None
    file_token: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
