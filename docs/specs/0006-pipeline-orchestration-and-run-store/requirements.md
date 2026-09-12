# Requirements: 0006 Pipeline Orchestration and Run Store

## Goal

Run the whole flow from clip to judged ads as one unit that emits typed events, persists everything under a run directory, and can be replayed without the network. After this spec, `python -m goldcoast run <clip>` produces a complete run directory, and the same command with `GOLDCOAST_REPLAY=1` reproduces it from cached model calls.

## Functional Requirements

- `Pipeline.run(clip_path, replay=False) -> Run` that creates a run id and directory, then executes detect, match, generate, and judge for every moment, brief, and format.
- An in-process `EventBus` with `emit(event)` and `subscribe() -> AsyncIterator[PipelineEvent]`, where every emitted event is also appended to `events.jsonl` atomically before subscribers receive it.
- Events for every stage transition as listed in `TECHNICAL_DESIGN.md`, including `run_started`, `run_completed`, and `run_failed` with a readable reason.
- A `RunStore` that creates run directories, writes and reads `run.json`, lists runs, and reads moments, briefs, ads, verdicts, and decisions for a run.
- Replay mode: when enabled, the Gemini client reads recorded calls from `GOLDCOAST_REPLAY_RUN` by stage and sequence, and image outputs are copied from the source run. The new run directory is complete and independent of the source run.
- Per-run model call recording directory wired into the client so all calls land under `model_calls/`.
- Partial failure handling: a failing brief or format does not stop other briefs. The run completes with `run_completed` and a summary of failures in `run.json`.
- CLI `run` command with `--replay-from <run_id>` and a `runs` command that lists runs with status and counts.
- Tests running the full pipeline in replay mode from a committed fixture run, asserting the event sequence and the run directory contents.

## Inputs and Outputs

- Inputs: clip path, settings, seed data, optional source run for replay.
- Outputs: run directory with all artifacts, event log, `Run` record.

## Out of Scope

- HTTP API and SSE transport (0007). The event bus is in-process.
- Human decisions and export.
- Concurrency across runs.

## Dependencies

- 0001 through 0005.
- Project owner input: none beyond earlier specs.
