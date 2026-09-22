import asyncio
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp

from ..config import Settings
from ..models import DownloadRequest, MediaFormat, MediaInfo, OutputType, Platform
from .base import MediaProvider, ProgressCallback


class CancelledByUser(Exception):
    pass


class YtDlpProvider(MediaProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    def supports(self, platform: Platform) -> bool:
        return platform in Platform

    def _base_options(self) -> dict[str, Any]:
        return {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "playlistend": 1,
            "socket_timeout": 20,
            "retries": 2,
            "fragment_retries": 2,
            "nocheckcertificate": False,
            "restrictfilenames": True,
            "js_runtimes": {"node": {}},
            "cachedir": str(self.settings.data_dir / ".cache"),
            "match_filter": self._reject_live,
        }

    @staticmethod
    def _reject_live(info: dict[str, Any], *, incomplete: bool = False) -> str | None:
        if not incomplete and (info.get("is_live") or info.get("live_status") == "is_live"):
            return "Live streams are not supported"
        return None

    async def analyze(self, url: str, platform: Platform) -> MediaInfo:
        def extract() -> dict[str, Any]:
            with yt_dlp.YoutubeDL(self._base_options()) as ydl:
                return ydl.extract_info(url, download=False)

        info = await asyncio.wait_for(
            asyncio.to_thread(extract), timeout=min(self.settings.download_timeout_seconds, 90)
        )
        formats: list[MediaFormat] = []
        seen: set[tuple] = set()
        for item in info.get("formats") or []:
            video = item.get("vcodec") not in {None, "none"}
            audio = item.get("acodec") not in {None, "none"}
            if not video and not audio:
                continue
            kind = "video" if video else "audio"
            key = (kind, item.get("height"), item.get("ext"), item.get("format_id"))
            if key in seen:
                continue
            seen.add(key)
            height = item.get("height")
            abr = item.get("abr") or item.get("tbr")
            label = f"{height}p" if video and height else f"{round(abr)} kbps" if abr else item.get("format_note") or kind
            formats.append(
                MediaFormat(
                    id=str(item.get("format_id")),
                    label=label,
                    kind=kind,
                    extension=item.get("ext") or "unknown",
                    width=item.get("width"),
                    height=height,
                    fps=item.get("fps"),
                    bitrate_kbps=abr,
                    filesize=item.get("filesize") or item.get("filesize_approx"),
                    has_audio=audio,
                )
            )
        formats.sort(key=lambda f: (f.kind != "video", -(f.height or 0), -(f.bitrate_kbps or 0)))
        if not formats:
            raise RuntimeError("The source returned no downloadable formats")
        return MediaInfo(
            id=str(info.get("id") or "media"),
            title=info.get("title") or "Untitled media",
            author=info.get("uploader") or info.get("channel"),
            duration=info.get("duration"),
            thumbnail=info.get("thumbnail"),
            platform=platform,
            webpage_url=info.get("webpage_url") or url,
            formats=formats,
        )

    async def download(
        self,
        request: DownloadRequest,
        destination: Path,
        progress: ProgressCallback,
        is_cancelled: Callable[[], bool],
    ) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        size_limit = self.settings.max_file_size_mb * 1024 * 1024

        def hook(data: dict[str, Any]) -> None:
            if is_cancelled():
                raise CancelledByUser()
            downloaded = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            if max(downloaded, total) > size_limit:
                raise RuntimeError("The download exceeds the configured size limit")
            progress(data)

        def postprocess_hook(data: dict[str, Any]) -> None:
            if is_cancelled():
                raise CancelledByUser()
            progress({"status": "processing", "postprocessor": data.get("postprocessor")})

        def run() -> Path:
            options = self._base_options()
            safe_id = re.sub(r"[^A-Za-z0-9._-]", "", request.format_id)
            if not safe_id or safe_id != request.format_id:
                raise ValueError("Invalid format identifier")
            options.update(
                {
                    "outtmpl": str(destination / "%(id)s.%(ext)s"),
                    "progress_hooks": [hook],
                    "postprocessor_hooks": [postprocess_hook],
                    "max_filesize": size_limit,
                    "continuedl": True,
                    "nopart": False,
                }
            )
            if request.output_type == OutputType.audio:
                codec = request.audio_format.value if request.audio_format else "mp3"
                options["format"] = f"{safe_id}/bestaudio"
                if codec == "mp3":
                    options["postprocessors"] = [
                        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}
                    ]
                elif codec == "m4a":
                    options["postprocessors"] = [
                        {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"}
                    ]
                elif codec == "webm":
                    options["postprocessors"] = [
                        {"key": "FFmpegVideoConvertor", "preferedformat": "webm"}
                    ]
            else:
                options["format"] = f"{safe_id}+bestaudio/{safe_id}"
                options["merge_output_format"] = "mp4"
            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([str(request.url)])
            files = [p for p in destination.iterdir() if p.is_file() and not p.name.endswith(".part")]
            if not files:
                raise RuntimeError("The source did not produce a downloadable file")
            result = max(files, key=lambda p: p.stat().st_mtime)
            if result.stat().st_size > size_limit:
                shutil.rmtree(destination, ignore_errors=True)
                raise RuntimeError("The resulting file exceeds the configured size limit")
            return result

        return await asyncio.wait_for(
            asyncio.to_thread(run), timeout=self.settings.download_timeout_seconds
        )
