# Goldcoast

Dynamic ad generation for the LA 2028 Olympics: an AI video agent spots hype moments in Olympics footage, and an ad-generation agent turns each moment into landscape and portrait ads for nearby local businesses, judged for quality and approved by a human through a web UI.

The first scaffold includes the shared data contracts, Simone Biles's profile, three real LA businesses, clip-manifest persistence, Gemini call recording, and command-line entry points. Pipeline stages are added by the later numbered specs.

## Setup

```powershell
conda env create -f environment.yml
conda activate goldcoast
pip install -e ".[dev]"
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

`detect`, `match`, `generate`, `judge`, and `run` are command stubs until their corresponding specs are implemented.

## Validation

```powershell
ffmpeg -version
python -m goldcoast validate-seed
pytest
ruff check .
ruff format --check .
```

If pytest cannot create its Windows temporary directory, create `output/` if needed and run `pytest -p no:cacheprovider --basetemp output/pytest-tmp`.

See [AGENTS.md](AGENTS.md) for working rules, [docs/FEATURE_STATUS.md](docs/FEATURE_STATUS.md) for feature progress, and [docs/DATA_REQUIREMENTS.md](docs/DATA_REQUIREMENTS.md) for production data requirements.
