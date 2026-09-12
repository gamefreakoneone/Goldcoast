# Design: 0001 Project Scaffold and Seed Data

## Overview

This spec creates the package skeleton, the typed contracts that every later stage depends on, and the seed data loaders. It implements the seed and pipeline models from `TECHNICAL_DESIGN.md` verbatim so later specs never redefine them.

## Components

- `environment.yml`: Conda env `goldcoast` with `python=3.12`, `ffmpeg`, and `pip`. Pip dependencies are not listed here; they come from `pyproject.toml`.
- `pyproject.toml`: package `goldcoast`, `src` layout, dependencies and `[project.optional-dependencies].dev`, `ruff` and `pytest` configuration, console script `goldcoast = goldcoast.cli:app`.
- `src/goldcoast/__main__.py`: invokes the Typer app so `python -m goldcoast` works.
- `src/goldcoast/settings.py`: `Settings` Pydantic model built from environment variables with `python-dotenv`. Exposes `get_settings()` cached per process.
- `src/goldcoast/models/seed.py`: `Athlete`, `FoodPreference`, `AthleteIdentification`, `Business`, `BusinessCategory`, `AdStyle`, `Venue`.
- `src/goldcoast/models/pipeline.py`: `AdFormat`, `AD_FORMAT_SIZES`, `HypeMoment`, `AthleteHints`, `AdBrief`, `GeneratedAd`, `QualityVerdict`, `VerdictScores`, `ApprovalDecision`, `PipelineEvent`, `PipelineEventType`, `Run`, `RunStatus`.
- `src/goldcoast/models/manifest.py`: `ClipEntry`, `ManifestMoment`, and `ClipManifest` with `load(path)`, `save(path)` (atomic), `get(file_name) -> ClipEntry | None`, `upsert(entry)`.
- `src/goldcoast/data/loaders.py`: `SeedData` dataclass with `athletes`, `businesses`, `ad_styles`, `venues` as dicts keyed by id, and `load_seed(data_dir) -> SeedData` that validates and cross-checks tags.
- `src/goldcoast/llm/client.py`: `GeminiClient` wrapping `google.genai.Client`, with `generate(stage, model_id, contents, config) -> RecordedCall`. Each call is written to `<record_dir>/<stage>_<sequence>.json` before returning. `record_dir` is injected so later specs can point it at a run directory.
- `src/goldcoast/cli.py`: Typer app with `validate-seed` and stubbed stage commands.
- `data/*.json`, `data/assets/`: seed data and logos.
- `tests/test_models.py`, `tests/test_loaders.py`, `tests/test_settings.py`.

## Data Flow

`load_seed(Path("data"))` reads the four JSON files, parses each array into its model, builds dicts by id, and raises `SeedValidationError` with every problem found (not only the first). `validate-seed` calls it and prints counts per file on success.

## Interfaces

- `get_settings() -> Settings` with fields `gemini_api_key: str | None`, `video_model: str`, `image_model: str`, `judge_model: str`, `judge_max_retries: int = 2`, `judge_pass_threshold: int = 7`, `replay: bool = False`, `replay_run: str | None`, `output_dir: Path = Path("output")`, `data_dir: Path = Path("data")`.
- `load_seed(data_dir: Path) -> SeedData`.
- `GeminiClient(settings, record_dir: Path).generate(...) -> RecordedCall` where `RecordedCall` has `stage`, `sequence`, `model_id`, `prompt`, `input_refs`, `response_text`, `response_raw`, `latency_ms`, `timestamp`.
- CLI: `goldcoast validate-seed [--data-dir PATH]`.
- Seed file shapes are exactly as documented in `docs/DATA_REQUIREMENTS.md`.

## Error Handling

- Missing `GEMINI_API_KEY` with replay off: `get_settings()` raises `SettingsError` naming the variable and pointing at `.env.example`.
- Invalid seed record: `SeedValidationError` listing file, index, id if present, and the Pydantic error message for every failure.
- Duplicate id or dangling tag: included in the same error list.
- Gemini API errors: re-raised as `LLMCallError` after the call record is written with the error text in `response_raw`.

## Open Questions

- Which Gemini model ids to default to for video, image, and judge. Default: leave the three variables required in `.env.example` with a comment-free placeholder value that the settings loader rejects if unchanged, so the owner must choose.
- Whether starter seed data should be fictional. Default: fictional athletes and businesses with clearly invented names, replaced by the owner's data before the demo.
