# TECHNICAL_DESIGN.md

## Architecture Summary

Goldcoast is a staged pipeline of agents that turns a hype moment in Olympics footage into approved local-business ads. Each stage consumes and produces typed Pydantic models, emits events to a run-scoped event bus, and persists its artifacts to the run directory.

1. Clip Source. Reads MP4 files from `sample_clips/`. The interface is a `ClipSource` protocol so a live-stream source can be added later without touching the agents.
2. Video Agent (`agents/video_agent.py`). Sends the clip to a Gemini video-capable model, asks for hype moments with timestamps, context, sport, and athlete hints, then extracts the best frame with ffmpeg. Produces a list of `HypeMoment`.
3. Matching Agent (`agents/matching_agent.py`). Resolves the athlete from seed data using the hints, ranks businesses by tag overlap and an LLM re-rank, selects an `AdStyle`. Produces one `AdBrief` per matched business.
4. Ad Generation Agent (`agents/ad_agent.py`). For each `AdBrief` and each format (landscape, portrait), calls a Gemini image model with the hype frame as the hero image, the athlete portrait as an identity reference, the business logo, business details, and style guidance. Produces `GeneratedAd` records and PNG files.
5. Judge Agent (`agents/judge_agent.py`). Scores every `GeneratedAd` against its `AdBrief` and `AdStyle` on a fixed rubric using a Gemini vision model, with the hero frame and athlete portrait as references. Produces a `QualityVerdict`. Failing ads are regenerated with the verdict's hints up to a retry cap.
6. Run Store and Event Bus (`pipeline/`). The orchestrator runs stages 2 to 5 in order, appends `PipelineEvent` records to `events.jsonl`, writes artifacts under `output/runs/<run_id>/`, and supports replay mode that serves cached model outputs.
7. API (`api/`). FastAPI exposes runs, an SSE event stream, media files, ads with verdicts, and approval decisions.
8. Web UI (`web/`). React and Vite. Plays the clip, shows the agent timeline as events arrive, displays ads with judge scores, and records approve or reject decisions.

Layers in `src/goldcoast/`: `models/`, `data/`, `agents/`, `pipeline/`, `api/`, `cli.py`. The frontend lives in `web/`.

## Development Environment

- OS: Windows 11 Pro. Primary shell PowerShell. Paths in code use `pathlib` and are never hard-coded with a drive letter.
- Conda environment `goldcoast` from `environment.yml`:
  - conda dependencies: `python=3.12`, `ffmpeg`.
  - pip dependencies come from `pyproject.toml`: `google-genai`, `pydantic>=2`, `fastapi`, `uvicorn[standard]`, `sse-starlette`, `python-dotenv`, `pillow`, `typer`, `httpx`. Dev extras: `pytest`, `pytest-asyncio`, `ruff`.
- Frontend: Node 20 LTS, `pnpm`, Vite, React, TypeScript. Tests with Vitest.
- Setup: `conda env create -f environment.yml`, `conda activate goldcoast`, `pip install -e ".[dev]"`, `pnpm --dir web install`.
- Environment variables (loaded from `.env` with `python-dotenv`):
  - `GEMINI_API_KEY`: Google AI Studio key. The `google-genai` client also accepts `GOOGLE_API_KEY`, which takes precedence if both are set.
  - `GOLDCOAST_VIDEO_MODEL`: Gemini model id used for video analysis.
  - `GOLDCOAST_IMAGE_MODEL`: Gemini model id used for image generation.
  - `GOLDCOAST_JUDGE_MODEL`: Gemini model id used for judging ads.
  - `GOLDCOAST_JUDGE_MAX_RETRIES`: integer retry cap for regeneration, default 2.
  - `GOLDCOAST_JUDGE_PASS_THRESHOLD`: overall score required to pass, default 7.
  - `GOLDCOAST_JUDGE_MIN_CRITERION`: minimum score for every criterion, default 5.
  - `GOLDCOAST_REPLAY`: set to `1` to serve cached model outputs instead of calling Gemini.
  - `GOLDCOAST_REPLAY_RUN`: run id whose cached outputs replay mode reads from.
  - `GOLDCOAST_OUTPUT_DIR`: default `output`.
  - `GOLDCOAST_CLIP_MANIFEST`: default `sample_clips/manifest.json`. The editable record of analyzed clips; see Clip manifest below.
  - `GOLDCOAST_HYPE_THRESHOLD`: default 6, minimum accepted hype score.
  - `GOLDCOAST_FRAME_CANDIDATE_WINDOW_S`: default 1.0, neighboring-frame window.
  - `GOLDCOAST_ATHLETE_CONFIDENCE_THRESHOLD`: default 0.6.
  - `GOLDCOAST_MAX_BUSINESSES`: default 2, global cap per moment.
