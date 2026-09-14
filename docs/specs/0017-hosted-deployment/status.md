# Status: 0017 hosted deployment

In progress - Lightsail deployment resumed by user on 2026-09-14.

The user created the $12/month server, static IP, DNS, Docker installation, Cognito client and owner account/group through guided console setup. This supersedes the prior hosting deferral. Deployment package is installed and the public HTTPS website returns 200. Owner login and end-to-end browser acceptance remain pending; do not treat this as completed hosted acceptance.

Technical design change: replace unimplemented ECS/CDK/S3/EFS/RDS with single-host Compose, existing LocalAssetStore persistent volume and Caddy HTTPS. Public API/model contracts unchanged. Cognito is us-east-1; compute us-west-2. No paid infrastructure was created by the assistant.

## Current evidence

2026-09-14 local validation (Python executable C:/Users/amogh/anaconda3/envs/goldcoast/python.exe):

- `python -m pytest tests/test_studio_hosting.py tests/test_studio_foundation.py tests/test_studio_replay.py -q`: 12 passed, 1 upstream Starlette warning, 48.33 seconds.
- `python -m ruff check infra/lightsail tests/test_studio_hosting.py`: All checks passed.
- `python -m ruff format --check infra/lightsail tests/test_studio_hosting.py`: 5 files already formatted (including subsequently added smoke.py).
- `C:/Program Files/Git/bin/bash.exe -n infra/lightsail/deploy.sh` and `... -n infra/lightsail/backup.sh`: exit 0, no syntax errors.
- `docker compose -f infra/lightsail/compose.yaml config --quiet`, with public Cognito/domain variables and a throwaway validation-only DB password: successful, proceeded to image build without configuration errors.
- `python infra/lightsail/bundle.py`: packaged 177 files to output/deploy/goldcoast-lightsail.tar.gz. Local secrets/output/Git metadata excluded; synthetic bundle exclusion and exact replay-byte tests passed.
- Initial `docker build -f infra/lightsail/Dockerfile --target app -t goldcoast-studio:lightsail .`: failed fetching Debian packages over HTTP (connection failures, apt exit 100). Switched package sources to HTTPS and added three package-download retries; retry passed (application image sha256:e22ad555c83ade3a8ab2db2071885bc313bc0c55285758c8bf9a5e06ef232872).
- `docker build -f infra/lightsail/Dockerfile --target gateway -t goldcoast-web:lightsail .`: passed; Vite built 56 modules, gateway image sha256:27294d72dd711c4e277f6811f9a64a5ebe571f2ec123adee88b35b0dfdbf9eaa. Initial gateway attempt was stopped after detecting unnecessary local node_modules context; added explicit dependency/cache exclusions and rebuilt with 2.99 MB frontend context.
- `docker run --rm -e GOLDCOAST_DOMAIN=goldcoast-amogh.duckdns.org goldcoast-web:lightsail caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`: Valid configuration; cosmetic formatting warning only.
- With user-provided key path, SSH reached 35.167.0.75. Windows initially rejected inherited broad key permissions. Restricted the original key ACL to its owner amogh, then SSH succeeded. No key material was displayed or copied into repo.
- Remote checks: x86_64, 1.9 GiB RAM, Docker Compose v5.5.1, no existing ~/Goldcoast. Created 2 GiB swap. Initial PowerShell/SSH multiline transfer mangled a carriage-return removal command; swap activation succeeded but persistence did not. Corrected via encoded nonsecret script and verified swap, then added /etc/fstab entry.
- Transferred output/deploy/goldcoast-lightsail.tar.gz via scp, extracted into new ~/Goldcoast, generated private configuration and started deploy.sh. Server build in progress. No provider keys or Telegram token configured; no live calls made.
- `docker run --rm --network none --shm-size 256m goldcoast-studio:lightsail python infra/lightsail/smoke.py`: exit 0; PASS: nonroot, no bundled secrets, offline replay, two approvals/export, Chromium PNG. Networking disabled throughout; temporary SQLite database only, no real user data.
- `git -c safe.directory=C:/Users/amogh/Desktop/Goldcoast diff --check`: passed (Windows line-ending notices only).
- Remote `bash infra/lightsail/deploy.sh`: exit 0. Both images built on Lightsail, Alembic migration completed, API and PostgreSQL healthy, worker/gateway running. Only gateway ports 80/443 published.
- `curl.exe --fail --max-time 25 -sS https://goldcoast-amogh.duckdns.org/health`: status ok, application goldcoast-studio.
- `curl.exe --fail --max-time 25 -sS https://goldcoast-amogh.duckdns.org/api/v2/auth/config`: correct user-supplied Cognito issuer/client/domain and invitation-only registration.
- `curl.exe --max-time 25 -sS -o NUL -w 'Website HTTP status: %{http_code}' https://goldcoast-amogh.duckdns.org/`: Website HTTP status: 200. TLS validated normally, no insecure flag.
- On Lightsail: `sudo docker run --rm --network none --memory 768m --memory-swap 1g --shm-size 256m goldcoast-studio:lightsail python infra/lightsail/smoke.py`: PASS: nonroot, no bundled secrets, offline replay, two approvals/export, Chromium PNG.
- Remote `sudo docker stats --no-stream`: gateway 14.89 MiB, worker 95.19 MiB, API 108.9 MiB, PostgreSQL 28.55 MiB at idle. `free -h`: 802 MiB used, 1.1 GiB available, 3.3 MiB of 2 GiB swap used. This is not a live-generation peak measurement.
- Remote `stat -c %a ~/Goldcoast/infra/lightsail/.env`: 600. No model credentials or Telegram token installed. No paid provider calls.

