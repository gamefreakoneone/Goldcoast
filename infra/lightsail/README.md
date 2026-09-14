# Lightsail deployment

Single-server, invitation-only demo. This replaces the earlier unimplemented ECS/CDK design in spec 0017. The Lightsail instance is in Oregon; the existing Cognito pool is in us-east-1. Cognito settings in configure.py are public identifiers supplied by the owner. No AWS access keys or Duck DNS token are needed on the server.

## Cost and prerequisites

The selected Linux dual-stack 2 GB / 60 GB Lightsail plan is $12/month before tax, extra traffic, snapshots and provider usage. The attached static IP is included. Cognito Essentials direct sign-in is within its free tier for the expected audience. Duck DNS is free. Check the AWS console bill rather than assuming credits apply. This is a small demo, not a high-availability service. The 2 GB capacity has not yet been live-tested.

Required: Ubuntu, Docker Engine and Compose plugin, Python 3, static IP 35.167.0.75, TCP 80/443 inbound and outbound internet. goldcoast-amogh.duckdns.org must resolve to that address; leave its AAAA record unset for this IPv4 deployment. Restrict administrative SSH appropriately while retaining Lightsail browser SSH. Only Caddy publishes ports. PostgreSQL/API/worker remain on the internal Docker network.

## Prepare and transfer

On the development computer, from the repository root:

```powershell
python infra/lightsail/bundle.py
```

This produces output/deploy/goldcoast-lightsail.tar.gz from tracked application files and the deployment files, without secrets, local recordings or accounts. Transfer the archive with scp using the Lightsail default Oregon SSH key downloaded privately from the instance Connect tab. Substitute the actual key path:

```powershell
scp -i "C:\path\LightsailDefaultKey-us-west-2.pem" output/deploy/goldcoast-lightsail.tar.gz ubuntu@35.167.0.75:~/
```

In the Lightsail browser terminal, for the FIRST installation:

```bash
tar -xzf ~/goldcoast-lightsail.tar.gz -C ~
cd ~/Goldcoast
python3 infra/lightsail/configure.py
```

Configuration is created with a random database password and Linux permissions 0600. Rerunning preserves existing values and never changes the database password. Keep this file private; do not paste it into chat. There are initially no live provider or Telegram credentials.

Before building on a 2 GB machine, inspect `swapon --show` and `free -h`. If no swap exists, create 2 GB once:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Do not run these swap creation commands over an existing swap file. Swap adds headroom; it is not proof that 2 GB handles live generation.

## Install and check

From ~/Goldcoast:

```bash
bash infra/lightsail/deploy.sh
curl --fail https://goldcoast-amogh.duckdns.org/health
```

The script builds the Python and frontend images sequentially, stops any old application services, waits for PostgreSQL, runs Alembic migrations, and starts the API, worker and HTTPS gateway. If a command fails, resolve it before continuing. Initial image builds and TLS issuance may take several minutes. Running it again updates the deployment without removing volumes. Do not run it while a campaign is active; cancel or finish the campaign first.

Caddy stores certificates in a persistent Docker volume and renews them automatically. Its API route preserves paths and streams SSE without buffering. Hash-based frontend routing needs no HTML fallback for unknown API paths. API access logs are disabled to avoid recording callback/query credentials; container logs rotate at 3 x 10 MB each.

```bash
cd ~/Goldcoast/infra/lightsail
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env logs --tail 80 api worker gateway
```

Expected: API healthy, PostgreSQL healthy, worker/gateway running. The migration service may show exited successfully. Log output must be reviewed for secrets before sharing. Browser acceptance: owner login and first-password change, sample replay, live progress, approve both formats, ZIP export, logout, and isolated judge account. Reboot the instance and confirm saved campaigns remain. Do not claim the site works until HTTPS and actual Cognito login have been verified.

## Accounts and live mode

Cognito: SPA public client with no client secret; authorization code grant; allowed scopes openid/profile; callback and sign-out URLs both https://goldcoast-amogh.duckdns.org/. Self-registration disabled. Users are created manually. Owner group is goldcoast-owner; judge group is goldcoast-demo. Adding an AWS IAM role to either group is unnecessary. Temporary passwords are changed at first managed login.

New Cognito users get fresh tenants with zero live allowance. Local Keycloak accounts, local Margin data and approvals are not migrated. Every user can try the committed historical Morrow Coffee sample without a provider key. Global live controls stay paused on a fresh database. Do not run demo_setup to grant implicit live credit in production.

