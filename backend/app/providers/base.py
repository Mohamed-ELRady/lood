from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from ..models import DownloadRequest, MediaInfo, Platform

ProgressCallback = Callable[[dict], None]


class MediaProvider(ABC):
    @abstractmethod
    def supports(self, platform: Platform) -> bool: ...

    @abstractmethod
    async def analyze(self, url: str, platform: Platform) -> MediaInfo: ...

    @abstractmethod
    async def download(
        self,
        request: DownloadRequest,
        destination: Path,
        progress: ProgressCallback,
        is_cancelled: Callable[[], bool],
    ) -> Path: ...

