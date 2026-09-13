# Status: 0008 Web UI and Approval

## Status

Completed

## Evidence

### Implementation

React/Vite/TypeScript UI under `web/`, using plain CSS modules and system fonts.
The UI reads and writes through the existing API only. It includes clip/recording
selection, muted playback from zero, first-moment seek/pause, all three selectable
best frames, highlight windows, a following/expandable agent timeline, live judged
previews, final-ad review, attempt histories, match detail drawer, and approved
PNG export links with an inspectable manifest. Each business has three separate
brief pairs; formats never overwrite ads belonging to another moment.

Every gallery card has a matching verdict. Five criterion scores and
`verdict.scores.overall` are displayed, and only final selections enable review.
REST attempts and SSE attempt pairs normalize into the same gallery shape.
Decisions use reviewer `demo`, refetch ads, and invalidate the displayed export.
Failed decisions preserve the current decision and expose the HTTP error.
Missing media shows its path and retries twice to recover transient file misses.
The native EventSource is retained on disconnect, allowing browser-managed
`Last-Event-ID` resume, and is closed explicitly on either terminal event.

No API/Pydantic/shared contracts were changed; `TECHNICAL_DESIGN.md` is unchanged.
No new creative assets, live Gemini calls, clip analysis, or force-analysis were
used. Simone Biles's name, recorded discovery copy, and the exact offer
`Demo offer: bring your Olympics ticket for 15% off` are preserved.

### Environment and frontend validation

Windows 11, Node `v22.15.0`, pnpm `10.18.1`, Conda `goldcoast` Python `3.12.14`.
PowerShell blocks `pnpm.ps1` in this execution environment, so the exact equivalent
`pnpm.cmd` was used. Installation needed network-enabled execution; test/lint/build
needed access to those installed files under the workspace owner.

Commands from the repository root:

```powershell
pnpm.cmd --dir web install
pnpm.cmd --dir web dev
pnpm.cmd --dir web test
pnpm.cmd --dir web lint
pnpm.cmd --dir web build
```

Relevant output:

```text
install: Done using pnpm v10.18.1
dev: VITE v6.4.3 ready; Local: http://localhost:5173/

Test Files  4 passed (4)
     Tests  12 passed (12)
  Duration  12.22s

lint: tsc --noEmit && eslint .
exit 0, no diagnostics

vite v6.4.3 building for production...
41 modules transformed.
dist/index.html                   0.72 kB | gzip: 0.46 kB
dist/assets/index-9XcO9RNn.css    8.12 kB | gzip: 2.35 kB
dist/assets/index-BL4jFn2A.js   247.38 kB | gzip: 77.34 kB
built in 4.18s
```

Final output logs: `output/manual/0008/frontend-tests.txt`,
`frontend-lint.txt`, and `frontend-build.txt`.
The 12 tests cover recorded reduction, duplicate/stale/other-run events, failed
runs, missing verdicts, business/brief grouping, progressive judged previews,
failed decision rollback, missing-media recovery and bounded retries, EventSource
lifecycle, and a mocked-HTTP integration flow through playback, every final card,
approval, rejection, refetch, and export. The integration uses the real 93-event
fixture, enriched with HTTP media URLs in the test adapter, with no model calls.

The copied JSONL and original fixture have identical SHA-256:
`AFBA1636A87D2F150B6BFCA64DDC0738B78319B924D6FB6A47BB4B01F79B573D`.

Initial checks exposed two invalid Testing Library selector options and missing
jsdom `showModal`; both test-harness issues were fixed. The first browser pass
found a transient image 404 that left a placeholder after the file became
available; bounded media retry fixes that behavior. The successful final browser
run loaded all 13 images, including the extracted frame, with zero console errors.

### Python regression validation

No Python source changed. The first sandboxed pytest run could not access the
pre-existing `output/pytest-tmp` and produced setup permission errors. After that
process exited, the same suite ran under the workspace owner with Conda's ffmpeg
directory on PATH; no pytest processes overlapped.

Exact successful commands:

```powershell
$env:PATH = 'C:\Users\amogh\anaconda3\envs\goldcoast;C:\Users\amogh\anaconda3\envs\goldcoast\Library\bin;' + $env:PATH
& C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m pytest -p no:cacheprovider --basetemp output/pytest-tmp
& C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff check .
& C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff format --check .
```