- Directory layout:

```
Goldcoast/
  environment.yml
  pyproject.toml
  .env.example
  data/
    athletes.json
    businesses.json
    ad_styles.json
    venues.json
    assets/<business_id>/logo.png
  sample_clips/
    manifest.json
    <sport>_<athlete-id>_<event>.mp4
  output/runs/<run_id>/
  src/goldcoast/
  web/
  tests/
  docs/
```

- Run: `python -m goldcoast run <clip>` for the full pipeline, `python -m goldcoast detect|match|generate|judge` for single stages, `uvicorn goldcoast.api.app:app --reload` for the API, `pnpm --dir web dev` for the UI.
- Test: `pytest`, `ruff check .`, `ruff format --check .`, `pnpm --dir web test`.

## Key Contracts

### Seed data models (`models/seed.py`)

- `Athlete`: `id`, `name`, `aliases: list[str]`, `country`, `sport`, `discipline`, `event`, `home_city`, `favorite_foods: list[FoodPreference]` where `FoodPreference` has `cuisine` and `dishes: list[str]`, `interests: list[str]`, `identification: AthleteIdentification` with `kit_colors`, `bib_number`, `distinguishing_features`, optional `headshot` (path under `data/assets/` to the athlete portrait used as an identity reference by ad generation and judging), `social_handles: dict[str, str]`, `fun_facts: list[str]`. The field stays optional in the model so seed validation does not fail for athletes without a portrait, but the ad agent requires it and fails early when it is missing.
- `Business`: `id`, `name`, `category` (one of `restaurant`, `cafe`, `bar`, `sports_venue`, `retail`, `experience`), `tags: list[str]`, `address`, `neighborhood`, `nearest_venue`, `short_description`, `offerings: list[str]`, `logo` (path relative to `data/assets/`), `brand_colors: list[str]` hex, `tagline`, `offer_text: str | None` (null for real businesses with no live promotion; the ad agent uses `tagline` in its place), `cta`, `website`, `instagram`, optional `hours`, `price_range`, `reference_photos: list[str]` (paths relative to `data/assets/`).
- `AdStyle`: `id`, `name`, `description`, `mood_keywords: list[str]`, `palette: list[str]`, `typography_guidance`, `layout_notes: dict[AdFormat, str]`, `required_elements: list[str]`, `use_when: list[str]`, optional `reference_images: list[str]`.
- `Venue` (optional): `id`, `name`, `sport`, `lat`, `lng`, `neighborhood`.

Seed files are JSON arrays of the corresponding model with unknown fields rejected. Loaders in `data/loaders.py` validate on load and fail fast on unknown ids, duplicate ids, missing logo files, and an athlete whose tags overlap no business at all. Athlete tags that no business uses are reported as warnings, not errors, so a rich profile can coexist with a small business list. Provenance and copy notes that do not belong in the validated JSON live in `data/SOURCES.md`.

### Pipeline models (`models/pipeline.py`)

- `AdFormat`: enum `landscape` (1920x1080, aspect 16:9, billboard) and `portrait` (1080x1920, aspect 9:16, reel).
- `HypeMoment`: `id`, `run_id`, `clip_path`, `start_s`, `end_s`, `best_frame_s`, `best_frame_path`, `hype_score` 0 to 10, `description`, `sport`, `event_context`, `athlete_id: str | None` (set when the manifest already names the athlete), `athlete_hints: AthleteHints | None` with `name`, `country`, `kit_colors`, `bib_number`, `crowd_reaction`, `source` (`gemini` or `manual`).
  - `source` belongs to the moment and reflects the manifest's `analyzed_by`; `best_frame_path` is nullable when extraction fails, as required by 0002. Consumers requiring a frame must reject null explicitly.
