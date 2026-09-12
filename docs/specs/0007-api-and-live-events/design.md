# Design: 0007 API and Live Events

## Overview

A thin FastAPI layer over the run store and event bus. It owns no business logic. Runs execute as background tasks in the same process, and the SSE endpoint bridges the in-process event bus to HTTP.

## Components

- `src/goldcoast/api/app.py`: application factory, CORS, router registration, lifespan that loads settings and seed data once.
- `src/goldcoast/api/deps.py`: dependencies providing `Settings`, `SeedData`, `RunStore`, and a `RunRegistry` of active runs and their event buses.
- `src/goldcoast/api/routes/runs.py`: `POST /runs`, `GET /runs`, `GET /runs/{run_id}`, `GET /runs/{run_id}/moments`, `GET /runs/{run_id}/briefs`, `GET /runs/{run_id}/ads`, `GET /runs/{run_id}/export`.
- `src/goldcoast/api/routes/events.py`: `GET /runs/{run_id}/events` using `sse-starlette`.
- `src/goldcoast/api/routes/decisions.py`: `POST /ads/{ad_id}/decision`.
- `src/goldcoast/api/routes/media.py`: `/media/{run_id}/{path}` and `/clips/{name}` with safe path resolution.
- `src/goldcoast/api/routes/seed.py`: seed endpoints.
- `src/goldcoast/api/schemas.py`: `RunCreate`, `AdWithVerdict`, `DecisionCreate`, `ExportManifest`.
- `tests/test_api.py`.

## Data Flow

1. `POST /runs` validates clip confinement and replay selection, creates and saves exactly one run through `RunStore`, registers its `EventBus`, and schedules `Pipeline.run(..., run=run, bus=bus)` with `asyncio.to_thread`. The 201 response is a snapshot of the `running` record. An explicit replay source enables replay; omitted `replay` inherits settings; replay without a source is 400. Explicit live selection overrides replay settings. Source runs must exist and match the clip. Only live runs require an existing MP4.
2. Active SSE uses `bus.subscribe(after)` to capture backlog and register live delivery atomically. Inactive runs stream a finite persisted backlog. IDs are zero-based string indexes, resume is exclusive, invalid cursors are 400, and cursors at/past terminal are 204. Each message has `id`, `event`, and JSON `data`. Streams close at terminal; `finally` explicitly closes subscriptions. An inactive interrupted run has a finite backlog rather than an endless subscription. Decisions made after terminal are read through the ads endpoint.
3. Final ads are selected only by `Run.ad_ids`, require a matching verdict, and include all generated attempts for that brief/format, ordered by attempt. Each attempt includes its ad, optional verdict, and `is_final`. Final responses include current decisions and judge-loop errors. Media URLs are additive HTTP-only fields; original artifacts and recorded events stay unchanged. SSE preserves the `JudgedAd` tuple-pair structure while adding URLs inside ad/moment payloads.
4. Decisions locate the persisted ad rather than constructing paths from unchecked IDs, verify the verdict and any duplicate body ID, write atomically, and use the active bus or a new `EventBus` for durable `ad_decided` emission. Per-run locks serialize decisions and export.
5. Export filters approved final ads, uses business/brief-hash/format filenames, writes images and manifest atomically, and removes stale exported PNGs. It returns IDs, decisions, relative paths, and media URLs. No zip is produced.
6. `GET /clips` merges manifest metadata with available MP4 files. Missing manifest clips remain visible with `available: false`. Paths are confined before use; media/clip serving uses `FileResponse` byte-range support.

## Interfaces

- Endpoints and bodies exactly as in `TECHNICAL_DESIGN.md`.
- `RunRegistry.get_bus(run_id) -> EventBus | None`, `RunRegistry.start(run, bus, pipeline)`. Background tasks are retained until completion, log unexpected exceptions, and are awaited during lifespan shutdown.
- Settings additions: `api_cors_origins: list[str] = ["http://localhost:5173"]`, `sample_clips_dir: Path = Path("sample_clips")`.
- Environment additions: `GOLDCOAST_API_CORS_ORIGINS` (JSON array) and `GOLDCOAST_SAMPLE_CLIPS_DIR`. Lifespan loads settings/seed data once and initializes store/registry; a lazy CORS wrapper reads that configuration on the first HTTP request. Importing the module does not require a key or `.env`. Tests inject settings through `create_app(settings)`.
- SSE event `id` is the zero-based line index in `events.jsonl` so `Last-Event-ID` maps directly to a resume offset.

## Error Handling

- Unknown run or ad: 404 with a JSON detail.
- Decision on an ad without a verdict: 409.
- Clip not found or outside `sample_clips/`: 400.
- Path traversal in media routes: 404, never a filesystem error.
- Pipeline exception inside the background task: the orchestrator already emits `run_failed`; the API logs the traceback and leaves the run record with status `failed`.
- Client disconnect on SSE: subscription is cleaned up in a `finally` block.

## Open Questions

- Whether to allow more than one active run at a time. Default: allow, since runs are independent, but the UI will focus on one.
- Whether export should also produce a zip. Default: no, a directory and manifest are enough for the demo.