After replay acceptance, edit the server-only infra/lightsail/.env using nano to set GEMINI_API_KEY, TAVILY_API_KEY, and explicit GOLDCOAST_VIDEO_MODEL, GOLDCOAST_IMAGE_MODEL, GOLDCOAST_JUDGE_MODEL matching the locally validated configuration. Optional TICKETMASTER_API_KEY may be added. Restart using deploy.sh. Manage limits and enable live mode explicitly using the server CLI below. Live campaigns and generation are not validated by replay tests.

Telegram is optional. Stop the local bot worker before configuring the same telegram_token and telegram_bot_link on the server. Recreate the API and worker with deploy.sh, then link Telegram to the new hosted account. Run exactly one hosted worker. Old local Telegram links are not automatically transferred.

## Backup, update and recovery

After initial acceptance and before updates, with no campaign active:

```bash
cd ~/Goldcoast
bash infra/lightsail/backup.sh
```

This briefly stops application services, dumps PostgreSQL, archives all assets/recordings and copies configuration to a timestamped private output/hosted-backups directory. It restarts application services on exit. Copy the backup off the instance using scp; a backup only on this server does not protect against server loss. Keep the copied config.env private. Backups are manual in this first deployment; set a calendar reminder for each day the demo changes. Monitor `df -h`, `free -h` and `sudo docker stats --no-stream`. No automated file pruning removes evidence.

For an update: retain the existing infra/lightsail/.env, take a backup, transfer/extract a new bundle, then run deploy.sh. Do not use docker compose down -v. Images currently use Python package constraints from pyproject.toml and upstream image tags rather than a complete dependency lock; test each rebuild before presenting.

Disaster recovery must use a NEW empty deployment, never an existing production volume: restore config.env as infra/lightsail/.env (chmod 600), build images, start PostgreSQL only, then restore the SQL and studio archive. From infra/lightsail, with BACKUP set to the private backup's absolute directory:

```bash
sudo docker compose --env-file .env build api
sudo docker compose --env-file .env up -d --wait postgres
sudo docker compose --env-file .env exec -T postgres psql -v ON_ERROR_STOP=1 -U goldcoast -d goldcoast < "$BACKUP/database.sql"
sudo docker compose --env-file .env run --rm --no-deps -T --entrypoint tar migrate -C /app/output/studio -xzf - < "$BACKUP/studio.tar.gz"
bash deploy.sh
```

Restore acceptance must confirm login, assets, approvals and exports before discarding the old deployment. Reuse the same Cognito pool to preserve user identities. Resume interrupted jobs only through explicit application actions; no automatic provider retries are added.

To end charges, first save required data off-server, then delete the Lightsail instance and release the static IP; remove retained chargeable snapshots/storage when no longer needed. Stopping the instance alone does not end billing. Remove the Duck DNS record after decommissioning to avoid pointing at a reassigned address.

## Server-only allowance administration

Connect to Lightsail using SSH, then run:

```bash
cd /home/ubuntu/Goldcoast/infra/lightsail
sudo docker compose exec api python -m goldcoast.studio.admin users
sudo docker compose exec api python -m goldcoast.studio.admin status
sudo docker compose exec api python -m goldcoast.studio.admin set-user ACCOUNT_ID --campaigns 5 --brand-analyses 5 --feed-refreshes 5
```

Replace ACCOUNT_ID with the ID shown by users or the account Settings page. A user appears after signing in. To prepare a newly created Cognito identity beforehand, run `sudo docker compose exec api python -m goldcoast.studio.admin register COGNITO_SUB --name aws-judge@example.com`. This does not create a Cognito login or grant an owner role. These are exact remaining balances, not additions; omitted options remain unchanged. Owner and judge accounts follow the same rules. This does not change Cognito roles. No website account can change allowances.

A separate shared budget caps all accounts combined. Inspect status before replacing it, preserving capacity intended for other users:

```bash
sudo docker compose exec api python -m goldcoast.studio.admin set-shared --campaigns 5 --brand-analyses 5 --feed-refreshes 5
sudo docker compose exec api python -m goldcoast.studio.admin live on
sudo docker compose exec api python -m goldcoast.studio.admin live off
```

Only turn live on when provider configuration is ready. Credits are workflow allowances, not purchased provider credits or a dollar cap. Replay does not consume them. Account provisioning and password changes remain in Cognito/CloudShell, not this CLI.

The configured judge login is `aws-judge@example.com`, with account ID `45e4f1d8708556e48b83095e8e9d5ce4`. Its permanent password was chosen privately in CloudShell. It has ordinary business access, no owner membership, and an initial remaining allocation of 5 campaigns, 5 brand analyses and 5 feed refreshes. The dummy email cannot receive recovery messages. The shared limits are also 5/5/5; live mode remains paused until explicitly enabled.
