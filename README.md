# Goldcoast

Dynamic ad generation for the LA 2028 Olympics: an AI video agent spots hype moments in Olympics footage, and an ad-generation agent turns each moment into landscape and portrait ads for nearby local businesses, judged for quality and approved by a human through a web UI.

The full agent pipeline and HTTP API are implemented, with Simone Biles's profile,
three LA businesses, recorded replay, live events, human decisions, and approved
exports. The React browser UI completes the demo with video highlights, an agent
timeline, judged ad pairs, human review, match details, and approved downloads.

## Marketing pivot implementation

The next release turns local events and cultural topics into branded campaigns
for onboarded food and drink businesses. Work starts with spec 0009: a Strands
Agents 1.55.1 runtime using Gemini, explicitly registered tools, typed outputs,
call budgets, cancellation, and request-validated offline replay. Existing
Olympics commands and recordings remain supported during the migration.

Installing the project with `pip install -e ".[dev]"` also installs
`strands-agents[gemini]`. New runtime calls use `AgentRuntime.gemini(...)` with
an explicitly configured Gemini model and the existing API key; do not hard-code
credentials. `AgentRuntime(..., replay_dir=...)` needs no model or API key.
Each runtime invocation records provider and tool activity under its supplied
record directory. Use a shared `ExecutionBudget` across collaborating agents.

The project MCP configuration also includes the official Strands documentation
server. Install its launcher with `python -m pip install uv`. The server runs in
an isolated environment with `mcp<2`, required by its published 0.2.7 release;
this does not downgrade the application's MCP dependency. Reload your MCP client
to discover `strands-docs`. This is developer documentation tooling, not an
application runtime dependency.

## Marketing studio development

The tenant-isolated studio API is separate from the legacy video API. Its login,
replay, and storage services do not need Gemini credentials. Local infrastructure
uses Docker Desktop with Linux containers:

```powershell
python scripts/setup_studio.py
docker compose up -d postgres keycloak
python -m alembic upgrade head
uvicorn goldcoast.api.studio_app:app --port 8001
```

The setup script generates development passwords only in `.env`. Keycloak runs
at `http://localhost:8080`; the imported `goldcoast` realm contains `owner` and
`demo` accounts. Their passwords are `GOLDCOAST_LOCAL_OWNER_PASSWORD` and
`GOLDCOAST_LOCAL_DEMO_PASSWORD` in `.env`. Public registration is disabled.
Passwords are imported on the first Keycloak start; changing `.env` later does
not automatically change an existing identity's password.

PostgreSQL binds to `127.0.0.1:5433`. Set `GOLDCOAST_DATABASE_URL` to use an
external PostgreSQL instance; otherwise the application constructs the local
connection from `GOLDCOAST_DB_PASSWORD`. Private local assets use
`output/studio/assets`. Both services bind only to localhost in this Compose
configuration. Hosted authentication will use Cognito with the same OIDC checks.

The authenticated `/api/v2` interface includes `/me`, `/usage`, run history and
SSE, cancellation, and owner-only allowance controls. Live generation starts
disabled; accounts start without paid grants. Owner grants and the global live
switch are separate controls. The old unauthenticated `/runs` routes are not
mounted in the studio API.

## Setup

```powershell
conda env create -f environment.yml
conda activate goldcoast
pip install -e ".[dev]"
pnpm --dir web install
Copy-Item .env.example .env
```

Edit `.env` and replace all three model placeholders. Add `GEMINI_API_KEY` for live calls. `GOOGLE_API_KEY` is also accepted and takes precedence when both variables are present. Set `GOLDCOAST_REPLAY=1` when running from cached outputs without an API key.

## Commands

```powershell
python -m goldcoast --help
python -m goldcoast validate-seed
python -m goldcoast detect sample_clips/<clip>.mp4
python -m goldcoast run sample_clips/<clip>.mp4
```

All CLI pipeline stages are implemented.

### Video detection

```powershell
python -m goldcoast detect sample_clips/gymnastics_simone.mp4 --out output/manual/0002
python -m goldcoast clips
```

