# Tasks

- [x] Add named campaign-video asset contracts, upload validation and private frame storage.
- [x] Implement bounded video analysis, timestamp validation and deterministic frame extraction.
- [x] Pass typed video evidence and the selected frame through discovery, planning and both creative producers.
- [x] Reuse original video evidence for regeneration and replay without provider calls.
- [x] Add website upload, selection and Review evidence UI; remove testimonial-facing controls.
- [x] Resolve current-account campaign videos from Telegram campaign briefs without premature grant use.
- [x] Author offline contract, ownership, extraction, propagation, replay, regeneration, Telegram and UI tests.
- [x] Update README, shared design and ledger.
- [x] Run validation, record evidence and commit spec 0024 separately.

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

No test or manual UI verification may start a live campaign. Verify desktop and mobile upload/selection/Review states using local fixtures or existing saved data. Confirm campaign and provider allowance counters are unchanged.
