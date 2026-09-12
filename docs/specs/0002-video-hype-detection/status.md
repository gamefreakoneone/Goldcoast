# Status: 0002 Video Hype Detection

## Status

Completed

## Evidence

### Successful final validation — 2026-09-12

After the user added credits and requested continuation, the same configured model returned its first usable analysis. This establishes success after the credit addition, not that billing caused the earlier 503 errors. No `--force-analysis` was used. All subsequent detections used the analyzed manifest.

```powershell
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast detect sample_clips/gymnastics_simone.mp4 --out output/manual/0002
python -m goldcoast clips
python -m goldcoast detect sample_clips/gymnastics_simone.mp4 --out output/manual/0002-again
```

All exited 0. First successful response: `output/manual/0002/model_calls/video_detect_3.json`, timestamp `2026-09-12T22:11:40.974639Z`, latency `9262 ms`, model/version `gemini-3.8-flash`, response ID `Hs6lavqjDb79qtsPxIWUkAk`. Usage: 12,015 input tokens (11,830 video), 632 candidate tokens, 1,349 thinking tokens, 13,996 total. The active Files API upload was reused. The successful record was copied byte-for-byte to `tests/fixtures/model_calls/video/video_detect_1.json`; only the filename expresses its position in the replay scenario, and original `sequence: 3` is retained as documented in the fixture README.

Detected results (full records are `output/manual/0002/moments/0002-moment-{1,2,3}.json`):

| Moment | Start/end seconds | Best frame | Score | Description |
|---|---|---|---|---|
| 0002-moment-1 | 106–125 | 122.5 | 7.8 | Final pass and standing ovation |
| 0002-moment-2 | 36.5–43 | 41.0 | 7.2 | Opening tumbling pass |
| 0002-moment-3 | 87.5–94 | 91.5 | 6.8 | Third tumbling pass |

Each record carries `athlete_id: simone-biles`, `sport: gymnastics`, `source: gemini`, and a PNG at `output/manual/0002/frames/<moment_id>.png`. `clips` printed `gymnastics_simone.mp4 True simone-biles 122.5, 41.0, 91.5`. The second detection returned identical moment content with fresh run-scoped IDs and PNG paths. Its `model_calls/` directory was inspected and contains zero entries.

Manual check: opened the primary PNG and observed a smiling athlete with arms raised against the standing crowd. Temporarily edited the manifest's first timestamp from 122.5 to 120.5 and `analyzed_by` to `manual`, reran the exact second `detect` command, and opened `output/manual/0002-again/frames/0002-again-moment-1.png`. It visibly changed to a side-facing smile with arms lowered. The output reported `best_frame_s: 120.5` and `source: manual`; `model_calls/` remained empty. Restored the original 122.5 timestamp and `analyzed_by: gemini` after this comparison. Both original and alternate PNGs remain under ignored `output/manual/` for inspection.

```powershell
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_video_agent.py -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
```

Results: `12 passed in 6.35s`; `All checks passed!`; `80 files already formatted`. The real-response tests now pass, and the empty fixture produces an analyzed entry with zero moments. Socket connections are denied by the test suite.

Final regression: `$env:GOLDCOAST_REPLAY = "1"; pytest -p no:cacheprovider --basetemp output/pytest-tmp` → `35 passed in 6.59s`.

### SDK documentation prerequisite

Used Context7 MCP v4.1.0 over stdio via `npx -y @upstash/context7-mcp`. A temporary protocol client under `%TEMP%/opencode/goldcoast_mcp.py` sent MCP initialize, initialized notification, and tools/call requests. `resolve-library-id` returned unrelated libraries, so subsequent `query-docs` requests targeted the official `/googleapis/python-genai` library directly.

Queries covered Files API upload and activation, structured output, reference images, generated image bytes, and aspect ratios. Context7 returned the official `README.md`, `docs/index.html`, `google/genai/files.py`, `google/genai/types.py`, and `_transformers.py` sources from https://github.com/googleapis/python-genai.

Confirmed before writing SDK code:

- `client.files.upload(file=path, config=types.UploadFileConfig(mime_type="video/mp4"))`; poll `client.files.get(name=uploaded.name)` until `FileState.ACTIVE`, rejecting `FAILED` and bounding the wait. A File becomes a URI part, or use `Part.from_uri(file_uri=uploaded.uri, mime_type="video/mp4")`.
- `GenerateContentConfig(response_mime_type="application/json", response_schema=PydanticModel)` requests structured JSON.
- Supply text and ordered `Part.from_bytes(data=image_bytes, mime_type=...)` image references in `contents`.
- The documented image example uses `gemini-3.1-flash-image`, `response_modalities=["IMAGE"]`, and `image_config=types.ImageConfig(aspect_ratio="9:16")`. The `ImageConfig` source explicitly lists both `16:9` and `9:16` as supported.
- Iterate `response.parts`, select `part.inline_data`, and use `part.as_image()` for the generated image; the inline Blob carries `data` bytes.