- `AdBrief`: `id`, `run_id`, `moment_id`, `athlete_id`, `business_id`, `ad_style_id`, `match_reason`, `match_score` 0 to 1, `headline_direction`, `offer_text`, `cta`, `formats: list[AdFormat]`.
- `GeneratedAd`: `id`, `run_id`, `brief_id`, `business_id`, `format`, `attempt`, `image_path`, `prompt_used`, `model_id`, `created_at`, `metadata: AdMetadata` with `format_mismatch: bool = false`, `resized_from: tuple[int, int] | None`, `portrait_omitted: bool = false`, `composited: bool = false`.
- `QualityVerdict`: `id`, `run_id`, `ad_id`, `attempt`, `scores: VerdictScores` with integer fields 0 to 10 for `image_quality`, `style_adherence`, `business_accuracy`, `format_compliance`, `brand_safety`, `overall` 0 to 10, `passed: bool`, `issues: list[str]`, `regeneration_hints: list[str]`, `model_id`, `created_at`.
- `ApprovalDecision`: `ad_id`, `decision` (`approved` or `rejected`), `reviewer`, `note`, `decided_at`.
- `PipelineEvent`: `id`, `run_id`, `type`, `timestamp`, `payload: dict`. Event types: `run_started`, `clip_loaded`, `clip_manifest_hit`, `moment_detected`, `frame_extracted`, `athlete_resolved`, `business_matched`, `brief_created`, `ad_generating`, `ad_generated`, `ad_judged`, `ad_regenerating`, `ad_final`, `run_completed`, `run_failed`, `ad_decided`.
- `Run`: `id`, `clip_path`, `status` (`running`, `completed`, `failed`), `started_at`, `finished_at`, `replay: bool`, `moment_ids`, `brief_ids`, `ad_ids` (final judged ads only), `replay_from: str | None`, `failures: list[RunFailure]`. RunFailure has stage, message, optional moment_id, brief_id, and format. `moment_skipped` is an explicit event type for a failed match.

### Run directory layout

```
output/runs/<run_id>/
  run.json
  settings.json
  clip_manifest.json
  seed/
  events.jsonl
  frames/<moment_id>.png
  moments/<moment_id>.json
  briefs/<brief_id>.json
  ads/<business_id>/brief_<key>/<format>/attempt_<n>.png
  ads/<business_id>/brief_<key>/<format>/attempt_<n>.json
  verdicts/<ad_id>_attempt_<n>.json
  decisions/<ad_id>.json
  model_calls/<stage>_<sequence>.json
  model_calls/images/<stage>_<sequence>_<index>.png
```

`model_calls/*.json` holds `stage`, `model_id`, `prompt`, `input_refs`, `response`, `latency_ms`, `timestamp`. Replay mode reads these files by stage and sequence.

`brief_<key>` uses the first 12 hexadecimal SHA-256 characters of the brief ID to
prevent different moments overwriting one business's ads while keeping Windows
paths short. Image calls retain original bytes under `model_calls/images/` and
relative references in `response_raw.images`; final PNG normalization never
changes these originals. Aspect-ratio checks allow 1% relative deviation for the
model's quantized native canvas (observed 1376x768 and 768x1376 for requested 16:9
and 9:16). Those outputs are normalized to the exact format dimensions; materially
different ratios are retried once and then flagged without distortion.

HTTP request accounting lives in `model_calls/http_requests/<id>.json` and records only method, URL path (no query), timestamp, response status, and latency. SDK generation retries are explicitly disabled with `HttpRetryOptions(attempts=1)`; any stage-level repair/regeneration is a separate recorded call. Files API initialization, multipart chunks, and activation polls are separate HTTP requests, not separate video analyses. `model_calls/video_upload.json` caches the remote file plus the source path, size, and modification time so a retry on an unchanged clip can reuse its upload.

### Clip manifest (`models/manifest.py`)

`sample_clips/manifest.json` is a JSON array of `ClipEntry`, keyed by clip file name. It is both the owner's input and the video agent's output, and it is committed so it can be edited by hand.

- `ClipEntry`: `file`, `sport`, `athlete_id: str | None`, `analyzed: bool`, `analyzed_by` (`gemini` or `manual`), `analyzed_at: datetime | None`, `notes`, `moments: list[ManifestMoment]`.
- `ManifestMoment`: `start_s`, `end_s`, `best_frame_s`, `hype_score`, `description`, `event_context`, `athlete_hints: AthleteHints | None`.

Rules:

- The video agent looks up the clip by file name. If the entry has `analyzed: true` and at least one moment with `best_frame_s`, it uses those moments, extracts the frames with ffmpeg at the recorded timestamps, and makes no Gemini call. Otherwise it analyzes the clip with Gemini, writes the results into the entry, sets `analyzed: true` and `analyzed_by: gemini`, and saves the manifest.
  An analyzed entry with zero moments is also a cache hit and returns an empty list without a model call.
