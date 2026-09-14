import argparse
import json

from sqlalchemy import select

from goldcoast.studio.config import StudioSettings
from goldcoast.studio.database import Controls, Tenant, session_factory
from goldcoast.studio.repository import Repository

FIELDS = {
    "campaigns": "campaign_grants",
    "brand_analyses": "brand_grants",
    "feed_refreshes": "feed_grants",
}


def allowance(row):
    return {name: getattr(row, field) for name, field in FIELDS.items()}


def set_allowance(sessions, account_id, values):
    if not values or any(k not in FIELDS or type(v) is not int or v < 0 for k, v in values.items()):
        raise ValueError("Supply nonnegative integer allowances")
    with sessions.begin() as session:
        model = Controls if account_id is None else Tenant
        row = session.scalar(
            select(model)
            .where(model.id == (1 if account_id is None else account_id))
            .with_for_update()
        )
        if row is None:
            raise ValueError("Account not found; sign in once, then run users")
        before = allowance(row)
        for name, value in values.items():
            setattr(row, FIELDS[name], value)
        return {"account": account_id or "shared", "before": before, "after": allowance(row)}


def nonnegative(value):
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("Must be nonnegative")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Server-only usage administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("users")
    commands.add_parser("status")
    register = commands.add_parser(
        "register", help="Prepare an account using its verified Cognito sub"
    )
    register.add_argument("subject")
    register.add_argument("--name", required=True)
    for command in ("set-user", "set-shared"):
        sub = commands.add_parser(
            command, help="Set remaining credits; omitted values stay unchanged"
        )
        if command == "set-user":
            sub.add_argument("account_id")
        for name in FIELDS:
            sub.add_argument("--" + name.replace("_", "-"), type=nonnegative)
    live = commands.add_parser("live")
    live.add_argument("state", choices=("on", "off"))
    args = parser.parse_args(argv)
    settings = StudioSettings.from_env()
    engine, sessions = session_factory(settings.database_url)
    try:
        if args.command.startswith("set-"):
            values = {
                name: getattr(args, name) for name in FIELDS if getattr(args, name) is not None
            }
            result = set_allowance(sessions, getattr(args, "account_id", None), values)
        elif args.command == "register":
            row = Repository(sessions).ensure_tenant(
                args.subject, settings.issuer, args.name, "business"
            )
            result = {"id": row.id, "subject": row.subject, **allowance(row)}
        elif args.command == "users":
            with sessions() as session:
                result = [
                    {
                        "id": row.id,
                        "name": row.name,
                        "subject": row.subject,
                        "role": row.role,
                        **allowance(row),
                    }
                    for row in session.scalars(select(Tenant).order_by(Tenant.name))
                ]
        else:
            with sessions.begin() as session:
                row = session.scalar(select(Controls).where(Controls.id == 1).with_for_update())
                if args.command == "live":
                    row.live_enabled = args.state == "on"
                result = {"live_enabled": row.live_enabled, **allowance(row)}
        print(json.dumps(result, indent=2))
    except ValueError as exc:
        parser.error(str(exc))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
