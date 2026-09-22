import asyncio
from pathlib import Path

import pytest

from app.config import Settings
from app.jobs import JobManager
from app.models import DownloadRequest, JobStatus, MediaInfo, Platform
from app.providers.base import MediaProvider


def test_download_requires_rights_confirmation():
    try:
        DownloadRequest(
            url="https://youtube.com/watch?v=test",
            format_id="18",
            output_type="video",
            authorized=False,
        )
        assert False, "validation should fail"
    except ValueError as error:
        assert "allowed" in str(error)


class FakeProvider(MediaProvider):
    def __init__(self, fail_once: bool = False):
        self.fail_once = fail_once

    def supports(self, platform: Platform) -> bool:
        return True

    async def analyze(self, url: str, platform: Platform) -> MediaInfo:
        raise NotImplementedError

    async def download(self, request, destination: Path, progress, is_cancelled):
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("temporary provider error")
        destination.mkdir(parents=True, exist_ok=True)
        progress({"downloaded_bytes": 5, "total_bytes": 10})
        progress({"status": "processing"})
        output = destination / "fixture.mp4"
        output.write_bytes(b"fixture")
        return output


def request_fixture() -> DownloadRequest:
    return DownloadRequest(
        url="https://vimeo.com/56015672",
        format_id="http-360p",
        output_type="video",
        authorized=True,
    )


async def wait_terminal(manager: JobManager, job_id: str, owner: str):
    for _ in range(100):
        record = manager.get(job_id, owner)
        if record and record.public.status in {
            JobStatus.completed,
            JobStatus.failed,
            JobStatus.cancelled,
        }:
            return record
        await asyncio.sleep(0.01)
    raise AssertionError("job did not reach a terminal state")


@pytest.mark.asyncio
async def test_job_completes_and_file_token_is_required(tmp_path):
    settings = Settings(data_dir=tmp_path, max_active_jobs=1)
    manager = JobManager(settings, FakeProvider())
    await manager.start()
    try:
        job = await manager.create(request_fixture(), "owner-a", Platform.vimeo)
        record = await wait_terminal(manager, job.id, "owner-a")
        assert record.public.status == JobStatus.completed
        assert record.public.progress == 100
        assert record.public.file_token
        assert manager.get(job.id, "owner-b") is None
        assert manager.get_file(job.id, "wrong-token") is None
        assert manager.get_file(job.id, record.public.file_token) is record
    finally:
        await manager.stop()


@pytest.mark.asyncio
async def test_failed_job_can_retry(tmp_path):
    settings = Settings(data_dir=tmp_path, max_active_jobs=1)
    manager = JobManager(settings, FakeProvider(fail_once=True))
    await manager.start()
    try:
        first = await manager.create(request_fixture(), "owner-a", Platform.vimeo)
        failed = await wait_terminal(manager, first.id, "owner-a")
        assert failed.public.status == JobStatus.failed
        retried = await manager.retry(first.id, "owner-a")
        assert retried is not None and retried.id != first.id
        completed = await wait_terminal(manager, retried.id, "owner-a")
        assert completed.public.status == JobStatus.completed
    finally:
        await manager.stop()

