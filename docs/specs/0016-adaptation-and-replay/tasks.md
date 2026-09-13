# Tasks: adaptation and replay

- [x] Read requirements and design.
- [x] Package real campaign with typed data and hashed image assets.
- [x] Implement tenant-isolated sample/owned replay cloning and historical labels.
- [x] Implement schedule API/worker tick and expiry/invalidation corrections.
- [x] Connect free sample and opt-in schedule controls in UI.
- [x] Test zero-provider replay, tenant isolation, independent decisions, tamper rejection, scheduling idempotency and expiry.
- [x] Validate browser replay/export for a zero-grant account, lint/build/tests, update evidence and commit.

## Validation Steps

`python -m pytest tests/test_studio_replay.py tests/test_studio_schedule.py tests/test_studio_workflow.py tests/test_studio_creative.py -q`

`python -m ruff check .` and `python -m ruff format --check .`

`pnpm.cmd --dir web test`, `pnpm.cmd --dir web lint`, `pnpm.cmd --dir web build`

Use authenticated Chrome to start sample replay while global live is paused and account has zero grants; inspect real images, historical labels and independently approve/export. Verify DB counters remain empty, no new provider records, and existing business/brand values are unchanged. Enable/disable schedule without live calls; offline tests verify due-time and duplicate behavior.
