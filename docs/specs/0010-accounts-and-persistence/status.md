# Status: 0010 accounts and persistence

## Status

Completed

## Evidence

- `python -m pytest tests/test_studio_foundation.py -q -p no:cacheprovider --basetemp output/pytest-0010-final`: 8 passed, 1 existing Starlette/AnyIO deprecation warning, 39.47s.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 150 files already formatted.
- `docker compose up -d postgres keycloak`: both containers started. `docker compose ps`: PostgreSQL healthy, Keycloak Up.
- `python -m alembic upgrade head`: exit 0. `python -m alembic current`: 0010 (head).
- `python scripts/check_studio_postgres.py`: 8 concurrent requests, exactly 3 reservations; rejected transactions preserved tenant grants. Repeated idempotency keys returned one job without additional usage.
- Signed RSA tokens exercise issuer/audience/expiry/token type and owner role boundaries. Repository tests exercise cross-tenant resources, events, cancellation, durable limits, worker leases, and storage paths.

## Shared design changes

Added the separate authenticated studio API, tenant-scoped PostgreSQL resource store, OIDC verification, atomic live allowances, durable provider counters, jobs with worker leases, and resumable events. Legacy API remains a separate development entry point. No live model calls were made. Local credentials exist only in ignored .env.
