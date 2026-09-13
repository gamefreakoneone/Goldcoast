# Status: 0013 chief marketing workflow

Completed

## Evidence

- `python -m pytest tests/test_studio_workflow.py tests/test_studio_brand.py tests/test_studio_foundation.py -q -p no:cacheprovider --basetemp output/pytest-0013-final`: 18 passed, 1 existing deprecation warning, 28.08s.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 174 files already formatted.
- `python -m goldcoast.studio.worker --help`: exit 0; --once and help documented.
- Typed provider fixtures exercise all four agent stages, durable model counters, candidate validation, completed output, owned replay with zero provider construction, interrupted-stage refusal, cancellation and checkpoint reuse.

## Shared design changes

Daily starts snapshot confirmed business and brand versions and private asset identities. Strands scouts receive bounded discovery tools; their completed checkpoints retain source data for recovery. A separate worker renews leases without overwriting checkpoints. Brand analysis preserves its own snapshot and returns an unconfirmed draft. Optional short MP4 analysis feeds uncertain visual cues into the planner. Creative generation is the next spec; completed planning results currently contain candidates, selection and graph. No paid model calls were made during validation.
