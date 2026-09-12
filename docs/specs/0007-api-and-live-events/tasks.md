# Tasks: 0007 API and Live Events

## Task List

- [x] Reconcile shared/spec contracts for clips, replay, final ads, media URLs, exports, and SSE.
- [x] Implement the app factory, lifespan, and CORS in `src/goldcoast/api/app.py`.
- [x] Implement dependencies and `RunRegistry` in `src/goldcoast/api/deps.py`.
- [x] Implement request and response schemas in `src/goldcoast/api/schemas.py`.
- [x] Implement the runs router including export.
- [x] Implement the SSE events router with backlog, live forwarding, `Last-Event-ID` resume, and cleanup on disconnect.
- [x] Implement the decisions router with verdict precondition.
- [x] Implement the media and clips routers with safe path resolution.
- [x] Implement the seed router.
- [x] Add `api_cors_origins` and `sample_clips_dir` to settings and `.env.example`.
- [x] Write `tests/test_api.py` against the fixture run, including a replay run started through `POST /runs` and consumed through the SSE endpoint.
- [x] Update `README.md` with the API run command.

## Validation Steps

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "1"
$env:GOLDCOAST_REPLAY_RUN = "20260912-230559-0d2470"
uvicorn goldcoast.api.app:app --reload
```

In a second terminal:

```powershell
$run = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/runs" -ContentType "application/json" -Body '{"clip_path":"sample_clips/gymnastics_simone.mp4","replay_from":"20260912-230559-0d2470"}'
curl.exe -N "http://localhost:8000/runs/$($run.id)/events"
$ads = Invoke-RestMethod "http://localhost:8000/runs/$($run.id)/ads"
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/ads/$($ads[0].id)/decision" -ContentType "application/json" -Body '{"decision":"approved","reviewer":"demo","note":""}'
Invoke-RestMethod "http://localhost:8000/runs/$($run.id)/export"
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_api.py -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
```

`curl.exe --data-binary @<request.json>` is an equivalent way to submit these bodies
and was used for the recorded HTTP evidence. This avoids native PowerShell 5.1
inline JSON quoting problems. Full HTTP captures are under `output/manual/0007/`.

Expected: the events stream prints events in order and closes after `run_completed`; the ads listing shows a verdict on every final ad; the decision is accepted and appears on the next ads listing; export lists the approved file; tests pass.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including a sample of the SSE output and the export manifest.
- `docs/FEATURE_STATUS.md` shows 0007 as Completed with a link to the evidence.
- The spec is committed on its own.
