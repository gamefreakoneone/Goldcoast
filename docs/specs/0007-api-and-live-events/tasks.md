# Tasks: 0007 API and Live Events

## Task List

- [ ] Implement the app factory, lifespan, and CORS in `src/goldcoast/api/app.py`.
- [ ] Implement dependencies and `RunRegistry` in `src/goldcoast/api/deps.py`.
- [ ] Implement request and response schemas in `src/goldcoast/api/schemas.py`.
- [ ] Implement the runs router including export.
- [ ] Implement the SSE events router with backlog, live forwarding, `Last-Event-ID` resume, and cleanup on disconnect.
- [ ] Implement the decisions router with verdict precondition.
- [ ] Implement the media and clips routers with safe path resolution.
- [ ] Implement the seed router.
- [ ] Add `api_cors_origins` and `sample_clips_dir` to settings and `.env.example`.
- [ ] Write `tests/test_api.py` against the fixture run, including a replay run started through `POST /runs` and consumed through the SSE endpoint.
- [ ] Update `README.md` with the API run command.

## Validation Steps

```powershell
conda activate goldcoast
uvicorn goldcoast.api.app:app --reload
```

In a second terminal:

```powershell
curl.exe -X POST http://localhost:8000/runs -H "Content-Type: application/json" -d "{\"clip_path\": \"sample_clips/<hype-clip>.mp4\", \"replay_from\": \"<run_id>\"}"
curl.exe -N http://localhost:8000/runs/<new_run_id>/events
curl.exe http://localhost:8000/runs/<new_run_id>/ads
curl.exe -X POST http://localhost:8000/ads/<ad_id>/decision -H "Content-Type: application/json" -d "{\"ad_id\": \"<ad_id>\", \"decision\": \"approved\", \"reviewer\": \"demo\", \"note\": \"\"}"
curl.exe http://localhost:8000/runs/<new_run_id>/export
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_api.py
ruff check .
```

Expected: the events stream prints events in order and closes after `run_completed`; the ads listing shows a verdict on every final ad; the decision is accepted and appears on the next ads listing; export lists the approved file; tests pass.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including a sample of the SSE output and the export manifest.
- `docs/FEATURE_STATUS.md` shows 0007 as Completed with a link to the evidence.
- The spec is committed on its own.
