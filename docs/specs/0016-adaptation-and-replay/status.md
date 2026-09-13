# Status: 0016 adaptation and replay

Completed

## Evidence

- `python -m pytest tests/test_studio_replay.py tests/test_studio_schedule.py tests/test_studio_workflow.py tests/test_studio_creative.py -q`: 16 passed in 13.27 s. Validates real packaged images/hashes, forbidden provider construction, zero grants/counters, unchanged existing setup, tenant isolation, independent replay approvals, historical export, path/tamper rejection, disabled/due scheduling, idempotency, version conflicts, expired-claim clamping and existing live freshness rules.
- `python scripts/check_studio_schedule.py`: actual PostgreSQL isolated temporary schema; 8 concurrent scheduler ticks created exactly 1 job and consumed exactly 1 grant. Temporary schema removed after validation; no live workers or providers saw those jobs.
- `python scripts/check_studio_browser.py --phase sample`: actual demo account OIDC login, free sample start, fully loaded private PNGs, two independent approvals and ZIP export, enable/disable schedule. 390px layout had no horizontal overflow; page errors empty. A loading-state race in schedule inputs was fixed by disabling edits until saved settings load.
- Actual demo replay d0d35bf656c3400fb31c635bbc994744 completed with counters `{}` and both account grants zero; global live remained disabled. Demo profile/brand stayed empty. Final schedule disabled. Screenshot output/studio-browser/sample-replay.png inspected using view_image; historical notice, date, media, judge scores and controls rendered correctly. ZIP output/studio-browser/sample-campaign.zip includes historical manifest and real PNGs.
- `pnpm.cmd --dir web test`: 6 files, 16 passed (17.88 s).
- `pnpm.cmd --dir web lint`: passed. `pnpm.cmd --dir web build`: passed; lazy marketing JS 50.64 kB (15.23 gzip).
- `python -m ruff check .`: all checks passed. `python -m ruff format --check .`: 198 files already formatted.

## Contract changes

Replay creative rows reference the immutable recorded snapshot, carry replay=true, and require an owned replay-mode job before bypassing current-business freshness checks. They preserve historical evidence dates and independently reset decisions. Live behavior still requires current version/expiry. ZIP export holds the tenant lock across approval/freshness checks to prevent concurrent business edits invalidating an export mid-read. Candidate expiry now includes supporting claim deadlines, not only source cache expiry. Schedule state is a versioned singleton; default disabled, deterministic per-account/local-date reservation, same grants/kill switch. Packaged replay hashes and paths are validated before use.
