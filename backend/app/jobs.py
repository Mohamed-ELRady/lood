import asyncio
import secrets
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .models import DownloadJob, DownloadRequest, JobStatus, Platform
from .providers.ytdlp import CancelledByUser, YtDlpProvider


@dataclass
class JobRecord:
    public: DownloadJob
    request: DownloadRequest
    owner: str
    platform: Platform
    created_at: float = field(default_factory=time.time)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    file_path: Path | None = None


class JobManager:
    def __init__(self, settings: Settings, provider: YtDlpProvider):
        self.settings = settings
        self.provider = provider
        self.jobs: dict[str, JobRecord] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=50)
        self.workers: list[asyncio.Task] = []
        self.cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.workers = [asyncio.create_task(self._worker()) for _ in range(self.settings.max_active_jobs)]
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        tasks = [*self.workers, *([self.cleanup_task] if self.cleanup_task else [])]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def create(self, request: DownloadRequest, owner: str, platform: Platform) -> DownloadJob:
        if self.queue.full():
            raise RuntimeError("The download queue is full. Try again shortly.")
        job_id = uuid.uuid4().hex
        public = DownloadJob(id=job_id, status=JobStatus.preparing, stage="queued", progress=0)
        self.jobs[job_id] = JobRecord(public=public, request=request, owner=owner, platform=platform)
        await self.queue.put(job_id)
        return public.model_copy(deep=True)

    def get(self, job_id: str, owner: str) -> JobRecord | None:
        record = self.jobs.get(job_id)
        return record if record and secrets.compare_digest(record.owner, owner) else None

    def cancel(self, job_id: str, owner: str) -> DownloadJob | None:
        record = self.get(job_id, owner)
        if not record:
            return None
        if record.public.status not in {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}:
            record.cancel_event.set()
            record.public.status = JobStatus.cancelled
            record.public.stage = "cancelled"
        return record.public.model_copy(deep=True)

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            record = self.jobs.get(job_id)
            try:
                if not record or record.cancel_event.is_set():
                    continue
                record.public.status = JobStatus.processing
                record.public.stage = "preparing_source"
                event_loop = asyncio.get_running_loop()
                current_record = record

                def on_progress(
                    data: dict,
                    current_record: JobRecord = current_record,
                    event_loop: asyncio.AbstractEventLoop = event_loop,
                ) -> None:
                    if current_record.cancel_event.is_set():
                        raise CancelledByUser()
                    downloaded = data.get("downloaded_bytes") or 0
                    total = data.get("total_bytes") or data.get("total_bytes_estimate")
                    progress = round(downloaded * 100 / total, 1) if total else None

                    def update(
                        current_record: JobRecord = current_record,
                        progress: float | None = progress,
                    ) -> None:
                        current_record.public.status = JobStatus.downloading
                        current_record.public.stage = "downloading"
                        current_record.public.progress = progress

                    event_loop.call_soon_threadsafe(update)

                path = await self.provider.download(
                    record.request,
                    self.settings.data_dir / job_id,
                    on_progress,
                    record.cancel_event.is_set,
                )
                if record.cancel_event.is_set():
                    raise CancelledByUser()
                record.file_path = path
                record.public.status = JobStatus.completed
                record.public.stage = "ready"
                record.public.progress = 100
                record.public.filename = path.name
                record.public.filesize = path.stat().st_size
                record.public.file_token = secrets.token_urlsafe(24)
            except (CancelledByUser, asyncio.CancelledError):
                record.public.status = JobStatus.cancelled
                record.public.stage = "cancelled"
            except Exception as exc:  # noqa: BLE001 - provider errors are normalized at the job boundary
                record.public.status = JobStatus.failed
                record.public.stage = "failed"
                record.public.error = self._friendly_error(exc)
            finally:
                self.queue.task_done()

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        message = str(exc)
        lowered = message.lower()
        if "private" in lowered or "login" in lowered:
            return "This media is private or requires sign-in. LOOD does not request account cookies."
        if "copyright" in lowered or "drm" in lowered:
            return "This media is protected or unavailable for download."
        if "larger than max-filesize" in lowered:
            return "The resulting file exceeds the server size limit."
        return "The source could not be processed. It may be unavailable or unsupported."

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            cutoff = time.time() - self.settings.job_ttl_seconds
            expired = [job_id for job_id, job in self.jobs.items() if job.created_at < cutoff]
            for job_id in expired:
                record = self.jobs.pop(job_id, None)
                if record:
                    shutil.rmtree(self.settings.data_dir / job_id, ignore_errors=True)
