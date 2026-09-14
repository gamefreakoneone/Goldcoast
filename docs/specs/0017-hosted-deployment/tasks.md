# Tasks: hosted deployment

- [x] Re-plan for the selected Lightsail instance and Cognito pool.
- [x] Add nonroot app image, frontend/gateway image, persistent private Compose services and migrations.
- [x] Add private idempotent config, transfer bundle, deploy script and backup/restore runbook.
- [x] Validate config/bundle tests, Compose parsing, shell syntax and existing auth/replay checks.
- [x] Validate Docker builds, Chromium and provider-free replay in Linux containers.
- [x] Transfer/start on existing server; verify public HTTPS, health, login configuration and offline Linux smoke test.
- [ ] Verify actual Cognito login, judge isolation, hosted SSE, approvals/export in browser.
- [ ] Verify restart persistence, restoration and memory; separately test bounded live generation.
- [ ] Record final evidence and commit spec 0017 separately.

## Validation Steps

From repository root:

```text
python -m pytest tests/test_studio_hosting.py tests/test_studio_foundation.py tests/test_studio_replay.py -q
python -m ruff check infra/lightsail tests/test_studio_hosting.py
python -m ruff format --check infra/lightsail tests/test_studio_hosting.py
python infra/lightsail/bundle.py
bash -n infra/lightsail/deploy.sh
bash -n infra/lightsail/backup.sh
```

With throwaway nonsecret env variables run docker compose -f infra/lightsail/compose.yaml config --quiet. Build app/gateway Dockerfile targets. On server run deploy.sh and the runbook acceptance checks. Record actual commands/results; Windows tests do not substitute for Linux or public acceptance.

- [x] Validate server-only allowance CLI, removal of HTTP administration and settings controls.
- [x] Deploy administration update and provision separate judge identity with 5/5/5 allowances.
