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

1. `POST /runs` validates the clip exists, creates the run through `RunStore`, registers an `EventBus` for it, and schedules `Pipeline.run` as a background task. The response is the `Run` with status `running`.
2. `GET /runs/{run_id}/events` reads `events.jsonl` for the backlog, then, if the run is active in the registry, subscribes to its bus and forwards events. Each SSE message has `id` set to the event's sequence, `event` set to the type, and `data` set to the event JSON. The stream closes after a terminal event.
3. `GET /runs/{run_id}/ads` reads ads and verdicts from the run directory, groups attempts by brief and format, marks the final attempt, and attaches any decision.
4. `POST /ads/{ad_id}/decision` locates the ad's run, writes the decision atomically, and emits `ad_decided` on the bus if the run is active, otherwise appends to the log directly.
5. Export filters approved decisions, copies files, and writes the manifest.

## Interfaces

- Endpoints and bodies exactly as in `TECHNICAL_DESIGN.md`.
- `RunRegistry.get_bus(run_id) -> EventBus | None`, `RunRegistry.start(run, coroutine)`.
- Settings additions: `api_cors_origins: list[str] = ["http://localhost:5173"]`, `sample_clips_dir: Path = Path("sample_clips")`.
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
