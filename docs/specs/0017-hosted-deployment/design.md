# Design: hosted deployment

Compose project goldcoast-hosted runs on the existing Lightsail host. Caddy serves built React and proxies /api/v2 and /health to the studio API, preserving SSE with immediate flushing. Only 80/443 are published. Hash routing needs no HTML fallback for API errors. Cognito issuer/client remain explicitly configured in us-east-1.

Nonroot Python 3.12 image contains FFmpeg, Playwright Chromium and committed replay. API/worker/migrations share that image. Separate Node build produces the Caddy frontend image. Builds run sequentially for limited memory. Dependencies retain project constraints/upstream tags, not complete locks; every rebuild requires validation.

Named volumes preserve PostgreSQL, shared studio assets/recordings and Caddy certificates. Existing LocalAssetStore stays unchanged; no S3/EFS/RDS adapter. App UID 10001 owns initial volume directories. Healthcheck verifies HTTP and DB. Migration precedes startup; update stops app services before migration. Operator finishes/cancels campaigns before deployment; no automatic downgrade.

configure.py exclusively creates private .env with a URL-safe random password and public identifiers; repeat invocation preserves values. API receives no Gemini/Tavily keys; worker receives optional providers. Telegram stays empty until local polling stops. Existing fresh database defaults preserve paused live/zero tenant grants.

bundle.py packages tracked application/frontend/migration/replay plus deployment files; .dockerignore allowlists build context. deploy.sh builds/migrates/starts without provisioning AWS or granting credit. backup.sh quiesces application services, saves SQL/studio files/private config, then restarts on exit. Copy backups off-server. Restore targets an empty deployment with same Cognito identity pool.

Validate config idempotence, secret exclusion, bundle bytes, Compose parsing, shell syntax, Docker build, nonroot renderer/replay, existing auth/replay tests and frontend build. Live acceptance needs user SSH/login: HTTPS, password change, roles, replay/SSE/approval/export, reboot persistence, resource usage and restoration. Manual backups/operator monitoring; no HA claim. Stopping Lightsail does not end charges.

python -m goldcoast.studio.admin manages the existing database directly using row-locked transactions. set-user and set-shared replace specified remaining balances, preserving omitted fields; neither enables live mode. Cognito remains responsible for identities. HTTP grants and controls routes are removed, including for owners. No database migration is required.

Staged uploads use a form with explicit trimmed-video-field validation and focus the first incomplete field on submit. Inline associated descriptions distinguish required input from placeholder examples. Upload remains gated on saved business, permission and complete metadata.
