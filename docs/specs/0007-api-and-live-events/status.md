# Status: 0007 API and Live Events

## Status

Completed

## Evidence

### Automated validation

Commands run from the repository root in PowerShell:

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "1"
pytest tests/test_api.py -p no:cacheprovider --basetemp output/pytest-tmp
pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
```

Relevant output:

```text
tests/test_api.py: 11 passed, 2 warnings in 23.19s
Full suite: 87 passed, 2 warnings in 78.81s
ruff check .: All checks passed!
ruff format --check .: 129 files already formatted
```

Warnings are dependency deprecations from Starlette's httpx TestClient and the
AnyIO BlockingPortal alias. No tests were skipped. The existing network guard,
including its narrow stdlib Windows socketpair exception, is unchanged.

Coverage includes the actual full fixture replay through POST/SSE, byte-identical
ads, 17 attempts versus 12 final selections, five criterion scores plus overall,
non-latest/failing final selection, approval updates and persistence across app
restart, 12 collision-free exports and re-export after rejection, unknown resources,
missing/mismatched verdicts, CORS, MP4 byte ranges, replay without the MP4, no live
client/detection, missing recording failure, and unexpected worker failure.
Direct ASGI streaming verifies delivery before worker completion, disconnect
cleanup, exclusive resume, and two concurrent independent runs. Windows junctions
exercise real directory-escape rejection without requiring symlink privileges.

The initial targeted run found a Windows reader/writer collision during atomic
replacement of `run.json` (WinError 5). A small bounded retry in the shared atomic
writer fixes this; regression tests verify successful retry, bounded failure,
preserved original content, and temporary-file cleanup. Both subsequent validation
commands above passed.

### Real HTTP replay

Source live run: **20260912-230559-0d2470**. Full committed fixture:
`tests/fixtures/runs/20260912-230559-0d2470/`.

API-created replay: **20260912-235123-6424eb**.

The harness does not retain background processes across shell calls, so the
manual driver launches Uvicorn, performs the HTTP checks in the same invocation,
and stops its process tree afterward. It uses only localhost HTTP and recorded
pipeline responses. Exact driver command:

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
python output/manual/0007/validate_http.py
```

Server command executed with `GOLDCOAST_REPLAY=1` and
`GOLDCOAST_REPLAY_RUN=20260912-230559-0d2470`:

```powershell
uvicorn goldcoast.api.app:app --reload
```

Startup output:

```text
Uvicorn running on http://127.0.0.1:8000
Started reloader process [58140] using WatchFiles
Started server process [56808]
Application startup complete.
```

Exact curl commands emitted by the driver:

```powershell
curl.exe --fail-with-body -sS -X POST -H "Content-Type: application/json" --data-binary @C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\run-create.json http://localhost:8000/runs -o C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\run-created.json -w "HTTP %{http_code}; %{time_total}s\n"
curl.exe --fail-with-body -sS -N http://localhost:8000/runs/20260912-235123-6424eb/events -o C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\events.sse -w "HTTP %{http_code}; %{time_total}s\n"
curl.exe --fail-with-body -sS http://localhost:8000/runs/20260912-235123-6424eb/ads -o C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\ads.json -w "HTTP %{http_code}; %{time_total}s\n"
curl.exe --fail-with-body -sS -X POST -H "Content-Type: application/json" --data-binary @C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\decision-0.json http://localhost:8000/ads/20260912-235123-6424eb-moment-1-brief-yama-sushi-marketplace-koreatown-landscape-attempt-1/decision -o C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\decision-result-0.json -w "HTTP %{http_code}; %{time_total}s\n"
curl.exe --fail-with-body -sS -X POST -H "Content-Type: application/json" --data-binary @C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\decision-4.json http://localhost:8000/ads/20260912-235123-6424eb-moment-2-brief-yama-sushi-marketplace-koreatown-landscape-attempt-2/decision -o C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\decision-result-4.json -w "HTTP %{http_code}; %{time_total}s\n"
curl.exe --fail-with-body -sS http://localhost:8000/runs/20260912-235123-6424eb/export -o C:\Users\amogh\Desktop\Goldcoast\output\manual\0007\export.json -w "HTTP %{http_code}; %{time_total}s\n"
```

Request bodies:

```json
{"clip_path":"sample_clips/gymnastics_simone.mp4","replay_from":"20260912-230559-0d2470"}
```

```json
{"ad_id":"20260912-235123-6424eb-moment-1-brief-yama-sushi-marketplace-koreatown-landscape-attempt-1","decision":"approved","reviewer":"demo","note":""}
```

The second decision has the corresponding moment-2/attempt-2 ID shown above.

Relevant output:

```text
POST /runs: HTTP 201; 0.251033s (returned status running)
GET /events: HTTP 200; 10.577330s (closed after run_completed)
GET /ads: HTTP 200; 0.714697s
First decision: HTTP 200; 0.254490s
Second decision: HTTP 200; 0.444217s
GET /export: HTTP 200; 0.317984s
```

