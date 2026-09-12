# Status: 0006 Pipeline Orchestration and Run Store

## Status

Completed

## Evidence

Read all spec documents and shared contracts after 0005 commit 077a18a. The live
run will consume the analyzed manifest without a video model request. Replay
will copy recorded moments/frames and seed snapshots rather than depending on
the current editable manifest or re-extracting an uncommitted MP4. Child IDs are
rebased to the new run, retaining deterministic suffixes. Run gains typed failure
records and replay provenance; moment_skipped becomes an explicit event type.

### Validation — 2026-09-12

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_events_store.py tests/test_cli.py tests/test_models.py -p no:cacheprovider --basetemp output/pytest-tmp
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast run sample_clips/gymnastics_simone.mp4
python -m goldcoast runs
$env:GOLDCOAST_REPLAY = "1"
python -m goldcoast run sample_clips/gymnastics_simone.mp4 --replay-from 20260912-230559-0d2470
python C:/Users/amogh/AppData/Local/Temp/opencode/goldcoast_run_evidence.py
pytest tests/test_pipeline.py -p no:cacheprovider --basetemp output/pytest-tmp
pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
```

Final results all exit 0. Preliminary tests `13 passed in 0.61s`; pipeline tests
`4 passed in 30.39s`; regression `73 passed in 49.97s`; lint passes; `114 files
already formatted`. Initial async test setup exposed the blanket network guard
blocking Python's Windows socketpair used internally to wake the event loop. The
guard now exempts only calls directly from the stdlib socketpair function's code
object; application socket connections and create_connection remain denied.

Actual live run: **20260912-230559-0d2470**, started
2026-09-12T23:05:59.939419Z, completed 23:10:47.237277Z. Three moments, six briefs,
twelve final judged ads, no pipeline failures. Every final ad passed with overall
7. There were 17 generation attempts and 17 judge calls, plus three reranking and
three style calls: exactly 40 recorded generation requests. Zero video calls.
Five ads needed one regeneration; none exceeded the default cap.

`runs` printed:
```text
20260912-230559-0d2470 completed moments=3 briefs=6 ads=12 failures=0 replay=False
```

Replay **20260912-231210-6155ce** completed in about 14 seconds with the same
3/6/12 counts, final attempt choices, and no failures. Automated tests compare
every replayed image byte-for-byte, verify the event type sequence, then remove
the installed original source and successfully replay the replay itself. They
replace both VideoAgent.detect and GeminiClient construction with failures, so
neither video decoding nor live-client creation can silently occur. Separate
tests cover a missing record, wrong clip, threaded event handoff/resume/cleanup,
event persistence failure, confined run IDs, and isolated format finalization
failure without stopping other briefs.

Complete source directory copied unchanged to
`tests/fixtures/runs/20260912-230559-0d2470/`. Inspection confirms no MP4, .env, or
API key in its JSON. Total size 65,822,062 bytes; all image and HTTP evidence is
retained. Directory inventory:

```text
run.json; settings.json (no secrets); clip_manifest.json; events.jsonl
frames/       3 PNGs
moments/      3 JSONs
briefs/       6 JSONs
ads/          17 PNGs + 17 sidecars, business/brief-key/format scoped
verdicts/     17 JSONs
seed/         12 JSON, source-note, and asset files
model_calls/  40 call JSONs + 17 original JPEGs + 40 HTTP journals
```

Event sequence from the real run (identical types on replay):

```text
run_started clip_loaded clip_manifest_hit
moment_detected frame_extracted athlete_resolved business_matched brief_created
ad_generating ad_generated ad_judged ad_final
ad_generating ad_generated ad_judged ad_regenerating ad_generating ad_generated ad_judged ad_final
business_matched brief_created
ad_generating ad_generated ad_judged ad_regenerating ad_generating ad_generated ad_judged ad_final
ad_generating ad_generated ad_judged ad_final
moment_detected frame_extracted athlete_resolved business_matched brief_created
ad_generating ad_generated ad_judged ad_regenerating ad_generating ad_generated ad_judged ad_final
ad_generating ad_generated ad_judged ad_final
business_matched brief_created
ad_generating ad_generated ad_judged ad_final
ad_generating ad_generated ad_judged ad_final
moment_detected frame_extracted athlete_resolved business_matched brief_created
ad_generating ad_generated ad_judged ad_regenerating ad_generating ad_generated ad_judged ad_final
ad_generating ad_generated ad_judged ad_final
business_matched brief_created
ad_generating ad_generated ad_judged ad_final
ad_generating ad_generated ad_judged ad_regenerating ad_generating ad_generated ad_judged ad_final
run_completed
```

Shared-contract updates cover typed failures/replay provenance, seed/settings/
manifest snapshots, replayed frame copying, run-local reader paths, and atomic
backlog/live subscription. The API can pass a pre-created run and bus into the
pipeline so it returns promptly without allocating a duplicate run.

## Blockers

None.

## Change Log

- 2026-09-12: Spec created.
- 2026-09-12: Completed the real full run, independent replay and replay-of-replay validation, recorded the complete fixture, and passed all 73 Python tests.