Remaining: owner first-login/password change, judge account/isolation in browser, real hosted replay/SSE/approval/export, restart persistence with saved data, backup/restore rehearsal and bounded live-generation acceptance. Changes are uncommitted pending remaining acceptance; unrelated pre-existing .claude directory was left untouched.

Historical evidence below is retained and is not hosted acceptance.

## Historical record

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

## Server-only usage administration, 2026-09-14

Removed Settings owner controls and both POST /api/v2/admin endpoints. New `python -m goldcoast.studio.admin` CLI supports users, status, register, set-user, set-shared, and live on/off. Row-locked exact balance changes preserve omitted fields and do not enable live mode. Existing repository enforcement applies to owner and ordinary accounts alike.

Validation: `python -m pytest tests/test_studio_foundation.py tests/test_studio_hosting.py tests/test_studio_replay.py -q`: 14 passed. Signed owner/business/demo requests and unauthenticated calls to former admin routes return 404; balances unchanged. Exact set idempotence, invalid/unknown account rejection and preserved shared/other-account balances pass. `python -m ruff check src/goldcoast/studio/admin.py src/goldcoast/api/studio_app.py tests/test_studio_foundation.py` and format check pass. `pnpm --dir web build` passes. Parallel frontend suite had one unrelated legacy replay timeout; `pnpm --dir web test --run --maxWorkers=1`: 38 passed, 13 files.

Browser plugin not available; used installed Python Playwright with Chrome and mocked authentication/API on http://127.0.0.1:4173. Flow: authenticated Settings -> read-only 5/5/5 balance with no Owner controls -> Campaigns -> Your campaign shelf. Passed for owner desktop 1440x1000 and ordinary account mobile 390x1000. Correct page title, meaningful content, no framework overlay or page errors. Screenshots inspected at Windows TEMP/goldcoast-settings-owner.png and goldcoast-settings-business.png. Initial QA fixture returned empty bodies instead of JSON null; corrected fixture, no product change needed. Actual judge credentials are private and not exercised by these mocks.

User confirmed CloudShell created aws-judge@example.com with permanent password and Cognito sub 2488c438-0061-70b0-562a-00fa7c006f3a without owner membership. Password was not supplied to this agent. Hosted allocation and deployment verification pending below.

Hosted update completed using `bash infra/lightsail/deploy.sh`: configuration preserved, app and gateway rebuilt, migrations succeeded, API/PostgreSQL healthy. `admin register` prepared the provided Cognito sub; `admin set-user 45e4f1d8708556e48b83095e8e9d5ce4 --campaigns 5 --brand-analyses 5 --feed-refreshes 5` verified exactly 5/5/5 and role business (no owner privilege). `admin set-shared --campaigns 5 --brand-analyses 5 --feed-refreshes 5` provides matching shared capacity; live remains false. Existing owner retains its prior zero balance. Public HTTPS /health returns ok; POST to both former admin routes returns 404. `docker run --rm --network none --memory 768m --memory-swap 1g --shm-size 256m goldcoast-studio:lightsail python infra/lightsail/smoke.py`: PASS nonroot, no bundled secrets, offline replay, two approvals/export, Chromium PNG. Frontend lint passes. Actual judge login, bounded live generation and backup restoration still require their separate acceptance checks; this update did not consume provider credits.

