# Tasks: accounts and persistence

- [x] Read the approved plan and inspect existing API/storage boundaries.
- [x] Add dependencies, studio configuration, database models, and initial migration.
- [x] Implement tenant repository, quota reservation, jobs, durable events, and private storage.
- [x] Implement OIDC validation and authenticated studio API.
- [x] Add local PostgreSQL/Keycloak Compose services and setup documentation.
- [x] Validate JWT/tenant boundaries, idempotency, quotas, job recovery, and PostgreSQL migration/concurrency.
- [x] Record evidence, update shared design and ledger, and commit spec 0010.

## Validation Steps

```powershell
python -m pytest tests/test_studio_foundation.py -q -p no:cacheprovider --basetemp output/pytest-0010
python -m ruff check .
python -m ruff format --check .
docker compose up -d postgres keycloak
python -m alembic upgrade head
python scripts/check_studio_postgres.py
```

Expected: authentication/isolation and quota tests pass; migration applies to PostgreSQL; concurrent reservations do not exceed grants; Compose services become healthy. Record exact command outputs and any environmental limits.
