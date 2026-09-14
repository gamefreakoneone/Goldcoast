# Requirements: hosted deployment

Provide an inexpensive, beginner-operated, always-on Lightsail demo. The user selected a $12/month Ubuntu 2 GB instance in us-west-2, attached 35.167.0.75, configured goldcoast-amogh.duckdns.org, and created invitation-only Cognito in us-east-1. This supersedes the deferred ECS/CDK architecture; do not provision additional services.

Run frontend, studio API, exactly one worker and PostgreSQL on the same host. Serve HTTPS and SSE, persist private assets/recordings/database across restarts, and document backup/restore. Do not deploy legacy unauthenticated API or development Keycloak. Fresh accounts have zero grants and global live stays paused. Replay works without provider credentials. Exclude secrets, local output/accounts and unrelated files from build/transfer. No AWS credentials are needed by containers. Budget excludes tax, backups and providers. Test 2 GB capacity rather than promising suitability. No local-data migration in this first deployment.

Do not claim a working public site until actual HTTPS, Cognito login, replay, approval/export and restart persistence pass. Record exact validation commands/results and remaining live checks.

Usage administration must be server-only for every role. Remove credit-changing HTTP routes and owner controls. Provide exact per-account remaining limits, shared limits and a live switch through a CLI. Judge allocation is 5 campaigns, 5 brand analyses and 5 feed refreshes; identity must not receive owner membership.