- The owner may edit any field afterward, in particular `best_frame_s` and `athlete_id`. The next run uses the edited values because frames are always extracted fresh from the timestamps. Set `analyzed_by: manual` when hand-editing so the change is visible in the UI.
- If `athlete_id` is set, the matching agent uses it directly and skips athlete resolution. If it is null after a Gemini analysis, the matching agent resolves it from `athlete_hints` and writes the result back into the entry for the owner to confirm or correct.
- `--force-analysis` re-runs Gemini and overwrites the entry's moments and hints, but never overwrites a non-null `athlete_id`.
- Replay mode is separate: it reproduces an entire run including matching, generation, and judging from recorded model calls.

### API shapes (`api/`)

- `POST /runs` body `{ "clip_path": str, "replay": bool | null, "replay_from": str | null }` returns a `running` `Run` with HTTP 201. Omitted/null `replay` inherits settings; an explicit source enables replay. Replay requires a source (body or configured default) and a matching confined clip path, but no MP4. Explicit live selection overrides the environment and requires an existing MP4. Execution runs off the event loop with the pre-created Run/EventBus.
- `GET /runs` returns `list[Run]`.
- `GET /runs/{run_id}` returns `Run`.
- `GET /runs/{run_id}/events` streams `PipelineEvent` backlog then live events using an atomic subscription. `Last-Event-ID` resumes strictly after the zero-based string ID; invalid cursors return 400. Stream closes at `run_completed`/`run_failed`; a cursor at/past terminal returns 204. Inactive runs return finite backlog. HTTP payloads add `image_url` to generated ads and `best_frame_url`/`clip_url` to moments, including nested `ad_final` attempts; stored recordings are unchanged. Consumers close EventSource on terminal events and refetch decisions over HTTP.
- `GET /runs/{run_id}/moments` returns HypeMoment fields plus `best_frame_url: str | None` and `clip_url: str`.
- `GET /runs/{run_id}/briefs` returns `list[AdBrief]`.
- `GET /runs/{run_id}/ads` returns only `Run.ad_ids` as `list[AdWithVerdict]`: GeneratedAd fields plus `image_url`, required `verdict`, nullable `decision`, `attempts: list[AdAttempt]`, and `errors: list[str]`. AdAttempt has `ad` (GeneratedAd plus image_url), nullable `verdict`, and `is_final`. Attempts group by brief/format and sort numerically; a final without a matching verdict is a 409 integrity error. Overall is `verdict.scores.overall`.
- `POST /ads/{ad_id}/decision` body `{ "ad_id": str | null, "decision": "approved" | "rejected", "reviewer": str, "note": str | null }` returns `ApprovalDecision` with server UTC `decided_at`. Body ID, when supplied, must match the URL. Missing verdict is 409. Latest decision is persisted atomically; every decision emits a durable `ad_decided` event.
- `GET /runs/{run_id}/export` returns `{run_id, exported_at, ads: [{ad_id, brief_id, business_id, format, path, image_url, decision}]}` and copies approved final ads to `approved/<business_id>_brief_<12-character-brief-hash>_<format>.png`. Writes `approved/manifest.json`; subsequent exports remove stale exported PNGs. `path` is relative to the run directory. No zip.
- `GET /clips` returns `list[ClipInfo]`: ClipEntry fields plus `clip_path`, `clip_url`, and `available`. Lists the union of manifest entries and local MP4 files; no analysis or decoding occurs.
- `GET /media/{run_id}/{path}` serves files from the run directory. `GET /clips/{name}` serves files from `sample_clips/`.
- `GET /seed/athletes`, `GET /seed/businesses`, `GET /seed/ad-styles` return the seed data.

API configuration: `GOLDCOAST_API_CORS_ORIGINS` is a JSON array, default `["http://localhost:5173"]`; `GOLDCOAST_SAMPLE_CLIPS_DIR` defaults to `sample_clips`. Media paths are confined, traversal is rejected, and clip responses support HTTP byte ranges for video seeking. Run IDs and ad IDs are validated before lookup or writing.

### CLI (`cli.py`)