```json
{
  "source_run": "20260912-230559-0d2470",
  "api_run": "20260912-235123-6424eb",
  "status": "completed",
  "events_through_terminal": 93,
  "moments": 3,
  "briefs": 6,
  "final_ads": 12,
  "attempts": 17,
  "approved_exported": 2,
  "video_range_status": 206,
  "frame_timestamps": [122.5, 41.0, 91.5],
  "failures": [],
  "recorded_http_requests": 0
}
```

The manual driver verified ordered event IDs 0 through 92, required passing
verdicts (overall 7), decisions visible on refetch, both exported images identical
to their originals, frame URLs responding successfully, and a 1024-byte MP4 range
response. Reconnecting with Last-Event-ID 2 resumed at 3; a terminal cursor returned
204. Two landscape ads for the same business from different moments exported to
distinct paths. All validation used recordings; there were no Gemini requests or
video reanalysis. The API server was stopped after validation; no UI was started.

SSE excerpt (full capture: `output/manual/0007/events.sse`):

```text
id: 0
event: run_started
data: {"id":"0","run_id":"20260912-235123-6424eb","type":"run_started","timestamp":"2026-09-12T23:51:23.035526Z","payload":{"id":"20260912-235123-6424eb","clip_path":"sample_clips\\gymnastics_simone.mp4","status":"running","started_at":"2026-09-12T23:51:23.018521Z","finished_at":null,"replay":true,"moment_ids":[],"brief_ids":[],"ad_ids":[],"failures":[],"replay_from":"20260912-230559-0d2470"}}

id: 1
event: clip_loaded
data: {"id":"1","run_id":"20260912-235123-6424eb","type":"clip_loaded","timestamp":"2026-09-12T23:51:23.046050Z","payload":{"clip_path":"sample_clips\\gymnastics_simone.mp4"}}
```

Export manifest (full response: `output/manual/0007/export.json`):

```json
{
  "run_id": "20260912-235123-6424eb",
  "exported_at": "2026-09-12T23:51:37.796378Z",
  "ads": [
    {
      "ad_id": "20260912-235123-6424eb-moment-1-brief-yama-sushi-marketplace-koreatown-landscape-attempt-1",
      "brief_id": "20260912-235123-6424eb-moment-1-brief-yama-sushi-marketplace-koreatown",
      "business_id": "yama-sushi-marketplace-koreatown",
      "format": "landscape",
      "path": "approved/yama-sushi-marketplace-koreatown_brief_426a5e194e06_landscape.png",
      "image_url": "/media/20260912-235123-6424eb/approved/yama-sushi-marketplace-koreatown_brief_426a5e194e06_landscape.png",
      "decision": {
        "ad_id": "20260912-235123-6424eb-moment-1-brief-yama-sushi-marketplace-koreatown-landscape-attempt-1",
        "decision": "approved", "reviewer": "demo", "note": "",
        "decided_at": "2026-09-12T23:51:34.811868Z"
      }
    },
    {
      "ad_id": "20260912-235123-6424eb-moment-2-brief-yama-sushi-marketplace-koreatown-landscape-attempt-2",
      "brief_id": "20260912-235123-6424eb-moment-2-brief-yama-sushi-marketplace-koreatown",
      "business_id": "yama-sushi-marketplace-koreatown",
      "format": "landscape",
      "path": "approved/yama-sushi-marketplace-koreatown_brief_704e72802d1a_landscape.png",
      "image_url": "/media/20260912-235123-6424eb/approved/yama-sushi-marketplace-koreatown_brief_704e72802d1a_landscape.png",
      "decision": {
        "ad_id": "20260912-235123-6424eb-moment-2-brief-yama-sushi-marketplace-koreatown-landscape-attempt-2",
        "decision": "approved", "reviewer": "demo", "note": "",
        "decided_at": "2026-09-12T23:51:35.234090Z"
      }
    }
  ]
}
```

### CLI replay check

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "1"
$env:GOLDCOAST_REPLAY_RUN = "20260912-230559-0d2470"
python -m goldcoast run sample_clips/gymnastics_simone.mp4 --replay-from 20260912-230559-0d2470
```

Output: run `20260912-235158-67038f`, status `completed`, 3 moments, 6 briefs,
12 final ads, `failures: []`, replay source `20260912-230559-0d2470`.
Started `2026-09-12T23:51:58.575250Z`; finished `2026-09-12T23:52:10.174577Z`.

## Blockers

None.

## Change Log

- 2026-09-12: Spec created.
- 2026-09-12: Started 0007. Reconciled clip listing, explicit replay selection, final-ad history/media responses, brief-namespaced exports, and atomic SSE subscription with the implemented 0006 contracts. Existing live run 20260912-230559-0d2470 supplies all validation recordings; no live model calls are needed.
- 2026-09-12: Completed the single-process FastAPI demo, offline tests, and real HTTP replay. Shared changes in TECHNICAL_DESIGN.md document additive HTTP media fields, required final verdicts/history, replay precedence, clip listing, terminal SSE semantics, brief-specific exports, and bounded Windows atomic-replacement retries. Updated README with API/CLI demo commands. Spec 0008 remains Not started.
