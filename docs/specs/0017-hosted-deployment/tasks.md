# Tasks: hosted deployment

- [x] Read requirements/design and official AWS/CDK documentation.
- [ ] Implement hosted storage/config/readiness and production container.
- [ ] Implement CDK infrastructure with private data/origins and Cognito.
- [ ] Add deployment/invitation/migration helpers and cost/teardown runbook.
- [ ] Validate storage/auth configuration tests, CDK synthesis assertions, Docker build and provider-free container replay.
- [ ] Review exact target account and costs; deploy when credentials/authorization available.
- [ ] Verify live HTTPS login/replay/export, record evidence and commit.

## Validation Steps

`python -m pytest tests/test_studio_hosting.py -q`

`python -m pytest infra/aws/tests -q`

`python infra/aws/app.py` (synthesis only; never creates resources)

`docker build -f infra/aws/Dockerfile -t goldcoast-studio:local .`

Run container health/packaged replay checks with no provider keys and inspect that .env/local output are absent. Run Python/frontend lint/build checks appropriate to changes. For live deployment, authenticate selected profile, inspect boto3 STS identity and cost preview, bootstrap/deploy CDK, upload only required secrets, migrate, start services, create password-protected reviewer account without sending email, then use Chrome HTTPS login/sample replay/approval/export. Record exact commands/outcomes. If blocked by missing AWS credentials, record the observed blocker and complete unaffected submission work.
