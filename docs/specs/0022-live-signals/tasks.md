# Tasks

- [x] Pass typed weather to both directors and require new brief influence explanations.
- [x] Restore saved weather for regeneration without new requests.
- [x] Display influence and historical missing-explanation state in Review.
- [x] Record follow-up validation evidence.

- [x] Freeze contracts and write spec.
- [x] Implement weather requests, evidence, workflow, API and UI.
- [x] Author offline request, failure, expiry, planning, replay and UI tests.
- [x] Run validation and record evidence.
- [ ] Validate one live two-placement Margin campaign and zero-provider replay.
- [x] Update README, shared design and ledger; commit 0022 separately.

## Validation Steps

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
pnpm.cmd --dir web test --maxWorkers=1
pnpm.cmd --dir web lint
pnpm.cmd --dir web build
alembic upgrade head
```

All automated checks pass without external network calls in tests. Live Review shows local_signals and weather evidence; replay counters are empty.
