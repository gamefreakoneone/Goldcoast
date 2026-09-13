from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from goldcoast.studio.config import StudioSettings
from goldcoast.studio.database import Base, Controls
from goldcoast.studio.repository import Conflict, Repository


def main():
    settings = StudioSettings.from_env()
    url = make_url(settings.database_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("This probe requires PostgreSQL")
    schema = "probe_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        sessions = sessionmaker(engine, expire_on_commit=False)
        with sessions.begin() as session:
            session.add(Controls(id=1, live_enabled=True, campaign_grants=3, brand_grants=3))
        repo = Repository(sessions)
        tenants = [
            repo.ensure_tenant(str(i), "integration-test", f"Probe {i}", "business")
            for i in range(8)
        ]
        for tenant in tenants:
            repo.grant(tenant.id, 1, 0)

        def attempt(tenant):
            try:
                row = repo.create_job(tenant.id, "campaign", "live", "race", {})
                return row.id
            except Conflict:
                return None

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, tenants))
        assert sum(result is not None for result in results) == 3
        assert repo.controls().campaign_grants == 0
        assert sum(repo.tenant(t.id).campaign_grants for t in tenants) == 5
        print(
            "PostgreSQL: 8 concurrent requests, exactly 3 reservations; "
            "rejected transactions preserved tenant grants."
        )
        chosen = next(t for t, result in zip(tenants, results, strict=True) if result)
        with ThreadPoolExecutor(max_workers=4) as pool:
            repeated = list(
                pool.map(
                    lambda _: repo.create_job(chosen.id, "campaign", "live", "race", {}).id,
                    range(8),
                )
            )
        assert len(set(repeated)) == 1
        print("PostgreSQL: repeated idempotency keys return one job without additional usage.")
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


if __name__ == "__main__":
    main()
