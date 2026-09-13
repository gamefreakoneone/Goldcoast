# Tasks: business and brand onboarding

- [x] Read requirements and design.
- [x] Implement typed profiles, asset validation/storage, and brand kit review.
- [x] Add authenticated profile, kit, upload and media routes.
- [x] Add recorded multimodal brand analysis helper.
- [x] Test real image upload, unsafe files, ownership and confirmation/version boundaries.
- [x] Update design/README/status and commit.

## Validation Steps

`python -m pytest tests/test_studio_brand.py tests/test_studio_foundation.py -q -p no:cacheprovider --basetemp output/pytest-0011`

`python -m ruff check .`

`python -m ruff format --check .`

Expected: bounded valid assets roundtrip privately, invalid files and foreign references fail, inferred kits cannot self-confirm, version conflicts fail, existing auth tests remain green. No paid calls during tests.
