# Tasks

- [x] Freeze typed contracts, UI behavior and spec.
- [x] Implement transport, linking, poller, receipts and offset migration.
- [x] Implement notifications, shared decisions, regeneration and feedback.
- [x] Implement Settings and Review behavior.
- [x] Author offline transport, lifecycle, authorization, conflict, replay, outage, idempotency and UI tests.
- [x] Run validation and record evidence.
- [ ] Link real bot, receive saved previews, approve/reject and verify safe regeneration Conflict.
- [x] Update shared design/README/ledger and commit 0023 separately.

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

No tests access the network. Manual acceptance reuses 0022 creatives without consuming a second campaign grant; if missing allowance or expired images block checks, record that explicitly.