- `goldcoast detect <clip>`: runs the video agent, prints `HypeMoment` JSON.
- `goldcoast match <moment.json>`: runs the matching agent, prints `AdBrief` JSON.
- `goldcoast generate <brief.json>`: runs the ad agent, prints `GeneratedAd` JSON.
- `goldcoast judge <ad.json>`: runs the judge, prints `QualityVerdict` JSON.
- `goldcoast run <clip>`: runs the full pipeline and prints the run id.
- `goldcoast validate-seed`: loads and validates all seed files.

## Critical Design Rules

- Stages communicate only through the typed models above. Model text is parsed into a model inside the agent, and parsing failures are retried once with a repair prompt before the stage fails.
- Every id referenced by an `AdBrief` or `GeneratedAd` must resolve to a record in the seed data. Agents never invent businesses, athletes, or styles.
- Every Gemini call is logged to `model_calls/` before its result is used.
- Each stage is runnable on its own through the CLI with a JSON file as input.
- The judge is a separate model call from generation and never edits an image. Its verdict is advisory to the human; it never auto-approves.
- Judge `scores.overall` is the minimum of business accuracy and the rounded five-criterion mean, computed in code. Wrong observed dimensions cap format compliance at 4. Judge-loop emission uses `emit(PipelineEventType, payload)` to match EventBus; `JudgedAd` contains final_ad, final_verdict, all (ad, verdict) attempts, and generation errors.
- Regeneration is bounded by `GOLDCOAST_JUDGE_MAX_RETRIES`. If every attempt fails, the highest-scoring attempt is kept, marked `passed: false`, and shown to the reviewer with its issues.
- Replay mode never touches the network. Tests run in replay mode by default.
- Full-run replay loads recorded moments/frames and seed/settings snapshots, creates new run-scoped IDs with deterministic child suffixes, and copies original model images into the new recording directory. It needs no source MP4 or mutable manifest for detection. Seed assets and normalized final images are run-local. Secrets are excluded from settings snapshots. The replayed clip path must match the source run.
- EventBus persists a complete JSONL event before notifying subscribers across threads. Subscription captures backlog and registers live delivery under one lock; `subscribe(after)` resumes after a zero-based event ID. API callers may pre-create a Run/EventBus and pass them to Pipeline.run, avoiding duplicate run IDs.
- Video analysis is never repeated for a clip whose manifest entry is already `analyzed: true`, unless the caller passes `--force-analysis`. A manifest hit emits `clip_manifest_hit` so the UI can show that the clip was recognized and whether its moments were hand-edited.
- The manifest is written atomically and only by the video agent and the matching agent's athlete write-back. No other code modifies it.
- Ad formats are exactly the two in `AdFormat`. Generated images are verified against the target dimensions and resized only if the model returns the correct aspect ratio at a different size.
- Secrets live only in `.env`. `output/`, `sample_clips/*.mp4`, and `.env` are gitignored.
- The web UI reads and writes only through the API. It never touches the filesystem or Gemini directly.
- Files are written atomically (write to a temp file, then rename) so the SSE stream never reads a partial artifact.
- On Windows, atomic replacement retries sharing/access violations (WinError 5/32) up to six attempts with bounded backoff (310 ms total). API validation exposed readers briefly preventing replacement of `run.json`; other errors still fail immediately and a persistent sharing failure remains an error.

## Intentional Design Decisions — Preserve During Rebuild

