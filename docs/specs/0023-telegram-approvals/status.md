# Status: 0023 Telegram approvals

Blocked: implementation and automated validation complete; real-bot/live acceptance awaits the intended Margin account, one-credit authorization, and the owner's Telegram connection. No campaign credits were added or spent. Both local Margin accounts (Margin acceptance and Demo Reviewer) have zero credits; no notifications Resource exists. Token and bot link are configured (values were not printed).

## Evidence

Python commands ran with the goldcoast Conda interpreter, C:/Users/amogh/anaconda3/envs/goldcoast/python.exe.

- `python -m pytest -q`: 188 passed, 1 existing Starlette deprecation warning, 144.75s.
- `python -m pytest tests/test_studio_notify.py -q`: 25 passed, 1 existing warning, 22.81s after final callback conflict handling. Covers authenticated routes and hidden internal fields; link lifecycle/expiry; multipart HTML escaping and timeouts; unauthorized chats; approval provenance/stale versions; reject reason/Skip; regeneration options, allowance/idempotency/expiry/ownership/active-job conflicts; disabled/replay suppression; offset and receipt restart behavior; send outages with terminal job preservation; six-photo cap; replay decision reset; both directors and refinement feedback.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 239 files already formatted.
- `pnpm.cmd --dir web test --maxWorkers=1`: 11 test files, 29 tests passed, 56.75s. Includes Settings states/link polling/toggle/disconnect/unmount and completed Review polling/phone label/notification events.
- `pnpm.cmd --dir web lint`: exit 0.
- `pnpm.cmd --dir web build`: exit 0; Vite 6.4.3, 56 modules, 3.88s.
- `alembic upgrade head`: exit 0 against local PostgreSQL.
- `alembic current`: 0023_telegram_offset (head).
- `git diff --check`: exit 0.

Frontend commands used approved execution outside the sandbox to read the existing pnpm dependencies. No dependencies or lockfiles changed. Tests use stub transports and deny network connections.

## Rendered UI verification

Browser plugin not available; used the existing Python Playwright installation with headless Chrome. Target flow: Settings -> Connect Telegram -> deep link and raw /start fallback -> polled Connected as Sam. API/auth responses were fixture-only: this is UI evidence, not real Telegram acceptance.

Commands: `pnpm.cmd --dir web dev --host 127.0.0.1 --port 5175 --strictPort`, then `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe C:/Users/amogh/AppData/Local/Temp/goldcoast-telegram-ui.py`.

| Check | Result |
|---|---|
| Page identity | http://127.0.0.1:5175/#/settings; Goldcoast - Local discovery studio |
| Meaningful content | Settings, account, Telegram and schedule cards rendered |
| Framework overlay | None |
| Console/page errors | Empty |
| Interaction | Connect displayed deep link/fallback, polling displayed Connected as Sam |
| Desktop | 1440x1000; screenshot visually inspected |
| Mobile | 390x844; no horizontal overflow, screenshot visually inspected |

Screenshots: C:/Users/amogh/AppData/Local/Temp/goldcoast-0023-qa/settings-link-desktop.png and settings-connected-mobile.png. Temporary Playwright fixture initially returned empty bodies for JSON null; fixed the fixture and reran successfully. No application failure remained.

## Shared contracts and operational limits

TECHNICAL_DESIGN.md records the notification APIs/internal pending state, decided_via, regeneration snapshot/expiry semantics, notification_ready and sent/failed events, migration/offset, and conservative at-most-once receipts. README documents BotFather setup, exact lowercase environment names, connection flow, full-resolution ZIP distinction, single-worker operation and crash behavior. Telegram long polling has a 30-second read timeout; ordinary requests use ten seconds. Reject uses ForceReply plus a separate Skip-button message because Telegram accepts one reply markup per message.

A failed or interrupted claimed action is not automatically retried. New explicit owner action is required after ambiguous delivery/crash; no exactly-once delivery is claimed. Live snapshots still reject changed versions and expired evidence. Replay resets decisions/provenance and sends nothing.

## Remaining manual acceptance

After the pending credit/account answer, generate the one two-placement 0022 weather campaign and verify its evidence and zero-call replay. Connect the real bot from Settings on the chosen account, explicitly send that run's still-eligible saved creatives, approve one, reject another with a reason, and observe Review. Exercise regeneration only when a preflight guarantees no second credit can be consumed (or seek separate authorization). If images expire or no allowance is available, preserve the blocker; do not fake passing acceptance. 0021 and the legacy Olympics pipeline remain untouched.
