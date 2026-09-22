# LOOD

LOOD is a bilingual, mobile-first PWA for analyzing supported public-media links and downloading an available video or audio format when the user has the right to do so.

This repository contains a real MVP:

- Next.js + TypeScript + Tailwind frontend with Arabic RTL and English UI
- installable PWA shell, service worker, offline fallback, light/dark themes
- FastAPI backend with a provider interface and a `yt-dlp` implementation
- bounded background job queue, real progress updates, cancellation, expiring files
- FFmpeg audio extraction and video/audio merging without shell interpolation
- supported-host allowlist, DNS/IP checks, per-client job ownership, rate limits
- Docker images, Compose setup, backend tests, and API documentation

## Live web deployment

The frontend is deployed to GitHub Pages at:

**<https://mohamed-elrady.github.io/lood/>**

GitHub Pages cannot run Python, FFmpeg, background workers, or `yt-dlp`. To enable analysis and downloads on the public URL, deploy `backend/` to a container host, then add a GitHub repository variable named `NEXT_PUBLIC_API_URL` containing its public HTTPS origin (for example, `https://api.example.com`). Also set the backend `LOOD_CORS_ORIGINS` to `https://mohamed-elrady.github.io`, then re-run the **Deploy web to GitHub Pages** workflow.

## Important limits

LOOD supports only public media that the user owns or has permission to save. It does not bypass DRM, private-content restrictions, logins, paywalls, or platform access controls. Platform extractors can change upstream; keep `yt-dlp` current and comply with each platform's terms and applicable law.

The included queue is process-local and intentionally simple for a single-instance MVP. Jobs remain on the server while the page is open or closed, but they do not survive an API restart. For multi-instance production deployment, replace `JobManager` storage/queue with Redis plus a worker such as Dramatiq, RQ, or Celery, and store outputs in private object storage.

## Requirements

- Node.js 20+
- Python 3.11+
- FFmpeg available on `PATH`
- internet access for source analysis/downloads

Or use Docker Desktop with Compose.

## Run with Docker

```bash
docker compose up --build
```

Open <http://localhost:3000>. API documentation is at <http://localhost:8000/docs>.

## Run locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` only when overriding defaults. Do not commit secrets. `NEXT_PUBLIC_API_URL` is compiled into the web build and must be reachable from the user's browser.

## API flow

1. `POST /api/media/analyze` validates and inspects a supported URL.
2. `POST /api/downloads` creates a bounded background job.
3. `GET /api/downloads/{job_id}` returns its real state and measurable progress.
4. `GET /api/downloads/{job_id}/file?token=...` streams the completed file.
5. `DELETE /api/downloads/{job_id}` requests cancellation.

The frontend generates a random client ID. The API hashes it and binds every job to it; knowing a job UUID alone is not sufficient. The completed file also requires its random token. Use authenticated accounts and persistent ownership records if deploying as a shared public service.

## Tests and checks

```bash
cd backend && pytest
cd frontend && npm run build
```

Backend tests use mocks for DNS and validation and do not download third-party media. Live extractor tests are intentionally excluded because they are unstable and may violate CI/network policy.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Browser-facing API origin |
| `LOOD_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed web origins |
| `LOOD_MAX_ACTIVE_JOBS` | `2` | Concurrent heavy jobs per API process |
| `LOOD_MAX_FILE_SIZE_MB` | `1024` | Per-download size ceiling |
| `LOOD_DOWNLOAD_TIMEOUT_SECONDS` | `1800` | Maximum job processing time |
| `LOOD_JOB_TTL_SECONDS` | `3600` | Completed/failed job and file retention |

## Production checklist

- Terminate TLS at a reverse proxy and serve web/API from trusted origins.
- Run downloads in isolated workers with CPU, memory, disk, network, and time quotas.
- Revalidate redirect destinations at the egress layer; block private/metadata networks there too.
- Add Redis-backed global rate limits and a durable queue for multiple API replicas.
- Use private object storage with short-lived signed URLs and malware scanning where appropriate.
- Add authentication if users need persistent history or cross-device access.
- Set a clear privacy policy and retention policy before public launch.
- Exercise real supported sources in a controlled integration environment.

## Project layout

```text
frontend/              Next.js application and PWA assets
  app/                 page, metadata, global design system
  components/          downloader flow and app providers
  lib/                 typed API client and models
  public/              manifest, icons, offline page, service worker
backend/
  app/main.py           FastAPI routes and middleware
  app/jobs.py           bounded background queue and file lifecycle
  app/providers/        extensible provider interface + yt-dlp provider
  app/security.py       host allowlist, DNS/IP checks, client ownership
  tests/                isolated validation tests
```