## Campaign-video upload validation, 2026-09-14

The reported disabled upload showed a filled video name but only placeholder text for description. Incomplete videos misleadingly displayed Ready. Staged uploads now expose required details through associated inline messages, label incomplete videos Needs video details, and focus the first empty/whitespace-only video field on submit. Upload metadata and permission requirements remain enforced; completed files remain skipped on retries.

`pnpm --dir web test --run src/test/assetLibrary.test.tsx src/test/marketing.test.tsx --maxWorkers=1`: 9 passed. Regression checks cover missing name, missing description, whitespace-only description, focus behavior, no premature request, successful multipart metadata and retry behavior. `pnpm --dir web build` and `pnpm --dir web lint`: passed.

Browser plugin not available; installed Python Playwright/Chrome tested the built site at http://127.0.0.1:4173 with mock authentication/API and an FFmpeg-generated one-second MP4. At 1440x1000 and 390x1000: select file -> fill name/confirm permission -> submit -> description receives focus/no request -> fill description -> submit -> exactly one multipart request containing both fields -> Uploaded. No page or console errors. Screenshot evidence in Windows TEMP/goldcoast-upload-missing-390.png and goldcoast-upload-success-1440.png. This verifies the browser workflow with a mock upload endpoint, not a real signed-in hosted upload.

Published with `docker compose build gateway` and `docker compose up -d --no-deps gateway`; backend/worker were not restarted. Public HTTPS health returned ok. Deployed frontend bundle MarketingApp-BZqNuxmd.js matches the locally tested build.

## Video subject/frame correction, 2026-09-14

Confirmed local run 30923a6683f14b65b2a25ce83a36c015 requested Ganesh Chaturthi boba for Indian customers near USC, selected video 212eb1b0534b430ca6e41c2ecf3fb6f6, and used creative_type product with no product_id. product_campaign silently selected Iced matcha. The video frame was only an optional generator reference. Fixed by restricting the typed campaign-local snapshot to the selected video subject, directly composing photo posts from original frame bytes, retaining the entire portrait frame, and excluding unrelated catalog/style images from that photo path. Generic ambiguous Product requests now reject before reserving credit. Updated TECHNICAL_DESIGN.md deliberately to document the owner-labeled video subject exception without mutating saved catalog data.

Regression coverage: linked and unlinked Product/Auto videos; owner metadata; unchanged saved catalog; zero image-generation calls; exact full-frame pixels; regeneration of new campaigns and old wrong-product campaigns using cached evidence; replay and social judge/approval/export. Campaign-video/social/workflow/creative/replay suite: 29 passed. Final request-validation addition: social suite 5 passed, verifies no allowance consumed. Ruff check and format: all six changed Python files pass.

Automatic approval initially rejected live correction (credit mutation/model egress). User explicitly approved one refunded credit and one corrective Gemini run, without Telegram notification. Corrective job 3a707e1c80944258a8f9e9f070927cd2 selected Limited Edition Ganesh Chaturiti Boba Drink and generated caption targeting Indian students near USC. Usage: 3 model calls, 1 search, zero image calls and zero video analyses; cached frame e81ef02e1e274179841113465c47ec50 reused. Judge returned no passing creatives: Teavaro source branding conflicts with Margin; original layout crop hid boba. Fixed cropping after this run and rendered a provider-free full-frame preview at output/video-repair-preview.png. That preview is not newly judged/approved. User confirmed the borrowed clip is a demo stand-in and Margin remains the business. No second live run, additional grant or Telegram notification was made; business profile and judge safeguards retained.

Local API/worker restarted and health returned ok. Final hosted deployment verification follows below.

Final request-validation regression: workflow/campaign-video suites 18 passed; social suite 5 passed. All six changed Python files pass Ruff check/format. Final local API PID 71084 and worker PID 27092 loaded the fix; /health returned ok. Hosted final image built successfully; idle-job guard passed before API/worker recreation.
`docker compose up -d --no-deps --wait api worker`: both services started and API healthy. Public HTTPS /health returned ok. Network-disabled Linux smoke passed nonroot/no bundled secrets/offline replay/two approvals and export/Chromium PNG.
