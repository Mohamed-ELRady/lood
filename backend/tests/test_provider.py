from pathlib import Path
from typing import Any, ClassVar

import pytest

from app.config import Settings
from app.models import DownloadRequest, Platform
from app.providers.ytdlp import YtDlpProvider


class FakeYDL:
    instances: ClassVar[list["FakeYDL"]] = []
    info: ClassVar[dict[str, Any]] = {
        "id": "fixture-id",
        "title": "Fixture video",
        "uploader": "LOOD tests",
        "duration": 10.25,
        "thumbnail": "https://example.invalid/thumb.jpg",
        "webpage_url": "https://vimeo.com/56015672",
        "formats": [
            {
                "format_id": "audio-128",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "aac",
                "abr": 128,
                "filesize": 1000,
            },
            {
                "format_id": "video-360",
                "ext": "mp4",
                "vcodec": "h264",
                "acodec": "none",
                "height": 360,
                "width": 640,
                "filesize": 2000,
            },
        ],
    }

    def __init__(self, options):
        self.options = options
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def extract_info(self, url, download=False):
        return self.info

    def download(self, urls):
        for hook in self.options.get("progress_hooks", []):
            hook({"downloaded_bytes": 10, "total_bytes": 10})
        template = self.options["outtmpl"]
        output = Path(template.replace("%(id)s", "fixture-id").replace("%(ext)s", "mp4"))
        output.write_bytes(b"media")


@pytest.mark.asyncio
async def test_analyze_normalizes_real_formats(monkeypatch, tmp_path):
    monkeypatch.setattr("app.providers.ytdlp.yt_dlp.YoutubeDL", FakeYDL)
    provider = YtDlpProvider(Settings(data_dir=tmp_path))
    result = await provider.analyze("https://vimeo.com/56015672", Platform.vimeo)
    assert result.title == "Fixture video"
    assert result.duration == 10.25
    assert [item.kind for item in result.formats] == ["video", "audio"]
    assert result.formats[0].label == "360p"
    assert FakeYDL.instances[-1].options["noplaylist"] is True
    assert "node" in FakeYDL.instances[-1].options["js_runtimes"]


@pytest.mark.asyncio
async def test_download_uses_selected_format_and_bounded_output(monkeypatch, tmp_path):
    FakeYDL.instances.clear()
    monkeypatch.setattr("app.providers.ytdlp.yt_dlp.YoutubeDL", FakeYDL)
    provider = YtDlpProvider(Settings(data_dir=tmp_path, max_file_size_mb=10))
    request = DownloadRequest(
        url="https://vimeo.com/56015672",
        format_id="video-360",
        output_type="video",
        authorized=True,
    )
    result = await provider.download(request, tmp_path / "job", lambda _: None, lambda: False)
    assert result.read_bytes() == b"media"
    options = FakeYDL.instances[-1].options
    assert options["format"] == "video-360+bestaudio/video-360"
    assert options["max_filesize"] == 10 * 1024 * 1024
