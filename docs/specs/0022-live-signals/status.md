# Status: 0022 Live signals

Blocked: implementation and automated validation complete; live acceptance awaits authorization to add one credit to the intended Margin account. Both local Margin tenants have zero campaign_grants. No live campaign or grant mutation was performed.

## Evidence

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