Detection writes `moments/*.json`, `frames/*.png`, and recorded calls under the output directory.
Files at least 20 MiB use the Gemini Files API. An analyzed clip is read from
`sample_clips/manifest.json` without another model call, including analyzed clips
with no hype moments. Edit timestamps within the clip and moment window and set
`analyzed_by` to `manual` to curate frames. `--force-analysis` explicitly replaces
the analysis while preserving the athlete ID and notes. `--threshold` overrides
`GOLDCOAST_HYPE_THRESHOLD` (default 6).

### Context matching

```powershell
python -m goldcoast match output/manual/0002/moments/0002-moment-1.json --out output/manual/0003
```

The manifest athlete ID takes precedence over model hints. Eligible businesses
must share cuisine, dish, or interest tags; `--max-businesses` defaults to 2.
Briefs are saved under `briefs/` and include both formats, discovery-oriented copy,
and the business tagline when no actual promotion exists.

### Ad generation

```powershell
python -m goldcoast generate output/manual/0003-creative/briefs/0002-moment-1-brief-yama-sushi-marketplace-koreatown.json --moment output/manual/0002/moments/0002-moment-1.json --out output/manual/0004-creative
```

One call per format generates the entire ad from the real frame, portrait, logo,
and product reference. `--format`, `--attempt`, and repeatable `--hint` support
single-format regeneration. Images and sidecars live under
`ads/<business_id>/brief_<12-character-brief-hash>/<format>/attempt_<n>.*` so multiple
moments never overwrite each other. Original model image bytes are retained under
`model_calls/images/` independently of dimension normalization.

Restaurant demo offers are explicitly fictional: `Demo offer: bring your Olympics
ticket for 15% off`. Creative copy connects the observed moment to Simone's
documented tastes and invites local discovery without implying endorsement.

### Quality judging

```powershell
python -m goldcoast judge <ad.json> --brief <brief.json> --moment <moment.json> --out output/manual/0005
python -m goldcoast judge-loop --brief <brief.json> --moment <moment.json> --format portrait --out output/manual/0005
```

The judge scores five criteria and supplies regeneration hints. The loop makes
at most `GOLDCOAST_JUDGE_MAX_RETRIES + 1` attempts (default 3), keeping the first
passing ad or the best failing attempt. Verdicts are advisory; they never approve
an ad. Threshold defaults are overall 7 and every criterion at least 5.

### Full pipeline and replay

```powershell
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast run sample_clips/gymnastics_simone.mp4
python -m goldcoast runs
$env:GOLDCOAST_REPLAY = "1"
python -m goldcoast run sample_clips/gymnastics_simone.mp4 --replay-from <recorded-run-id>
```

The live run uses the analyzed clip manifest and makes no new video-analysis
request. Run directories contain all moments, frames, briefs, generation attempts,
verdicts, events, model-call images, and seed/settings snapshots. Replays are
independent of the original output directory after creation and do not need to
reanalyze or decode the video. `GOLDCOAST_REPLAY_RUN` supplies the default source
when replay mode is enabled. An unavailable recording fails explicitly.

### API demo

From the repository root:

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "1"
$env:GOLDCOAST_REPLAY_RUN = "20260912-230559-0d2470"
uvicorn goldcoast.api.app:app --reload
```

Open `http://localhost:8000/docs` for the interactive API. In another terminal:

```powershell
$run = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/runs" -ContentType "application/json" -Body '{"clip_path":"sample_clips/gymnastics_simone.mp4","replay_from":"20260912-230559-0d2470"}'
curl.exe -N "http://localhost:8000/runs/$($run.id)/events"
$ads = Invoke-RestMethod "http://localhost:8000/runs/$($run.id)/ads"
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/ads/$($ads[0].id)/decision" -ContentType "application/json" -Body '{"decision":"approved","reviewer":"demo","note":""}'
Invoke-RestMethod "http://localhost:8000/runs/$($run.id)/export"
```

The source run is the actual completed demo: 3 moments, 6 briefs, and 12 passing
final ads. It exists locally under `output/runs/20260912-230559-0d2470/`. On a fresh
checkout, install the committed fixture first:

```powershell
New-Item -ItemType Directory -Force output/runs
Copy-Item -Recurse tests/fixtures/runs/20260912-230559-0d2470 output/runs/20260912-230559-0d2470
```

