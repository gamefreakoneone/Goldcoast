# Status: 0017 hosted deployment

Blocked - deferred by user

## Evidence

The user requested: "I want to see a local deployment and test it out before we go ahead with hosting it."

AWS discovery found no configured profiles, credentials or region. No AWS resources were created, no cloud credentials were requested in chat, and no hosted URL exists. Requirements/design are a deployment draft only; infrastructure implementation and provisioning are deferred until local acceptance testing and an explicit hosting go-ahead. The completed application is available locally through the studio API on 8001, Vite on 5173, PostgreSQL on 5433, Keycloak on 8080, and the separate worker. Global live generation remains paused; both local accounts have zero grants. Sample replay works through the demo account without provider calls.

## Local acceptance handoff

- `python -m pytest -q`: 130 passed, one upstream Starlette deprecation warning, 118.21 seconds.
- Frontend regression suite: 16 passed; production build, TypeScript, ESLint and Ruff passed (0016 evidence).
- Git-blob verification: all 23 replay manifest hashes match committed file bytes. `.gitattributes` disables line-ending conversion for hashed replay data, preserving clean Windows/Linux checkouts.
- HTTP checks: localhost:5173 frontend, localhost:8001/health API and localhost:8080/realms/goldcoast identity discovery all returned 200.
- Opened http://localhost:5173 in the user's visible Chrome window. Refreshed the API process to load final committed code. Local demo login uses username demo and GOLDCOAST_LOCAL_DEMO_PASSWORD from .env. Both local accounts have zero paid grants; global live generation and the demo schedule are disabled. Worker remains available for free replay.
