# Requirements: accounts and persistence

Add the tenant-isolated foundation for the hosted marketing studio. Keep the legacy CLI usable; the new studio API must not expose legacy unauthenticated routes.

- PostgreSQL persistence through SQLAlchemy and Alembic for tenants, generic typed resources, workflow jobs, events, and usage reservations.
- OIDC authentication supports Keycloak locally and Cognito in deployment. Validate token signature, issuer, expiry, and audience/client ID; only configured role claims grant owner privileges.
- Backend tenant identity comes only from authentication. Every resource, asset, job, event, and usage query is tenant scoped.
- Live jobs require account and global allowance, active live enablement, and an atomic reservation. Default global campaign and brand-analysis allowances are three each; accounts start with zero until owner grants access. One active paid job per tenant.
- Jobs have idempotency keys, leases, checkpoints, and terminal states. Store events durably with monotonic per-job cursors. Replay jobs are separate and consume no provider allowance.
- Persist per-job provider counts and enforce budget/cancellation before each paid call. Restarting a worker must not reset counts.
- Private storage uses a local filesystem adapter initially, with an interface for S3. Confine asset IDs and do not expose raw paths.
- Ship Docker Compose PostgreSQL and Keycloak development services, migrations, and regression tests. No fake authentication in the running app.
