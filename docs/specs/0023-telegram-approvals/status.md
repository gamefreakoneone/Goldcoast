# Status: 0023 Telegram approvals

Blocked: implementation and automated validation complete; full phone preview/decision acceptance still awaits the 0022 live campaign. The owner has now linked Demo Reviewer and requested a five-credit top-up, completed below. Earlier zero-allowance and missing-link blockers are resolved. No campaign was generated during this follow-up.

## Owner-requested bot commands and demo cleanup

Added native /start, /commands, /campaign, /status and /credits, plus /help and /commnads help aliases. /campaign uses the existing metered workflow and durable update idempotency, while /start without a link code is free help. Missing/ambiguous chats cannot access account commands. Disabled approvals, invalid briefs, depleted allowance and active-job conflicts do not start a campaign. Removed the visible Source attribution link from Brand library cards; stored provenance remains. README, shared contracts and this spec describe the behavior.

The existing Demo Reviewer tenant dcce8d173adb5c65ab2a1f0c87a48751 was topped up from 0 to 5 campaign grants; shared controls from 2 to 5. A transaction used max(5, current), retaining usage and other allowances. Recheck before worker restart: active_jobs=0, campaign_credits=5, shared_credits=5. The real bot connection is present. Restarted only the identified idle marketing worker, PID 29040 -> 4928, with a hidden window. No generation or synthetic phone decision was sent.

Validation (Python environment C:/Users/amogh/anaconda3/envs/goldcoast):

- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m pytest tests/test_studio_notify.py -q`: 33 passed, one existing Starlette/AnyIO deprecation warning, 20.51s.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m pytest -q`: 196 passed, same warning, 188.86s.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff check .`: All checks passed. Initial check found two long new strings; split them and reran successfully.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff format --check .`: 239 files already formatted.
- `pnpm.cmd --dir web test --maxWorkers=1`: 11 files, 30 tests passed, 84.98s.
- `pnpm.cmd --dir web lint`: passed (tsc and eslint).
- `pnpm.cmd --dir web build`: passed, 56 modules, 3.68s.
- `C:/Users/amogh/anaconda3/envs/goldcoast/Scripts/alembic.exe upgrade head`: exit 0; `alembic.exe current`: 0023_telegram_offset (head).
- `git -c safe.directory=C:/Users/amogh/Desktop/Goldcoast diff --check`: passed.
- Real Telegram getMyCommands through the sanitized client returned start, commands, campaign, status, credits after worker restart. No token or transport URL was printed.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe C:/Users/amogh/AppData/Local/Temp/goldcoast-bot-brand-check.py`: actual local OIDC demo login and Brand library, source_attribution_count=0. Screenshot C:/Users/amogh/AppData/Local/Temp/goldcoast-0023-qa/brand-no-attribution.png visually inspected; inspiration cards retained without attribution links.

New offline tests cover free help before linking, typo alias, linked status/credits, unlinked command isolation, long briefs, disabled notifications, depleted allowance, active-job conflicts, repeated campaign updates consuming exactly one grant, and native menu payload/timeouts. End-to-end generation and physical-phone decisions remain unchecked; the available credits are left for the owner. Historical evidence below describes the earlier state.

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

## Follow-up: stale running API and loading error

The user's actual Settings page displayed Loading Telegram settings with Not Found. GET http://127.0.0.1:8001/openapi.json returned no notification routes: the API process predated 0023. Confirmed zero active jobs, then restarted only the identified studio API and worker. The running OpenAPI document now contains /notifications/config, /notifications, /notifications/telegram/link and /notifications/telegram. No credits were added or spent.

TelegramPanel now exits loading on request failure, explains that missing routes require an API/worker restart, and offers Retry Telegram settings. A regression test covers failure -> retry -> Connect button.

- `pnpm.cmd --dir web test --maxWorkers=1 src/test/telegram.test.tsx`: 5 passed, 10.10s.
- `pnpm.cmd --dir web lint`: passed.
- `pnpm.cmd --dir web build`: passed.
- `git diff --check`: passed.
- Actual local OIDC login as demo using existing private credentials, then Settings: Connect Telegram visible, loading count 0, Not Found count 0. No fixtures, no Telegram link mutation, no generation. Playwright script: C:/Users/amogh/AppData/Local/Temp/goldcoast-telegram-live-check.py. Screenshot visually inspected: C:/Users/amogh/AppData/Local/Temp/goldcoast-0023-qa/settings-live-fixed.png.

Full campaign/phone-decision acceptance remains Blocked as above; this fixes access to the linking UI.
