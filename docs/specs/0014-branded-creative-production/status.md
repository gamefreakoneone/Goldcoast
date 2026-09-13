# Status: 0014 branded creative production

Completed

## Evidence

- `python -m pytest tests/test_studio_creative.py tests/test_studio_workflow.py -q -p no:cacheprovider --basetemp output/pytest-0014-fixed`: 10 passed, 1 existing deprecation warning, 8.45s.
- `python -m pytest tests/test_studio_foundation.py tests/test_studio_brand.py tests/test_studio_discovery.py -q -p no:cacheprovider --basetemp output/pytest-0014-api`: 16 passed, 1 warning, 8.67s.
- `python scripts/check_studio_compositor.py`: landscape 1920x1080 and portrait 1080x1920, no overflow. Actual installed Chrome rendered both with network requests blocked.
- Inspected both output/compositor-probe PNGs with view_image: intact logo, readable headline/body/CTA, correct food crop and dimensions, no clipping.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 183 files already formatted.
- Installed Playwright 1.62.0 for the backend compositor. User-facing browser QA remains Chrome computer use.
- Initial creative tests needed an explicit dependency fixture import; corrected and reran successfully.

## Shared design changes

Studio creatives reference a business snapshot and brand ID, without requiring Olympics seed athlete/style IDs. Actual uploaded images guide generated backgrounds; trusted templates place exact text and original logos/fonts. Final composites receive typed judge verdicts before review. At most three attempts per format; factuality/legibility failures stop expensive image retries early. Approval/export require passing verdicts, current profile/brand versions and unexpired opportunities/offers. Full final composite bytes are saved beside model recordings for audit. No live paid calls were made in this spec.
