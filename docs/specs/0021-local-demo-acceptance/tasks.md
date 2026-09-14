# Tasks

- [x] Source images and create original demo branding/catalog assets.
- [x] Add idempotent local demo loader and capped grants.
- [x] Complete live discovery and fix observed token/schema failures with bounded handling.
- [x] Verify Chrome desktop/mobile layout, persisted classification and historical replay/review/export.
- [x] Run full tests/lint/build and document the local handoff.
- [ ] Complete actual mixed-file Chrome transfer after extension file-URL permission or manual user testing.
- [ ] Obtain approval for one additional isolated live campaign attempt.
- [ ] Finish live creative generation, judge, approval/export and zero-call social replay acceptance.

## Validation Steps

Run full pytest, Ruff check/format check, pnpm frontend test --maxWorkers=1, lint and build. Test sample loader idempotency and non-overwrite. Inspect populated Today/library/feed in Chrome, run one capped live campaign from fresh discovery, verify judge and approval/export and replay with zero counters. Record provider counters, artifact dimensions and paths without secrets.
