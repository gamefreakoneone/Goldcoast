# AGENTS.md

## Project Purpose

Goldcoast is a dynamic ad-generation workflow for the LA 2028 Olympics that redirects incoming visitors toward local businesses. A video agent watches Olympics footage and detects hype moments, for example a Japanese archer hitting a bullseye while the crowd erupts. It identifies the best frame and hands the moment to an ad-generation agent. That agent resolves the athlete's profile (nationality, favorite foods, interests), matches local businesses whose offerings relate to the moment (a sushi restaurant, later an archery range), selects an ad style, and produces one landscape ad and one portrait ad per matched business. A judge agent scores every ad against the brief and style before it reaches a human. A web UI shows the AI watching the video, the detection, the agent hand-offs, the judge verdicts, and the generated ads, and lets an operator approve or reject each ad. The project is built for a hackathon demo, so the pipeline must run reliably on pre-recorded clips and must be replayable from cached model outputs.

## Working Rules

- Check `docs/FEATURE_STATUS.md` first to see what is completed, in progress, blocked, or not started.
- Work one spec at a time, in numeric order, from `docs/specs/NNNN-feature-name/`. Do not start a later spec while an earlier one is In progress unless it is explicitly Blocked.
- Read the spec's `requirements.md`, `design.md`, and `tasks.md` in full before writing any code for it.
- When a feature's status changes, update `docs/FEATURE_STATUS.md`, the spec's `status.md`, and the checkboxes in the spec's `tasks.md` in the same change.
- Validate before committing by running the Validation Steps listed in the spec's `tasks.md` and recording the commands and outputs as evidence in `status.md`.
- Commit each spec separately. One spec, one commit series, with the spec id in the commit message.
- Keep `README.md` current whenever setup, run, or test commands change.
- `docs/specs/demo-spec/` is a format reference. It is not a feature and is not tracked in `docs/FEATURE_STATUS.md`, except that its `requirements.md` holds the project-level requirements and delivery order.
- `PLANS.md` is the template to use when no spec exists yet or a spec needs re-planning. A finished plan graduates into a numbered spec folder.
- `TECHNICAL_DESIGN.md` holds the contracts and invariants shared across specs. Change it deliberately and note the change in the affected spec's `status.md`.

## Development Environment

- OS: Windows 11 Pro, PowerShell as the primary shell. Git Bash is available for POSIX scripts.
- Python: 3.12 inside a Conda environment named `goldcoast`, defined by `environment.yml` at the repo root. Conda provides `python` and `ffmpeg`. Python packages are installed with pip from `pyproject.toml`.
- Frontend: Node 20 LTS with `pnpm`, project under `web/`.
- AI provider: Google Gemini through the `google-genai` Python SDK. The API key comes from Google AI Studio and is stored in `.env` as `GEMINI_API_KEY`.
- Setup:

```powershell
conda env create -f environment.yml
conda activate goldcoast
pip install -e ".[dev]"
pnpm --dir web install
Copy-Item .env.example .env
```

- Run:

```powershell
python -m goldcoast --help
python -m goldcoast detect sample_clips/<clip>.mp4
python -m goldcoast run sample_clips/<clip>.mp4
uvicorn goldcoast.api.app:app --reload
pnpm --dir web dev
```

- Test and lint:

```powershell
pytest
ruff check .
ruff format --check .
pnpm --dir web test
pnpm --dir web lint
```

- Replay mode: set `GOLDCOAST_REPLAY=1` to serve cached model outputs from a previous run instead of calling Gemini. Use this for demos and for tests that must not hit the network.

## Project Areas

- `src/goldcoast/models/`: Pydantic models that define every contract between stages (athletes, businesses, ad styles, hype moments, ad briefs, generated ads, quality verdicts, approvals, pipeline events).
- `src/goldcoast/data/`: loaders and validators for the seed JSON files in `data/`.
- `src/goldcoast/agents/`: the video agent, matching agent, ad-generation agent, and judge agent. Each agent is a class with a single typed entry point and a Gemini client wrapper that logs every call.
- `src/goldcoast/pipeline/`: orchestration, the event bus, the run store, and replay mode.
- `src/goldcoast/api/`: FastAPI application, SSE event stream, media serving, and approval endpoints.
- `src/goldcoast/cli.py`: command-line entry points that run each stage independently.
- `web/`: React and Vite frontend with the video player, agent timeline, ad gallery, and approval controls.
- `data/`: seed JSON files (`athletes.json`, `businesses.json`, `ad_styles.json`, optional `venues.json`) and brand assets under `data/assets/<business_id>/`.
- `sample_clips/`: input MP4 clips and `manifest.json`. Gitignored except the manifest.
- `output/runs/<run_id>/`: per-run artifacts: extracted frames, generated ads, judge verdicts, the event log, and every model call. Gitignored.
- `docs/`: `FEATURE_STATUS.md` ledger, `DATA_REQUIREMENTS.md`, `specs/` folders, and `archive/`.
- `tests/`: pytest suites, with fixtures that use replay mode so they never call the network.

## Quality Bar

- Every document must be explicit enough that another agent can execute it without asking the author.
- Every spec ships with validation evidence in its `status.md`: the exact commands run and their relevant output.
- Prefer minimal, targeted changes over rewrites. Do not refactor code outside the current spec's scope.
- Agents exchange typed Pydantic models, never free-form text. Any model output is parsed into a model before it leaves the agent.
- Every Gemini call is logged with its prompt, inputs, response, model id, and latency into the run directory.
- A generated ad must reference a `business_id`, `athlete_id`, and `ad_style_id` that exist in the seed data. Agents may not invent businesses.
- No ad reaches the approval UI without a judge verdict attached.
- The end-to-end demo must run in replay mode from cached outputs so a live API failure cannot break a presentation.
- Secrets live only in `.env`, which is never committed.
- Do not add comments in source files unless explicitly asked.
