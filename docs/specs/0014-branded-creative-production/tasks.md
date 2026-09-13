# Tasks: branded creative production

- [x] Read requirements and design.
- [x] Add typed creative contracts, factual validation and controlled composition.
- [x] Add bounded reference-image generation, composite judging and worker integration.
- [x] Add tenant-scoped creative review, media and export endpoints with stale checks.
- [x] Test retries, missing/failed verdict restrictions, stale versions, private media, export and HTML escaping.
- [x] Render both exact sizes with real Chromium and inspect outputs.
- [x] Update status/design/setup documentation and commit.

## Validation Steps

`python -m pytest tests/test_studio_creative.py tests/test_studio_workflow.py -q -p no:cacheprovider --basetemp output/pytest-0014`

`python scripts/check_studio_compositor.py`

`python -m ruff check .`

`python -m ruff format --check .`

Expected: two correctly sized PNGs, no text overflow or external network, bounded retries, no export of unapproved/failed/stale/foreign assets, and passing offline regression tests. Inspect the compositor probe images with view_image.
