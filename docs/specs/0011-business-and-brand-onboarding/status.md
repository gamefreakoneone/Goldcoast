# Status: 0011 business and brand onboarding

Completed

## Evidence

- `python -m pytest tests/test_studio_brand.py tests/test_studio_foundation.py -q -p no:cacheprovider --basetemp output/pytest-0011-fixed`: 12 passed, 1 existing deprecation warning, 42.78s.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 157 files already formatted.
- Actual PNG bytes roundtrip through private storage and reach the multimodal provider seam. Invalid image/PDF/font signatures, oversize payloads, missing rights confirmation, foreign asset references and stale versions are rejected. Model-supplied confirmation is cleared.
- Initial run found a missing shared test fixture import; fixed explicitly and reran all targeted tests successfully.

## Shared design changes

Business facts and brand preferences use separate versioned typed documents. Uploads are immutable private assets with content hashes and owner-confirmed rights. Analysis is a separate worker operation; upload/save endpoints never invoke providers. A confirmed kit requires owned visual references. Recorded analysis returns an unconfirmed draft for review.
