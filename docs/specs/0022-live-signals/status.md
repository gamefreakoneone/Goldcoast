# Status: 0022 Live signals

Blocked: implementation and automated validation complete; live campaign evidence and replay acceptance remain pending. During the owner's 0023 follow-up, Demo Reviewer and the shared budget were topped up to five campaign grants as explicitly requested, resolving the earlier allowance blocker. No weather campaign was generated in that follow-up. Historical evidence below describes the original zero-credit state.

## Evidence

### 2026-09-14 creative direction follow-up

Both directors now receive validated SignalsResult and require WeatherInfluence on new brief output. Historical briefs keep null influence and an explicit UI notice. Regeneration restores the original local_signals without fresh provider requests. The owner-generated original 3089976d103d43469a82640bf94f4436 and Telegram revision 6d67369c467645be88a6a1cae76ac6a1 both completed with available weather; these historical ads were not rewritten. No live generation or campaign grant was consumed in this follow-up. Full original two-placement/replay acceptance remains unchecked.

- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m pytest -q`: 197 passed, one existing Starlette/AnyIO warning, 227.11s.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff check .`: All checks passed.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff format --check .`: 239 files already formatted.
- `pnpm.cmd --dir web test --maxWorkers=1`: 29 passed; existing legacy App replay test exceeded 5000ms under concurrent validation.
- `pnpm.cmd --dir web test --maxWorkers=1 --testTimeout=15000`: all 30 tests / 11 files passed, 90.28s, including expanded weather explanation/historical fallback UI test. No source timeout was changed.
- `pnpm.cmd --dir web lint`: passed.
- `pnpm.cmd --dir web build`: passed, 56 modules, 8.03s.
- `C:/Users/amogh/anaconda3/envs/goldcoast/Scripts/alembic.exe upgrade head`: exit 0; `alembic.exe current`: 0023_telegram_offset (head).
- `git -c safe.directory=C:/Users/amogh/Desktop/Goldcoast diff --check`: passed.

Shared design and README now document the typed new-output/historical distinction and original-weather reuse. Automated tests verify direct context for both directors, new required schema, historical compatibility, saved forecast reuse and zero-provider regeneration/replay. Real rendered Review verification follows with the 0023 continuity change.

Commands ran with the goldcoast Conda environment on PATH (C:/Users/amogh/anaconda3/envs/goldcoast).

- `python -m pytest -q`: 161 passed, 1 existing Starlette deprecation warning, 157.77s.
- `python -m pytest tests/test_studio_signals.py -q`: 12 passed, 1 existing warning, 11.18s. Forecast requests/cache/tool accounting, four supported claims, DST expiry, unavailable/malformed forecasts, cancellation, campaign continuation, API shape, product skip and zero-provider checkpoint replay.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 232 files already formatted.
- `pnpm.cmd --dir web test --maxWorkers=1`: 9 files, 23 tests passed, 58.51s. Includes weather chips/provider label.
- `pnpm.cmd --dir web lint`: exit 0.
- `pnpm.cmd --dir web build`: exit 0; Vite 6.4.3, 55 modules transformed.
- `alembic upgrade head`: exit 0 against local PostgreSQL; this spec adds no migration.
- `git diff --check`: exit 0.

Frontend checks initially failed because the sandbox could not read installed pnpm dependencies. The same commands passed outside the sandbox; dependencies and lockfile were unchanged.

## Shared design changes

TECHNICAL_DESIGN.md documents weather provider, local_signals stage, deterministic verbatim claims and business-local day-end expiry. ProviderCassette.call accepts optional budget_kind so named geocode/forecast recordings reserve tool allowance while retaining exact payloads. Result API adds local_signals and preserves existing graph access. Margin already uses Los Angeles.

## Remaining acceptance

Generate one live two-placement Margin campaign, inspect Review weather evidence, and replay with empty counters. Preserve originals for 0023. Do not exceed one live campaign across both specs. 0021 scope is untouched.
