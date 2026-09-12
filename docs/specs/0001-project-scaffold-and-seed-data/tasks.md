# Tasks: 0001 Project Scaffold and Seed Data

## Task List

- [x] Create `environment.yml` with Conda env `goldcoast`, `python=3.12`, `ffmpeg`, `pip`.
- [x] Create `pyproject.toml` with the `src` layout, runtime and dev dependencies, ruff and pytest config, and the `goldcoast` console script.
- [x] Create `.gitignore` per `requirements.md`.
- [x] Create `.env.example` with every variable from `TECHNICAL_DESIGN.md`.
- [x] Implement `src/goldcoast/settings.py` with `Settings` and `get_settings()`.
- [x] Implement `src/goldcoast/models/seed.py`.
- [x] Implement `src/goldcoast/models/pipeline.py` including `AD_FORMAT_SIZES`.
- [x] Implement `src/goldcoast/models/manifest.py` with `ClipManifest` load, atomic save, get, and upsert.
- [x] Implement `src/goldcoast/data/loaders.py` with `load_seed` and `SeedValidationError`.
- [x] Implement `src/goldcoast/llm/client.py` with `GeminiClient` and call recording.
- [x] Implement `src/goldcoast/cli.py` and `src/goldcoast/__main__.py` with `validate-seed` and stubbed stage commands.
- [x] Populate `data/athletes.json`, `data/businesses.json`, `data/ad_styles.json` and add logos under `data/assets/`.
- [x] Write `tests/test_models.py`, `tests/test_loaders.py`, `tests/test_settings.py`.
- [x] Update `README.md` with the setup commands.

## Validation Steps

```powershell
conda env create -f environment.yml
conda activate goldcoast
pip install -e ".[dev]"
ffmpeg -version
python -m goldcoast validate-seed
pytest
ruff check .
ruff format --check .
```

Expected: `ffmpeg -version` prints a version, `validate-seed` prints record counts for each seed file and exits 0, all tests pass, ruff reports no issues.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`.
- `docs/FEATURE_STATUS.md` shows 0001 as Completed with a link to the evidence.
- The spec is committed on its own.
