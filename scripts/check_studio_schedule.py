from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.config import StudioSettings
from goldcoast.studio.database import Base, Controls
from goldcoast.studio.replay import load_package
from goldcoast.studio.repository import Repository
from goldcoast.studio.schedule import ScheduleInput, ScheduleSave, ScheduleService


def main():
    settings = StudioSettings.from_env()
    schema = "schedule_probe_" + uuid4().hex
    control = create_engine(settings.database_url)
    with control.begin() as connection:
        connection.execute(text("CREATE SCHEMA " + schema))
    engine = create_engine(
        settings.database_url, connect_args={"options": "-csearch_path=" + schema}
    )
    try:
        Base.metadata.create_all(engine)
        sessions = sessionmaker(engine, expire_on_commit=False)
        with sessions.begin() as session:
            session.add(Controls(id=1, live_enabled=True))
        repo = Repository(sessions)
        tenant = repo.ensure_tenant("probe", "probe", "Probe", "business")
        repo.grant(tenant.id, 3, 0)
        snapshot = load_package().snapshot
        repo.put(tenant.id, "business", snapshot.profile.model_dump(mode="json"))
        repo.put(tenant.id, "brand", snapshot.brand.model_dump(mode="json"))
        service = ScheduleService(repo, LocalAssetStore(settings.asset_root))
        service.save(
            tenant.id, ScheduleSave(version=0, schedule=ScheduleInput(enabled=True, hour=0))
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: service.tick(datetime.now(UTC)), range(8)))
        jobs = repo.jobs(tenant.id)
        assert len(jobs) == 1 and repo.tenant(tenant.id).campaign_grants == 2
        assert sum(len(value) for value in results) == 1
        print("PostgreSQL: 8 simultaneous scheduler ticks created 1 job and consumed 1 grant.")
    finally:
        engine.dispose()
        assert schema.startswith("schedule_probe_") and len(schema) == 47
        with control.begin() as connection:
            connection.execute(text("DROP SCHEMA " + schema + " CASCADE"))
        control.dispose()


if __name__ == "__main__":
    main()
