# Development and operations

Start with the [README quickstart](../README.md#run-locally). Commands below run from the repository root in the `goldcoast` environment. Hosted commands differ; use the [Lightsail runbook](../infra/lightsail/README.md).

## Local identities and storage

`python scripts/setup_studio.py` fills missing local passwords in `.env` while preserving existing values. The Keycloak realm imports `demo` and `owner` on its first start. Changing a password in `.env` later does not update an existing Keycloak user; change that user's password through Keycloak administration.

`GOLDCOAST_KEYCLOAK_ADMIN_PASSWORD` administers the local identity server. It is not a Goldcoast business login or a judge password. Hosted users authenticate with Cognito, not this development realm. The website offers no credit-granting owner controls.

PostgreSQL defaults to localhost:5433 using `GOLDCOAST_DB_PASSWORD`; `GOLDCOAST_DATABASE_URL` can override it. Private uploaded assets default to `output/studio/assets`. Keep `.env`, private artifacts, and backups out of Git. Never use local Keycloak's development configuration as a public identity service.

## Usage administration

After a user signs in once, inspect its application account ID:

```powershell
python -m goldcoast.studio.admin users
python -m goldcoast.studio.admin status
```

Use the ID from `users`, not an email address or an unregistered Cognito subject:

```powershell
python -m goldcoast.studio.admin set-user ACCOUNT_ID --campaigns 5 --brand-analyses 5 --feed-refreshes 5
python -m goldcoast.studio.admin set-shared --campaigns 5 --brand-analyses 5 --feed-refreshes 5
python -m goldcoast.studio.admin live on
```

These replace the remaining balances for the supplied fields; omitted fields stay unchanged. Account and shared credit are both required. `live off` pauses subsequent live provider work; use the UI's Stop workflow to cancel a running job. Credits are application limits, independent of provider billing.

For a hosted account that has not signed in yet, `register COGNITO_SUB --name "Judge"` prepares an ordinary business account using a verified subject from your user pool. Give judges their own login and grants; they do not need owner membership or access to server credentials.

## Optional populated local demo

For an **empty local account**, use:

```powershell
python -m goldcoast.studio.demo_setup --tenant ACCOUNT_ID
```

This adds the fictional Margin Cafe & Goods business and source-attributed assets. It also enables shared live mode and grants the initial demo allowances: 3 campaigns, 2 brand analyses and 10 feed refreshes. Run it only when you intend to enable that local test account. It is idempotent, does not replenish repeated grants, and will not overwrite an existing business. It is restricted to a local database. The built-in Morrow replay needs none of this setup.

## Optional Telegram

Create a bot through Telegram's BotFather. Store its token in `.env` as `telegram_token` and its `https://t.me/<bot>` link as `telegram_bot_link`. These names are lowercase. Restart the studio API and worker after configuration.

In **Settings > Telegram approvals > Connect Telegram**, follow the link and press Start, or send the displayed `/start <code>` message within ten minutes. The toggle pauses notifications; Disconnect revokes the link and pending prompts.

| Command | Behavior |
|---|---|
| `/start`, `/commands` | Free help |
| `/credits` | Show account/shared campaign allowance |
| `/status` | Latest campaign status and review link |
| `/campaign` | Start an automatic campaign; uses one campaign credit |
| `/campaign Promote our iced latte this afternoon` | Start with your brief; uses one campaign credit |
| `/campaign Use the video I just uploaded` | Select the latest named campaign video; ambiguous input is rejected before reserving a credit |

Passing campaign previews support approval, rejection and feedback regeneration. A regeneration uses one campaign credit and reuses the original eligible evidence. Phone-created campaigns and their revisions appear on the website, with each version's own decisions. Export retains the full-resolution files even when Telegram compresses its previews.

Run exactly **one worker/poller per bot token**. Stop the local worker before moving that token to a hosted worker. Telegram deliveries are conservative: ambiguous sends or interrupted receipts are not automatically retried, so a notification can be missed. Replay sends no messages and spends no provider credits.

## Scheduling and updates

Scheduling is disabled by default. In Settings, choose the start hour and goal, using the business timezone, then explicitly enable it. The worker checks once per minute and creates at most one campaign per local day. Scheduling uses the same profile, brand, credits and shared live checks as manual generation.

After pulling an application update:

```powershell
python -m alembic upgrade head
```

Then restart the API and worker; restart Vite if frontend configuration changed. Avoid updating while a paid workflow is active. Restarting Vite alone cannot load backend routes. Keep the PostgreSQL and private file stores together when backing up; deleting Compose volumes destroys saved data.

## Troubleshooting

| Symptom | Check |
|---|---|
| Sign-in page or API unavailable | Docker services, Keycloak startup, API on 8001, Vite on 5173; preserve `localhost` in the configured callback |
| Replay queued without progress | Run `python -m goldcoast.studio.worker` in a separate terminal |
| Live controls unavailable | Confirm business and brand, account/shared balances, global live switch, and no conflicting active job |
| Provider quota or authentication error | Server-side keys/model IDs and provider quota; local `.env` does not configure the hosted server |
| Upload remains disabled | Name and describe every queued campaign video, then confirm usage permission |
| Wrong product in a brief | Choose the intended catalog product or named campaign video; also confirm exact offers on Business |
| Stale idea or export blocked | Refresh expired evidence or start a fresh campaign after business/brand changes; inspect critical judge issues |
| Composition browser missing | Installed Chrome on Windows, or `python -m playwright install --with-deps chromium` on Linux |
| New Telegram routes return 404 | Restart both API and worker after the update |
| PowerShell blocks pnpm | Use `pnpm.cmd` |

For Windows temporary-directory issues, use `pytest -p no:cacheprovider --basetemp output/pytest-tmp` and ensure no concurrent pytest process shares that directory. Use `pnpm --dir web test --maxWorkers=1` on resource-constrained machines.

## Deeper references

- [Architecture](architecture.md)
- [Feature and acceptance ledger](FEATURE_STATUS.md)
- [Hosted installation, backup and recovery](../infra/lightsail/README.md)
- [Legacy Olympics CLI/API commands](legacy-olympics.md)
- [Working rules](../AGENTS.md)
