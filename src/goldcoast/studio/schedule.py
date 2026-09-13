from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from pydantic import Field
from sqlalchemy import select

from goldcoast.studio.brand import StrictModel, resource_view
from goldcoast.studio.database import Job, Resource, Tenant
from goldcoast.studio.repository import Conflict
from goldcoast.studio.workflow import WorkflowStart, start_campaign


class ScheduleInput(StrictModel):
    enabled: bool = False
    hour: int = Field(default=9, ge=0, le=23)
    goal: str = Field(default="Bring more neighbors in today", min_length=1, max_length=1500)


class ScheduleSave(StrictModel):
    version: int = Field(ge=0)
    schedule: ScheduleInput


class ScheduleState(ScheduleInput):
    last_local_date: str | None = None
    last_job_id: str | None = None
    last_error: str | None = None


class ScheduleService:
    def __init__(self, repo, assets):
        self.repo, self.assets = repo, assets

    def current(self, tenant):
        return next(iter(self.repo.list(tenant, "schedule")), None)

    def save(self, tenant, body):
        with self.repo.sessions.begin() as session:
            query = select(Resource).where(
                Resource.tenant_id == tenant, Resource.kind == "schedule"
            )
            row = session.scalar(query.with_for_update())
            if row is None:
                session.execute(
                    select(Tenant).where(Tenant.id == tenant).with_for_update()
                ).scalar_one()
                row = session.scalar(query.with_for_update())
            if (row.version if row else 0) != body.version:
                raise Conflict("Schedule changed; reload before saving")
            state = ScheduleState.model_validate(row.data if row else {})
            state = state.model_copy(update=body.schedule.model_dump())
            if row:
                row.data, row.version = state.model_dump(mode="json"), row.version + 1
            else:
                row = Resource(
                    tenant_id=tenant, kind="schedule", data=state.model_dump(mode="json")
                )
                session.add(row)
            session.flush()
            return resource_view(row)

    def tick(self, now=None):
        now = now or datetime.now(UTC)
        with self.repo.sessions() as session:
            ids = list(session.scalars(select(Resource.id).where(Resource.kind == "schedule")))
        started = []
        for identity in ids:
            with self.repo.sessions.begin() as session:
                row = session.scalar(
                    select(Resource)
                    .where(Resource.id == identity)
                    .with_for_update(skip_locked=True)
                )
                if row is None:
                    continue
                state = ScheduleState.model_validate(row.data)
                if not state.enabled:
                    continue
                profile = next(iter(self.repo.list(row.tenant_id, "business")), None)
                if profile is None:
                    error = "Confirm your business and brand kit before scheduling."
                else:
                    local = now.astimezone(ZoneInfo(profile.data["timezone"]))
                    date = str(local.date())
                    if local.hour < state.hour or state.last_local_date == date:
                        continue
                    key = "scheduled:" + date
                    previous = session.scalar(
                        select(Job).where(Job.tenant_id == row.tenant_id, Job.request_key == key)
                    )
                    try:
                        job = previous or start_campaign(
                            self.repo,
                            self.assets,
                            row.tenant_id,
                            WorkflowStart(mode="live", goal=state.goal),
                            key,
                        )
                        state.last_local_date, state.last_job_id, state.last_error = (
                            date,
                            job.id,
                            None,
                        )
                        row.data = state.model_dump(mode="json")
                        row.version += 1
                        started.append(job.id)
                        continue
                    except (Conflict, ValueError):
                        error = (
                            "Not started: confirm business/brand, "
                            "enable live usage, and check allowance."
                        )
                if state.last_error != error:
                    state.last_error = error
                    row.data, row.version = state.model_dump(mode="json"), row.version + 1
        return started