Replay does not require the MP4; browser playback requires
`sample_clips/gymnastics_simone.mp4`. Replay never analyzes or regenerates inputs
through Gemini. The same demo also runs through the CLI:

```powershell
python -m goldcoast run sample_clips/gymnastics_simone.mp4 --replay-from 20260912-230559-0d2470
```

`GET /clips` provides clip metadata and playback URLs. Moment/ad responses include
media URLs; final ads include their verdict, attempt history, and current decision.
SSE resumes strictly after `Last-Event-ID` and closes on completion/failure; consumers
should close EventSource on those terminal events. Export returns a manifest with
download URLs and writes `approved/` under the run, using brief-specific filenames.
Changing an approval and exporting again refreshes that directory.

This is a single-process demo server. CORS defaults to `http://localhost:5173`;
configure `GOLDCOAST_API_CORS_ORIGINS` as a JSON array and
`GOLDCOAST_SAMPLE_CLIPS_DIR` to change the clip directory.

### Browser demo

Start the replay API with the API demo commands above. In a second PowerShell
terminal at the repository root:

```powershell
pnpm --dir web install
pnpm --dir web dev
```

Open `http://localhost:5173`. Leave **Replay recording** checked, select
`gymnastics_simone.mp4` and recording `20260912-230559-0d2470`, and click **Start
replay**. Expect 3 moments, 6 briefs, 12 passing final ads, and 17 attempts.
The video starts muted from zero, then pauses on the first detected best frame
(122.5s). Moment buttons also select 41.0s and 91.5s. The frame beside the video
comes from the recording. Replay works without the MP4, with a video placeholder.

Follow the timeline or uncheck **Follow events** to inspect earlier hand-offs.
Expand judged steps for all scores and regenerating steps for hints. Each business
contains three distinct brief pairs, each with landscape and portrait ads. Cards
show five criteria plus overall, pass/fail, judge notes, and every recorded attempt.
Judged previews appear during the run; only final selections can be reviewed.
Click **Why this match?** for the athlete, business, style, and discovery brief.

Click **Approve**, or **Reject**, enter a reason and confirm. Decisions use reviewer
`demo` and refetch the final selections. **Export approved** produces a manifest
and downloadable PNG links. Changing a decision clears the displayed export;
export again to refresh it. Judge scores are advisory and never auto-approve ads.

The UI uses plain CSS modules, local system fonts, and only the existing API.
Vite listens on port 5173 and proxies API/media requests to port 8000. Optional
`VITE_API_BASE` overrides the API origin (set before starting Vite or building;
configure API CORS for that UI origin). Native EventSource reconnects with
`Last-Event-ID`; terminal events close it. A page refresh returns to the picker;
start another replay for a fresh demo.

If PowerShell blocks `pnpm.ps1`, use `pnpm.cmd` for the same commands. Node 20+
is the project baseline; this UI was validated with Node 22.15.0 and pnpm 10.18.1.

## Validation

```powershell
ffmpeg -version
python -m goldcoast validate-seed
pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
pnpm --dir web test
pnpm --dir web lint
pnpm --dir web build
```

Create `output/` first if needed. The pytest flags avoid Windows temporary-directory
permission issues; do not run concurrent pytest processes sharing that directory.

See [AGENTS.md](AGENTS.md) for working rules, [docs/FEATURE_STATUS.md](docs/FEATURE_STATUS.md) for feature progress, and [docs/DATA_REQUIREMENTS.md](docs/DATA_REQUIREMENTS.md) for production data requirements.


The studio API now accepts business profiles at `/api/v2/business`, editable brand kits at `/api/v2/brand`, and multipart uploads at `/api/v2/assets` (`file`, `role`, `rights_confirmed`). Supported roles are logo, product, reference, guidelines (PDF), and font. Limits: 10 MB per file, 30 files and 100 MB per account. Images must be still PNG/JPEG/WebP below 16 megapixels. Uploading is free of model calls; brand analysis will run as a separately metered workflow.


Studio discovery uses `TAVILY_API_KEY` for bounded basic search and page extraction. `TICKETMASTER_API_KEY` optionally adds structured local events; its absence is reported explicitly. Provider requests are recorded and cached, and incomplete requests never retry automatically. Graph claims retain citations, excerpts, conflicts and freshness. Tests remain offline.
