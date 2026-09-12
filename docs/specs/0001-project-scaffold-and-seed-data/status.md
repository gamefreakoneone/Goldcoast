# Status: 0001 Project Scaffold and Seed Data

## Status

Completed

## Evidence

Validation completed on Windows 11 in the `goldcoast` Conda environment on 2026-09-12.

```powershell
conda env create -f environment.yml
```

Result: environment created successfully with Python 3.12.14 and ffmpeg 9.0.1.

```powershell
conda activate goldcoast
pip install -e ".[dev]"
```

Result: editable wheel built and `goldcoast==0.1.0` installed successfully with runtime and development dependencies.

```powershell
ffmpeg -version
```

Result: `ffmpeg version 9.0.1`, exit code 0.

```powershell
python -m goldcoast validate-seed
```

Result:

```text
athletes: 3
businesses: 6
ad_styles: 3
venues: 3
```

```powershell
pytest
```

Result: `21 passed in 1.68s` on Python 3.12.14.

```powershell
ruff check .
```

Result: `All checks passed!`

```powershell
ruff format --check .
```

Result: `63 files already formatted`.

### Housekeeping revalidation — 2026-09-12

The non-interactive PowerShell session needed its Conda hook loaded before activation. Commands used:

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
python -m goldcoast validate-seed
pytest
pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
```

`validate-seed` exited 0: `athletes: 1`, `businesses: 3`, `ad_styles: 2`, `venues: 2`. Expected warning: unmatched tags `american, dessert, dogs, fashion, gymnastics, horseback_riding, shopping, spa, tennis, walking, wellness`.

Initial `pytest`: `1 failed, 8 passed, 13 errors`. Temporary-directory errors were `PermissionError: [WinError 5] Access is denied: ...\\Temp\\pytest-of-amogh`. The failing assertion required both logo dimensions to be 512, whereas `docs/DATA_REQUIREMENTS.md` requires 512 on the long side. Corrected the assertion to `max(image.size) >= 512`, preserving the supplied logos. The first fallback invocation found the `output/` parent missing; created it and reran the exact fallback command.

Final results: `22 passed in 1.30s`; `ruff check .`: `All checks passed!`; `ruff format --check .`: `65 files already formatted`.

## Blockers

None.

## Change Log

- 2026-09-12: Spec created.
- 2026-09-12: Implemented the project scaffold, shared contracts, seed validation, fictional demo data and logos, manifest persistence, Gemini call recording, CLI commands, and tests.
- 2026-09-12: Completed all validation steps and marked the spec Completed.
- 2026-09-12: Post-completion data change. Replaced fictional seed data with the Simone Biles MVP set (one athlete, three real LA businesses, two styles, two venues). Made `Business.offer_text` optional, relaxed the unmatched-tag check from error to warning (zero overlap is still an error), and added warning output to `validate-seed`. Tests updated and passing.
- 2026-09-12: Revalidated planning and MVP seed changes, aligned the logo test with the documented long-side requirement, and documented the Windows pytest fallback in README.