- Pre-recorded clips instead of a live stream. The vision is live analysis, but the first versions read MP4 files so the demo is deterministic. `ClipSource` exists so a stream source can be added without changing agents.
- Seed JSON instead of a database. Hand-editable files are the source of truth for athletes, businesses, and styles. Do not replace with a database unless a spec calls for it.
- The clip manifest is keyed by file name, not content hash, and doubles as the analysis cache. This is a deliberate simplicity choice: the owner curates a handful of clips and wants to edit timestamps and athlete ids by hand. Renaming a clip means it is treated as new.
- The MVP is one athlete and one clip. Nothing in the contracts is single-athlete specific, but the seed data, tests, and demo flow are built around one gymnastics clip of Simone Biles first. Do not generalize the demo to multiple athletes until that flow works end to end.
- The hype frame is the hero image and always appears in the ad. The athlete portrait serves two roles: an identity reference so the athlete stays consistent, and, when the athlete's face is not clearly visible in the hero frame (mid-air, turned away, small in frame), a foreground cutout overlay placed beside the business's product or offering. The model is never asked to redraw or synthesize the athlete's face; it composes with the real images it is given.
- Ads are framed as discovery, not endorsement. The copy invites visitors to explore the athlete's interests near the venue ("Simone's pick after a big routine? Find out at Slice House") rather than stating that the athlete endorses or recommends the business. Only facts present in the athlete's seed profile may be referenced. This is a copy rule enforced by the matching agent's headline direction and checked by the judge under brand safety.
- The image model produces the whole ad, including text. Rendering text inside generated images can be imperfect. This is accepted for the hackathon and mitigated by the judge's `business_accuracy` and `format_compliance` checks rather than by a Pillow overlay step.
- Judge verdicts are advisory. Even a passing ad requires a human decision. Even a failing ad after all retries is shown, flagged, so the reviewer can still approve it.
- Replay mode is a first-class feature, not a test shim. The demo may run entirely from cached outputs.
- Server-Sent Events instead of WebSockets. Events flow one way from server to UI, and SSE keeps the API simpler.
- Exactly two ad formats. Landscape for digital billboards, portrait for reels. Additional formats are a stretch goal, not a config knob.
- Matching is tag overlap first, LLM re-rank second. A business with no overlapping tag can never be matched, even if the model suggests it. This keeps matches explainable.


## Marketing pivot: additive Strands runtime (0009)

`agents/runtime.py` introduces `AgentRuntime`, `ExecutionBudget`, and a metered
Strands Model adapter. Strands 1.55.1 runs registered application tools through
a real agent loop; a native Gemini structured-output request then validates
the result. Both conversational and structured-output requests consume the
shared model allowance. Gemini SDK and Strands automatic retries are disabled.

Each invocation records the full typed request, schema/tool specifications,
request digest, model ID, timestamp, tool results, provider response chunks,
usage when supplied by the provider, latency, and final output or failure.
Provider configuration and invocation internals are excluded. Recordings are
written atomically before results leave the runtime. Replay requires an exact
request digest and a completed recording, never constructs a model, and never
runs tools. Missing/mismatched/failed recordings raise ReplayMissError.

Budget reservations are serialized across threads and accept a durable reserve
callback for spec 0010. Cancellation and the 100,000-character context limit
are checked before subsequent requests. Tool dispatch is sequential within an
agent; separate specialist runtimes can share one budget. Legacy pipelines and
recording formats are unchanged by this additive integration.


## Studio foundation (0010)

The studio serves only /api/v2 authenticated routes from goldcoast.api.studio_app. JWT issuer and subject establish a tenant; client-supplied tenant IDs never select user data. PostgreSQL stores versioned resources, durable jobs, per-job event cursors, account grants and singleton global controls. Paid work atomically consumes one account and global grant, with one active live job per tenant. Each provider call requires a running job and valid worker lease, enabled live controls, and remaining durable allowance. Replay cannot invoke providers. Terminal transitions and their event are atomic. OIDC uses Keycloak locally and Cognito in AWS. Media stays private behind authenticated resource lookup.


## Visual brand library (0011)

Studio business profiles and brand kits are separate versioned resource documents. Only owners confirm factual products/offers and inferred brand preferences. Immutable assets are tenant-scoped, content-hashed and validated before storage. Image uploads are normalized to PNG; documents/fonts are served as downloads. Brand analysis passes image/PDF bytes to a recorded Gemini call and cannot self-confirm its result. Confirmed kits require owned visual references. Profile and kit versions form later campaign snapshot boundaries.


## Evidence graph (0012)

Studio discovery records Tavily and optional Ticketmaster requests without credentials. Exact completed requests are cached; replay has no live fallback. Extraction is restricted to public URLs discovered in the same workflow. Evidence is untrusted input. Typed graphs retain source URLs, content hashes, retrieval/expiry timestamps, exact supporting quotes, and conflicting values. Fresh supported claims may inform opportunities, but only owner-confirmed profiles establish business products and offers.


## Chief workflow (0013)

Daily jobs capture business/brand versions, asset metadata and the business-local date. Chief planning, local scouting, cultural scouting and chief selection exchange typed outputs through the Strands runtime. Candidates must use owner-listed products and fresh, supported graph sources. Weak evidence produces a labeled evergreen option. Completed stage checkpoints are reusable; pending stages fail safely after interruption. Worker heartbeat renewals do not overwrite checkpoints. Replay copies an owned completed snapshot and constructs no providers. Brand jobs produce a separate unconfirmed draft; they never silently overwrite the active kit.
