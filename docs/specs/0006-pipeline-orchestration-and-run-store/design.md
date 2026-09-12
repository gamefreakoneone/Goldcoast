# Design: 0006 Pipeline Orchestration and Run Store

## Overview

This spec adds the glue that makes the agents a product. The orchestrator owns the run lifecycle, the event bus makes progress observable, the run store makes results durable and queryable, and replay mode makes demos safe.

## Components

- `src/goldcoast/pipeline/run_store.py`: `RunStore(output_dir)` with `create_run(clip_path, replay) -> Run`, `save_run(run)`, `get_run(run_id)`, `list_runs()`, `run_dir(run_id)`, and typed readers `moments(run_id)`, `briefs(run_id)`, `ads(run_id)`, `verdicts(run_id)`, `decisions(run_id)`.
- `src/goldcoast/pipeline/events.py`: `EventBus(run_dir)` with `emit(type, payload)`, `subscribe()`, `backlog()`, and the atomic JSONL append.
- `src/goldcoast/pipeline/orchestrator.py`: `Pipeline(settings, seed, run_store)` with `run(clip_path, replay_from=None) -> Run`.
- `src/goldcoast/llm/replay.py`: `ReplayClient(source_run_dir)` implementing the same interface as `GeminiClient`, reading `model_calls/<stage>_<sequence>.json` and copying image outputs.
- `src/goldcoast/pipeline/ids.py`: run id format `YYYYMMDD-HHMMSS-<6 hex>` and deterministic child ids derived from parent ids and sequence so replays produce matching ids.
- `src/goldcoast/cli.py`: `run` and `runs` commands.
- `tests/test_pipeline.py`, `tests/fixtures/runs/<fixture_run_id>/` containing a full recorded run.

## Data Flow

1. `run` creates the run directory and `run.json` with status `running`, builds the client (real or replay) pointed at `model_calls/`, and constructs the four agents with the run directory as output.
2. Emit `run_started` and `clip_loaded`. Call `VideoAgent.detect`, which consults the clip manifest first. On a manifest hit emit `clip_manifest_hit`. For each moment, emit `moment_detected` and `frame_extracted`.
3. For each moment, call `MatchingAgent.match`. Emit `athlete_resolved`, one `business_matched` per brief, and `brief_created`.
4. For each brief and each format, call `judge_loop` with the bus's `emit` so it produces `ad_generating`, `ad_generated`, `ad_judged`, `ad_regenerating`, and `ad_final`.
5. Update `run.json` with all ids and failures, set status `completed`, emit `run_completed`. On an unrecoverable error (clip unreadable, athlete unresolved for every moment), set status `failed` and emit `run_failed`.

## Interfaces

- `Pipeline.run(clip_path: Path, replay_from: str | None = None) -> Run`.
- `EventBus.emit(type: PipelineEventType, payload: dict) -> PipelineEvent`, `EventBus.subscribe() -> AsyncIterator[PipelineEvent]`, `EventBus.backlog() -> list[PipelineEvent]`.
- `RunStore` methods as listed under Components.
- CLI: `goldcoast run <clip> [--replay-from RUN_ID]`, `goldcoast runs`.
- Settings: `replay` and `replay_run` from spec 0001 map to `--replay-from`.
- Event payloads carry the full model for the stage output (for example `moment_detected.payload = HypeMoment`) so the UI needs no extra fetch to render a step.

## Error Handling

- Any agent exception inside a brief or format is caught, logged as an `ad_failed` payload on `run_completed.failures`, and does not stop other work.
- `AthleteUnresolvedError` for a moment skips that moment with a `moment_skipped` event carrying the reason.
- `ReplayMissError` fails the run with a clear message naming the missing stage and sequence.
- Event append failure is fatal, since the log is the source of truth for the UI.

## Open Questions

- Whether formats for one brief should generate concurrently. Default: sequential in this spec, with the loop structured so `asyncio.gather` can be introduced later.
- Whether replay should allow a different clip than the source run. Default: no, the clip path must match the source run's `run.json`.
