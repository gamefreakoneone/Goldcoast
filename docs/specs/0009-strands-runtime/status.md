# Status: 0009 Strands runtime

## Status

Completed

## Evidence

Installed strands-agents 1.55.1 with its Gemini extra in the goldcoast Conda environment (Python 3.12.14, google-genai 2.23.0). Added the pinned SDK dependency to pyproject.toml. uv 0.12.13 is installed for isolated developer MCP tooling.

Commands used C:/Users/amogh/anaconda3/envs/goldcoast/python.exe:

```text
python -m pytest tests/test_strands_runtime.py -q -p no:cacheprovider --basetemp output/pytest-strands
8 passed in 45.15s

python -m pytest -q -p no:cacheprovider --basetemp output/pytest-0009-regression
95 passed, 1 warning in 236.13s

python -m ruff check .
All checks passed!

python -m ruff format --check .
134 files already formatted

python -m goldcoast --help
Exit 0; existing validate-seed, detect, clips, match, generate, judge, judge-loop, run, runs commands remain available.
```

The warning is an existing Starlette TestClient/AnyIO deprecation. An initial full-suite attempt used the old output/pytest-tmp directory and failed in pytest fixture cleanup because that directory belongs to another execution identity. A fresh output/pytest-0009-regression directory resolved the environment issue; no legacy source changes were needed.

Tests invoke a real Strands Agent with a deterministic Model and registered addition tool, then validate a typed answer. Coverage includes provider and structured-output call accounting, atomic shared budgets, tool dispatch rejection, cancellation, malformed output, failure recording, matching replay, mismatched/missing/failed replay, and no-network execution. All tests run under the repository network-denial fixture.

## Shared design changes

TECHNICAL_DESIGN.md documents the additive runtime, provider-boundary recording, bounded execution, native structured output, and request-validated replay. Legacy contracts and recorded runs remain unchanged. README documents installation and runtime usage.

## Developer tooling

.mcp.json includes the official Strands documentation server 0.2.7, isolated with mcp<2 as required by the published package. scripts/check_strands_mcp.py verifies initialization, tool listing, and a documentation search. MCP tools require a client reload to appear in an existing editor session. The application keeps the newer MCP version required by Strands.