```text
87 passed, 2 warnings in 93.96s (0:01:33)
All checks passed!
129 files already formatted
```

The two warnings are existing Starlette/httpx and anyio deprecations.

### Playwright MCP manual verification

Flow: `http://localhost:5173` -> original recording -> Start replay -> moment and
agent hand-offs -> judged final gallery -> match details -> approve -> export ->
reject with a reason -> export empty -> approve again -> export one file.

Native Playwright MCP tools were not exposed in the agent tool list. Used the
existing stdio helper at
`C:\Users\amogh\AppData\Local\Temp\opencode\goldcoast_mcp.py` to call
`@playwright/mcp@latest` (`browser_navigate`, `browser_resize`, `browser_evaluate`,
`browser_wait_for`, `browser_take_screenshot`, `browser_console_messages`).

API startup used the Conda interpreter directly, equivalent to activation:

```powershell
$env:GOLDCOAST_REPLAY = '1'
$env:GOLDCOAST_REPLAY_RUN = '20260912-230559-0d2470'
& C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m uvicorn goldcoast.api.app:app --reload
```

Browser verification commands:

```powershell
& C:/Users/amogh/anaconda3/envs/goldcoast/python.exe output/manual/0008/verify_ui.py
& C:/Users/amogh/anaconda3/envs/goldcoast/python.exe output/manual/0008/verify_resume.py
```

Verified run: **20260913-002142-60027e**. Source:
**20260912-230559-0d2470**. Started `2026-09-13T00:21:42.804115Z`, completed
`2026-09-13T00:21:55.637550Z`; `replay: true`, `failures: []`.

| Check | Observed result |
|---|---|
| Page identity, meaningful render, framework overlay | Correct Goldcoast title/URL, all panels present, no overlay |
| Replay | POST 201; 3 moments, 6 briefs, 12 passing finals, 17 attempts |
| Video and frame | Paused at 122.5s; buttons also seek/pause at 41.0s and 91.5s with matching loaded frames; highlight window visible |
| Timeline | All 93 events present; 12 `ad_final` steps; judged step exposes six scores; regeneration hints readable |
| Gallery | 6 distinct brief pairs across 2 businesses; every final shows all six labels, pass badge, enabled approval |
| Match drawer | Simone Biles, favorite foods, Yama Sushi Marketplace, creative direction, offer, and seed records present |
| Decisions | Approved by demo; rejection reason persisted and rendered; final ads refetched each time |
| Export | One downloadable PNG verified with HTTP 200 and PNG signature; rejection clears stale UI export; re-export gives zero files; final approval restores one |
| SSE terminal | Native EventSource has `readyState: 2` after completion |
| SSE disconnect | Local recorded-event stream closes after event 11; actual reconnect header is `Last-Event-ID: 11`; reducer ends with 93 unique events and 12 finals |
| Desktop / narrow | 1440x1100 and 390x844; narrow layout stacks with no horizontal overflow |
| Console | Final full UI run: Errors 0, Warnings 0 |

The reconnect test uses a temporary local HTTP stream at port 8766 and the actual
frontend `subscribeToRun`/reducer with recorded events. Observed connection states:
`connecting -> connected -> reconnecting -> connected -> closed`. It does not call
Gemini or change the API. The temporary stream server is stopped afterward.

Screenshots taken by Playwright MCP and visually inspected:

- `output/manual/0008/desktop.png`
- `output/manual/0008/export.png`
- `output/manual/0008/mobile.png`

Full tool evidence: `output/manual/0008/playwright-evidence.json` and
`output/manual/0008/resume-evidence.json`. Additional MCP snapshots/logs were moved
under `output/manual/0008/mcp-runtime/`. These artifacts remain gitignored.

Final export contains
`approved/yama-sushi-marketplace-koreatown_brief_80dd5108f4e4_landscape.png`.
Browser reload intentionally returns to the picker; there is no persisted UI
session. Live mode was not exercised. All runtime validation used recordings.

## Blockers

None.

## Change Log

- 2026-09-12: Spec created.
- 2026-09-12 (PDT): Implemented and completed spec 0008 only. Added frontend,
  recorded tests, README demo commands, and validation evidence. Existing
  `dispose.md`, `docs/REVIEW_PROMPT.md`, and `.claude/` user work remain untouched.
