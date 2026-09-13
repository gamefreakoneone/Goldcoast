# Design: accounts and persistence

Introduce goldcoast/studio as the new domain layer and goldcoast.api.studio_app as a separate authenticated application. Use SQLAlchemy 2, PostgreSQL 16, Alembic, psycopg 3, PyJWT crypto, and existing FastAPI. Database configuration is separate from legacy Settings so replay/login require no Gemini key.

Tables: tenants (OIDC issuer+subject unique, role, campaign and brand grants); resources (tenant, kind, ID, versioned JSON document); jobs (tenant, kind, mode, idempotency key, state, lease, checkpoint, counters); events (job+sequence unique, tenant, type, JSON payload); controls (singleton live flag and global grants). Resource documents are parsed through stage-specific Pydantic schemas when later specs add them. Database foreign keys and tenant-scoped repository functions enforce ownership.

Use conditional SQL updates and transactions for quota reservation; failure rolls back all debits. A tenant active-job flag plus global controls lock serializes live reservation. Idempotent retries return the existing job. Counts remain durable and are incremented before provider invocation. Errors retain reservations conservatively; owner grants can replenish explicitly. Lease expiration makes a job reclaimable without resetting counters. Unknown in-flight operations are not automatically reissued.

JWT validation uses configured issuer and JWKS URL, RS256 only, audience validation for Keycloak and Cognito token_use/access client_id validation for Cognito. Tokens remain in browser memory in later UI work. API endpoints expose /api/v2/auth/config, /me, tenant-scoped resources/jobs/events/usage, and owner-only grants and live controls. Health and public auth configuration reveal no secrets. Integration tests supply signed JWTs through a local key resolver rather than bypass auth.

Local assets reside under configured storage root/tenant/asset ID. Validate MIME and payload size at upload boundaries in 0011. Docker Compose runs PostgreSQL and Keycloak with development realm import; local passwords come from .env, not committed files. Docker binds local service ports to 127.0.0.1. Local development and cloud use the same repository schema and OIDC protocol.

SQLite can exercise fast repository unit tests, but a separate PostgreSQL integration probe must test migrations and competing quota reservations before completion. Existing no-network pytest policy remains for normal tests.
