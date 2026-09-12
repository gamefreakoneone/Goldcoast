# Tasks: 0008 Web UI and Approval

## Task List

- [ ] Scaffold `web/` with Vite, React, TypeScript, Vitest, and a dev proxy to the API.
- [ ] Write `web/src/api/types.ts` matching the Pydantic models field for field.
- [ ] Implement `web/src/api/client.ts` including the `EventSource` helper with resume.
- [ ] Implement `runReducer` and the provider in `web/src/state/runStore.ts`.
- [ ] Implement `ClipPicker`, `VideoStage`, `AgentTimeline`, `AdGallery`, `AdCard`, `DetailDrawer`, and `ExportPanel`.
- [ ] Implement `App.tsx` layout with a narrow-screen single-column fallback.
- [ ] Copy the fixture run's `events.jsonl` into `web/src/test/fixtures/` and write reducer and gallery grouping unit tests.
- [ ] Write one integration test with a mocked API that replays the fixture events and asserts the gallery renders every final ad with a verdict.
- [ ] Update `README.md` with the frontend install and dev commands.

## Validation Steps

```powershell
conda activate goldcoast
uvicorn goldcoast.api.app:app --reload
```

In a second terminal:

```powershell
pnpm --dir web install
pnpm --dir web dev
pnpm --dir web test
pnpm --dir web lint
pnpm --dir web build
```

Manual check in the browser at `http://localhost:5173`: start a replay run from the fixture run, confirm the video seeks to the hype moment, the timeline shows every step through `ad_final`, each ad card shows five scores and a pass or fail badge, approving an ad updates the card, and export lists the approved file.

Expected: unit and integration tests pass, lint and build succeed, and the manual check matches the description above.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including a description of the manual check and a screenshot path under `output/manual/0008/`.
- `docs/FEATURE_STATUS.md` shows 0008 as Completed with a link to the evidence.
- The spec is committed on its own.
