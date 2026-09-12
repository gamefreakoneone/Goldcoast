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

`run` is a command stub until pipeline orchestration is implemented.

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
