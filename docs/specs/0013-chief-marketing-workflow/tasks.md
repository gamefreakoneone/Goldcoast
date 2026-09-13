# Tasks: chief marketing workflow

- [x] Read requirements and design.
- [x] Add typed plans, scout results, candidate validation and chief selection.
- [x] Implement snapshot starts, reserved brand analysis and optional video evidence.
- [x] Implement worker leases, resumable stage checkpoints and provider accounting.
- [x] Expose authenticated start/result/graph routes.
- [x] Test complete orchestration with typed fake providers, replay, cancellation, recovery and unsupported candidates.
- [x] Update status, design, README and commit.

## Validation Steps

`python -m pytest tests/test_studio_workflow.py tests/test_studio_brand.py tests/test_studio_foundation.py -q -p no:cacheprovider --basetemp output/pytest-0013`

`python -m ruff check .`

`python -m ruff format --check .`

`python -m goldcoast.studio.worker --help`

Expected: typed orchestration chooses supported real-product angles, provider counters remain durable, replay invokes no providers, interrupted stage does not repeat, and all auth/brand tests pass.
