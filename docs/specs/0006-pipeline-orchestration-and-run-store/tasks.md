# Tasks: 0006 Pipeline Orchestration and Run Store

## Task List

- [ ] Implement run and child id generation in `src/goldcoast/pipeline/ids.py`.
- [ ] Implement `RunStore` in `src/goldcoast/pipeline/run_store.py` with atomic writes.
- [ ] Implement `EventBus` in `src/goldcoast/pipeline/events.py` with JSONL append and async subscription.
- [ ] Implement `ReplayClient` in `src/goldcoast/llm/replay.py` and a client factory that picks real or replay from settings.
- [ ] Implement `Pipeline.run` in `src/goldcoast/pipeline/orchestrator.py` with per-brief failure isolation.
- [ ] Wire the `run` and `runs` CLI commands.
- [ ] Execute one real end-to-end run and copy its directory to `tests/fixtures/runs/<fixture_run_id>/`, scrubbing nothing but confirming no secrets are present.
- [ ] Write `tests/test_pipeline.py` that replays the fixture run and asserts the event sequence, file layout, and `Run` contents.
- [ ] Update `README.md` with the `run` command and replay instructions.

## Validation Steps

```powershell
conda activate goldcoast
python -m goldcoast run sample_clips/<hype-clip>.mp4
python -m goldcoast runs
python -m goldcoast run sample_clips/<hype-clip>.mp4 --replay-from <run_id_from_previous_step>
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_pipeline.py
ruff check .
```

Expected: the first run finishes with `run_completed` and a directory containing frames, briefs, ads for each format, verdicts, `events.jsonl`, and `model_calls/`; the replay run produces the same set of files without network access; tests pass.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including the run id, a directory listing, and the event type sequence.
- `docs/FEATURE_STATUS.md` shows 0006 as Completed with a link to the evidence.
- The spec is committed on its own.
