from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .jobs import JobManager
from .models import AnalyzeRequest, DownloadJob, DownloadRequest, ErrorBody, JobStatus
from .providers.ytdlp import YtDlpProvider
from .security import owner_hash, require_client_id, validate_media_url

settings = get_settings()
provider = YtDlpProvider(settings)
jobs = JobManager(settings, provider)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await jobs.start()
    yield
    await jobs.stop()


app = FastAPI(
    title="LOOD API",
    version="0.1.0",
    description="Analyze permitted public media and manage bounded download jobs.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Client-ID"],
)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorBody(code=f"http_{exc.status_code}", message=str(exc.detail)).model_dump(),
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/media/analyze")
@limiter.limit("12/minute")
async def analyze(request: Request, body: AnalyzeRequest):
    url, platform = await validate_media_url(str(body.url))
    try:
        return await provider.analyze(url, platform)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="The source took too long to respond") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="The source could not be analyzed. It may be private, protected, or unavailable.",
        ) from exc


@app.post("/api/downloads", response_model=DownloadJob, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("6/minute")
async def create_download(
    request: Request,
    body: DownloadRequest,
    client_id: str = Depends(require_client_id),
):
    _, platform = await validate_media_url(str(body.url))
    try:
        return await jobs.create(body, owner_hash(client_id), platform)
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@app.get("/api/downloads/{job_id}", response_model=DownloadJob)
async def get_download(job_id: str, client_id: str = Depends(require_client_id)):
    record = jobs.get(job_id, owner_hash(client_id))
    if not record:
        raise HTTPException(status_code=404, detail="Download job not found")
    return record.public


@app.delete("/api/downloads/{job_id}", response_model=DownloadJob)
async def cancel_download(job_id: str, client_id: str = Depends(require_client_id)):
    job = jobs.cancel(job_id, owner_hash(client_id))
    if not job:
        raise HTTPException(status_code=404, detail="Download job not found")
    return job


@app.get("/api/downloads/{job_id}/file")
async def get_file(job_id: str, token: str, client_id: str = Depends(require_client_id)):
    record = jobs.get(job_id, owner_hash(client_id))
    if not record or not record.file_path or record.public.status != JobStatus.completed:
        raise HTTPException(status_code=404, detail="Download file not found")
    if not record.public.file_token or token != record.public.file_token:
        raise HTTPException(status_code=403, detail="Invalid file token")
    return FileResponse(
        record.file_path,
        filename=record.public.filename,
        media_type="application/octet-stream",
    )

