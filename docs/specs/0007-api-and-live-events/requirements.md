# Requirements: 0007 API and Live Events

## Goal

Expose the pipeline over HTTP so the web UI can start runs, watch progress live, view ads with their verdicts, and record approval decisions. After this spec, the API serves every endpoint in `TECHNICAL_DESIGN.md` and a browser can follow a run's events as they happen.

## Functional Requirements

- FastAPI application at `goldcoast.api.app:app` with all endpoints listed under API shapes in `TECHNICAL_DESIGN.md`.
- `POST /runs` starts a pipeline run in a background task and returns immediately with the `Run` record.
- `GET /runs/{run_id}/events` streams Server-Sent Events: first the backlog from `events.jsonl`, then live events until `run_completed` or `run_failed`, then closes. Reconnects with `Last-Event-ID` resume strictly after that event. A cursor at or beyond the terminal event returns 204; invalid cursors return 400. Disconnected subscriptions are closed.
- `GET /runs/{run_id}/ads` returns each final ad with its verdict, all attempts, and any decision.
- `POST /ads/{ad_id}/decision` records an `ApprovalDecision` to `decisions/<ad_id>.json`, emits `ad_decided`, and rejects decisions for ads without a verdict.
- `GET /runs/{run_id}/export` copies currently approved final ads to `approved/<business_id>_brief_<12-character-brief-hash>_<format>.png`, writes `approved/manifest.json`, and returns the manifest with media URLs. Re-export removes stale exported PNGs after approval changes.
- Static serving for run media under `/media/{run_id}/{path}` and clips under `/clips/{name}`, restricted to the run and clip directories with path traversal rejected.
- `GET /clips` lists MP4 files and manifest entries with availability, metadata, analysis status, and playable URLs. Clip serving supports byte ranges for browser seeking.
- Seed endpoints returning athletes, businesses, and ad styles for the UI's detail panels.
- CORS enabled for the Vite dev server origin.
- Replay support: `POST /runs` accepts `replay_from` so the demo can run from cached outputs through the same UI.
- Omitted `replay` inherits settings; explicit `replay_from` enables replay. Replay requires a source and a matching confined clip path, but does not require the source MP4. Live runs require an existing clip. Synchronous pipeline work runs off the event loop.
- Tests using the FastAPI test client against the fixture run from spec 0006, covering the event stream, ads listing, decisions, export, and path traversal rejection.

## Inputs and Outputs

- Inputs: HTTP requests, run directories, seed data.
- Outputs: JSON responses, SSE stream, media files, decision and export files.

## Out of Scope

- Authentication and multi-user access.
- The frontend (0008).
- Deleting runs.

## Dependencies

- 0006 for `Pipeline`, `RunStore`, and `EventBus`.
- Project owner input: none beyond earlier specs.