### Contract changes

Read TECHNICAL_DESIGN.md before changing shared models. Documented moment-level `source`, nullable `best_frame_path` for extraction failure, persisted `moments/<id>.json`, settings, and the analyzed-empty manifest cache rule. Added a small recorded-response reader now because 0002 requires replay tests; full run replay remains 0006.

### Live validation and blocker

Each non-interactive PowerShell command loaded the Conda hook and activated the environment:

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast detect sample_clips/gymnastics_simone.mp4 --out output/manual/0002
```

The clip probed successfully as 130.519 seconds. Its size selected the Files API upload path, and activation succeeded. The first generation request was rejected before analysis with:

```text
400 INVALID_ARGUMENT. Invalid JSON payload received. Unknown name "additional_properties" at 'generation_config.response_schema': Cannot find field.
```

The same unsupported field was reported at `generation_config.response_schema.properties[1].value.items` and its nested athlete-hints schema. Preserved the exact complete request/error in `output/manual/0002-schema-rejected/model_calls/video_detect_1.json`. Corrected the wire-schema adapter to resolve references, encode nullable fields, and omit unsupported `additionalProperties`, defaults, and titles while retaining strict Pydantic validation of returned JSON. A regression test checks this behavior.

Reran the same `detect` command after the correction. Result, exit code 1:

```text
Gemini call failed during stage 'video_detect': 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
```

Preserved this request/error in `output/manual/0002-unavailable/model_calls/video_detect_1.json`. Retried after a bounded wait:

```powershell
Start-Sleep -Seconds 30
python -m goldcoast detect sample_clips/gymnastics_simone.mp4 --out output/manual/0002
```

Result: the identical `503 UNAVAILABLE` error, exit code 1. Final request/error is in `output/manual/0002/model_calls/video_detect_1.json`, timestamp `2026-09-12T21:55:59.845773Z`, recorded latency `52779 ms`.

No successful analysis response was obtained. No live `--force-analysis` was used, no hype moments were fabricated, and the manifest remains unchanged and unanalyzed. The two unavailable requests followed a schema rejection; none returned a reusable analysis. The live manifest-hit and manual timestamp/frame comparison validations cannot run until the first analysis succeeds. Running `detect ... --out output/manual/0002-again` now would submit another live analysis request, not test a cache hit, so that dependent command was not run.

```powershell
python -m goldcoast clips
```

Output, exit code 0:

```text
clip                    analyzed  athlete_id    best_frame_s
gymnastics_simone.mp4    False     simone-biles
```

### Automated validation

Used the user-prescribed Windows temporary-directory fallback established during housekeeping:

```powershell
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_video_agent.py -p no:cacheprovider --basetemp output/pytest-tmp
```

Result: `2 failed, 10 passed in 5.02s`. Both failures are `ReplayMissError` for the absent real fixture `tests/fixtures/model_calls/video/video_detect_1.json`, in `test_real_recording_replays_and_persists_manifest` and `test_force_preserves_curated_athlete_and_notes`.

```powershell
$env:GOLDCOAST_REPLAY = "1"; pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
```

Results: `2 failed, 32 passed in 5.95s` (the same missing real fixture); `All checks passed!`; `79 files already formatted`. Formatting was applied with `ruff format .` before these final checks. Tests block socket connections automatically; ffmpeg test videos are generated only in the ignored pytest temporary directory. Passing checks cover manifest hits and edits with fresh PNGs and zero calls, empty-response caching, invalid manifest and timestamps, overlap/threshold logic, candidate extraction, clip-source confinement, Files API polling and processing failure, strict local versus compatible wire schemas, and the existing scaffold tests.

### Manual checks

The real clip was found and probed, and its Files API upload became active, but Gemini returned no moments. Consequently there is no detected frame to visually inspect and no valid timestamp to adjust for the required real-clip comparison. That manual check remains incomplete; no screenshot or successful comparison is claimed. Automated extraction checks used a synthetic changing video, confirmed different timestamps produced different PNG bytes, and verified no model call occurred on cache hits.

## Blockers

None. The first usable response was obtained and final validation passed. The following paragraphs preserve the resolved investigation history.

### Resolved availability and request-count investigation

`gemini-3.8-flash` returned the exact `503 UNAVAILABLE` high-demand error above. The user subsequently requested continuing with the same model and reported approximately 20 dashboard API calls but only one error. Resumed 0002 to reconcile request accounting and retry with HTTP-level logging and uploaded-video reuse. The audited retry again returned 503, so 0002 is Blocked again. No later spec has started.

Installed SDK investigation: `google-genai 2.23.0` uses 8 MiB upload chunks; file initialization, chunks, and activation polling create additional API requests. `_api_client.retry_args(None)` uses one attempt, and the previous client configuration left `retry_options=None`, so hidden generation retries are not established as the cause of the dashboard count. The three application-level generation records show one 400 and two 503 errors; without prior HTTP-level traces or the dashboard's method/time breakdown, exact dashboard accounting and billing cannot be determined. No usable analysis reached the application, which is distinct from claiming no provider-side processing or charges.

Context7 confirmed `HttpRetryOptions(attempts=1)` includes the initial attempt and disables retries. Made this explicit, added per-request HTTP journals containing method/path/status/timing (no headers, bodies, or URL query secrets), and reusable uploaded-file metadata. Existing recorded upload URIs may be recovered for the unchanged input clip, so resuming in the same output directory avoids another multipart upload.

### Audited attempt after the user's request to continue

Before another live call, ran:

```powershell
pytest tests/test_llm_client.py tests/test_video_agent.py -p no:cacheprovider --basetemp output/pytest-tmp -k "not real_recording and not force_preserves"
ruff format .
ruff check .
```

Results: `13 passed, 2 deselected in 4.66s`; formatting succeeded; `All checks passed!`. The new test exercises the actual SDK against `httpx.MockTransport`, asserts exactly one HTTP request on a 503, and checks the audit contains status/path without the key. Upload tests verify a second request reuses the active uploaded file.

```powershell
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast detect sample_clips/gymnastics_simone.mp4 --out output/manual/0002
```

Result: exit 1 with the same exact 503 message above. `output/manual/0002/model_calls/video_detect_2.json` records timestamp `2026-09-12T22:04:20.806337Z`, model `gemini-3.8-flash`, and latency `10183 ms`.

Exactly two HTTP requests were recorded for this invocation:

| UTC timestamp | Method/path | HTTP status | Latency |
|---|---|---|---|
| 2026-09-12T22:04:20.623341+00:00 | GET /v1beta/files/apyp2a8yftg6 | 200 | 148 ms |
| 2026-09-12T22:04:20.828347+00:00 | POST /v1beta/models/gemini-3.8-flash:generateContent | 503 | 10153 ms |

Trace files: `output/manual/0002/model_calls/http_requests/9df4e1ae3497463f8e37cf95ce7550cb.json` and `af265e10a2684fc5a7ca6d0f33105218.json`. The reused upload is ACTIVE, size 41,211,440 bytes, expiration `2026-09-14T21:55:52.185880+00:00`. No upload, extra generation request, or text-repair request occurred in this invocation.

The application has now recorded four generation invocations total: one schema rejection and three 503 errors. No usable analysis has been received. The final audited request confirms provider unavailability rather than an upload failure; no authentication or quota error was returned. A dashboard breakdown by API method at the exact UTC timestamps above can help reconcile the user's observed counters. Previous invocation HTTP counts and charges cannot be inferred from the application-level records alone.

Final regression commands after the HTTP accounting changes:

```powershell
$env:GOLDCOAST_REPLAY = "1"; pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
git diff --check
```

Results: `2 failed, 33 passed in 5.19s` (only the two real-fixture-dependent tests above); `All checks passed!`; `79 files already formatted`; diff check exit 0. This is a partial implementation commit, not completion evidence.

### Resume when the configured model is available

Preserve the failed-call directories above. Reuse the same output directory so the active upload can be reused while it remains available:

```powershell
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast detect sample_clips/gymnastics_simone.mp4 --out output/manual/0002
```

After success, retain the real successful call records as fixtures (preserving their original recorded sequences and documenting the fixture replay ordering), finish 0002's repeated detection and manual edit checks, use its actual moment paths for 0003, and complete the remaining specs in order. Do not pass `--force-analysis` unless a successful first analysis is unusable and that decision is recorded here.

## Change Log

- 2026-09-12: Spec created.
- 2026-09-12: Started after housekeeping commit 28e93f1. Verifying current SDK documentation through Context7 before SDK implementation.
- 2026-09-12: Implemented the detector, Files API handling, frame extraction/candidate pick, manifest helpers/cache, replay reader, structured-response adapter, settings, CLI, and local tests. Recorded Context7 verification and shared-contract changes.
- 2026-09-12: Marked Blocked after two 503 responses. Real-fixture tasks and dependent live validations remain incomplete. Stopped before 0003.
- 2026-09-12: User requested continuing with gemini-3.8-flash. Resumed In progress, investigated SDK request counts without a Gemini call, and added HTTP auditing, explicit one-attempt requests, and upload reuse before the next live attempt.
- 2026-09-12: Audited retry reused an ACTIVE upload and sent exactly one generateContent HTTP request, which returned 503. Marked Blocked again; 0003–0008 remain Not started.
- 2026-09-12: User confirmed three 503 errors in API logs, added credits, and requested another attempt on spec 0002. Resumed In progress with the same model and cached upload. The reported 503 does not itself establish a billing failure.
- 2026-09-12: First successful live analysis obtained; recorded the real fixture, verified manifest-hit detection and a manual timestamp/frame change, restored the baseline manifest, and passed all 12 video tests.
- 2026-09-12: All 35 Python tests passed; marked Completed before starting 0003.
