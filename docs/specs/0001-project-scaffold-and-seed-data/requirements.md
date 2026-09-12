# Requirements: 0001 Project Scaffold and Seed Data

## Goal

Stand up the Python project so every later spec has a working environment, typed models for all shared contracts, validated seed data, and a CLI entry point. After this spec, `python -m goldcoast validate-seed` passes on the real seed files and `pytest` runs green.

## Functional Requirements

- A Conda environment defined by `environment.yml` with Python 3.12 and ffmpeg, and a `pyproject.toml` that installs the `goldcoast` package from `src/` with the dependencies listed in `TECHNICAL_DESIGN.md`.
- A `.env.example` listing every environment variable from `TECHNICAL_DESIGN.md` with safe defaults and no real secrets.
- A `settings` module that loads `.env`, exposes typed settings, and fails with a clear message if `GEMINI_API_KEY` is missing and replay mode is off.
- Pydantic v2 models for all seed and pipeline contracts in `TECHNICAL_DESIGN.md`: `Athlete`, `Business`, `AdStyle`, `Venue`, `AdFormat`, `HypeMoment`, `AdBrief`, `GeneratedAd`, `QualityVerdict`, `ApprovalDecision`, `PipelineEvent`, `Run`, and the clip manifest models `ClipEntry` and `ManifestMoment` with a loader and atomic saver for `sample_clips/manifest.json`.
- Loaders for `data/athletes.json`, `data/businesses.json`, `data/ad_styles.json`, and optional `data/venues.json` that validate every record, reject duplicate ids, fail when an athlete shares no tag with any business, and warn about athlete tags that no business uses.
- Seed data files populated with the project owner's data per `docs/DATA_REQUIREMENTS.md`, or with clearly fictional starter records if that data is not yet available.
- A Typer CLI at `python -m goldcoast` with a `validate-seed` command and stubs for `detect`, `match`, `generate`, `judge`, and `run` that print "not implemented" and exit non-zero.
- A Gemini client wrapper that creates `genai.Client()` from settings and records every call to a `model_calls/` directory, with the recording interface defined now so later specs only add calls.
- `.gitignore` covering `.env`, `output/`, `sample_clips/*.mp4`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `web/node_modules/`, `web/dist/`.
- Tests for model validation and the seed loaders.

## Inputs and Outputs

- Inputs: seed JSON files under `data/`, `.env`.
- Outputs: installed package, validated seed data in memory, CLI commands, test suite.

## Out of Scope

- Any Gemini call that produces pipeline output. The client wrapper is built but only exercised by a smoke test that can be skipped without a key.
- The web frontend.
- Run directories and event persistence beyond the model-call recorder.

## Dependencies

- None. This is the first spec.
- Project owner input: seed data per `docs/DATA_REQUIREMENTS.md` and a Gemini API key.
