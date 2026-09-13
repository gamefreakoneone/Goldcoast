import hashlib
import json
import time
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from goldcoast.studio.database import Controls, Event, Job, Resource, Tenant, identifier


class AccessError(RuntimeError):
    pass


class Conflict(RuntimeError):
    pass


LIMITS = {"model": 32, "tool": 32, "search": 8, "extract": 10, "image": 6, "video": 1}
TERMINAL = {"completed", "failed", "cancelled"}


class Repository:
    def __init__(self, sessions):
        self.sessions = sessions

    def ensure_tenant(self, subject, issuer, name, role):
        tenant_id = uuid5(NAMESPACE_URL, issuer + "\n" + subject).hex
        try:
            with self.sessions.begin() as s:
                row = s.get(Tenant, tenant_id)
                if row is None:
                    row = Tenant(id=tenant_id, subject=subject, issuer=issuer, name=name, role=role)
                    s.add(row)
                else:
                    row.name, row.role = name, role
            return row
        except IntegrityError:
            return self.tenant(tenant_id)

    def tenant(self, tenant_id):
        with self.sessions() as s:
            row = s.get(Tenant, tenant_id)
            if row is None:
                raise AccessError("Not found")
            return row

    def grant(self, tenant_id, campaign, brand):
        if campaign < 0 or brand < 0:
            raise ValueError("Grants must be nonnegative")
        with self.sessions.begin() as s:
            result = s.execute(
                update(Tenant)
                .where(Tenant.id == tenant_id)
                .values(
                    campaign_grants=Tenant.campaign_grants + campaign,
                    brand_grants=Tenant.brand_grants + brand,
                )
            )
            if not result.rowcount:
                raise AccessError("Not found")

    def controls(self, *, enabled=None, campaign=0, brand=0):
        if campaign < 0 or brand < 0:
            raise ValueError("Grants must be nonnegative")
        with self.sessions.begin() as s:
            row = s.execute(select(Controls).where(Controls.id == 1).with_for_update()).scalar_one()
            if enabled is not None:
                row.live_enabled = enabled
            row.campaign_grants += campaign
            row.brand_grants += brand
            return row

    def put(self, tenant_id, kind, data, resource_id=None, expected_version=None):
        with self.sessions.begin() as s:
            if resource_id:
                row = s.execute(
                    select(Resource)
                    .where(
                        Resource.id == resource_id,
                        Resource.tenant_id == tenant_id,
                        Resource.kind == kind,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if row is None:
                    raise AccessError("Not found")
                if expected_version is not None and row.version != expected_version:
                    raise Conflict("Resource changed; reload before saving")
                row.data, row.version, row.updated_at = data, row.version + 1, time.time()
            else:
                row = Resource(tenant_id=tenant_id, kind=kind, data=data)
                s.add(row)
            s.flush()
            return row

    def get(self, tenant_id, kind, resource_id):
        with self.sessions() as s:
            row = s.execute(
                select(Resource).where(
                    Resource.id == resource_id,
                    Resource.tenant_id == tenant_id,
                    Resource.kind == kind,
                )
            ).scalar_one_or_none()
            if row is None:
                raise AccessError("Not found")
            return row

    def list(self, tenant_id, kind):
        with self.sessions() as s:
            return list(
                s.scalars(
                    select(Resource)
                    .where(Resource.tenant_id == tenant_id, Resource.kind == kind)
                    .order_by(Resource.created_at.desc())
                    .limit(500)
                )
            )

    def create_job(self, tenant_id, kind, mode, request_key, payload):
        if kind not in {"campaign", "brand"} or mode not in {"live", "replay"}:
            raise ValueError("Invalid job kind or mode")
        if not request_key or len(request_key) > 128:
            raise ValueError("Invalid idempotency key")
        digest = hashlib.sha256(
            json.dumps([kind, mode, payload], sort_keys=True).encode()
        ).hexdigest()
        with self.sessions.begin() as s:
            tenant = s.execute(
                select(Tenant).where(Tenant.id == tenant_id).with_for_update()
            ).scalar_one()
            previous = s.execute(
                select(Job).where(Job.tenant_id == tenant_id, Job.request_key == request_key)
            ).scalar_one_or_none()
            if previous:
                if previous.request_digest != digest:
                    raise Conflict("Idempotency key was used for another request")
                return previous
            job_id = identifier()
            if mode == "live":
                controls = s.execute(
                    select(Controls).where(Controls.id == 1).with_for_update()
                ).scalar_one()
                field = f"{kind}_grants"
                if not controls.live_enabled:
                    raise Conflict("Live generation is disabled")
                if tenant.active_job:
                    raise Conflict("A live workflow is already active")
                if getattr(tenant, field) < 1 or getattr(controls, field) < 1:
                    raise Conflict("Live allowance exhausted")
                setattr(tenant, field, getattr(tenant, field) - 1)
                setattr(controls, field, getattr(controls, field) - 1)
                tenant.active_job = job_id
            row = Job(
                id=job_id,
                tenant_id=tenant_id,
                kind=kind,
                mode=mode,
                request_key=request_key,
                request_digest=digest,
                input=payload,
            )
            s.add(row)
            s.flush()
            return row

    def job(self, tenant_id, job_id):
        with self.sessions() as s:
            row = s.execute(
                select(Job).where(Job.id == job_id, Job.tenant_id == tenant_id)
            ).scalar_one_or_none()
            if row is None:
                raise AccessError("Not found")
            return row

    def jobs(self, tenant_id):
        with self.sessions() as s:
            return list(
                s.scalars(
                    select(Job)
                    .where(Job.tenant_id == tenant_id)
                    .order_by(Job.created_at.desc())
                    .limit(100)
                )
            )

    def reserve_call(self, tenant_id, job_id, kind, worker=None):
        if kind not in LIMITS:
            raise ValueError("Unknown provider allowance")
        with self.sessions.begin() as s:
            row = s.execute(
                select(Job).where(Job.id == job_id, Job.tenant_id == tenant_id).with_for_update()
            ).scalar_one_or_none()
            if row is None:
                raise AccessError("Not found")
            if (
                row.state != "running"
                or row.lease_owner != worker
                or row.lease_until <= time.time()
            ):
                raise Conflict("Worker does not hold a live lease")
            controls = s.get(Controls, 1)
            if row.mode != "live" or row.state in TERMINAL or not controls.live_enabled:
                raise Conflict("Provider call is not permitted")
            counters = dict(row.counters)
            limit = min(LIMITS[kind], 8) if row.kind == "brand" else LIMITS[kind]
            if counters.get(kind, 0) >= limit:
                raise Conflict(f"{kind} allowance exhausted")
            counters[kind] = counters.get(kind, 0) + 1
            row.counters = counters

    def claim(self, worker, lease_seconds=120):
        with self.sessions.begin() as s:
            row = s.execute(
                select(Job)
                .where(
                    or_(
                        Job.state == "queued",
                        (Job.state == "running") & (Job.lease_until < time.time()),
                    )
                )
                .order_by(Job.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            ).scalar_one_or_none()
            if row:
                row.state, row.lease_owner = "running", worker
                row.lease_until = time.time() + lease_seconds
            return row

    def checkpoint(self, tenant_id, job_id, worker, data):
        with self.sessions.begin() as s:
            result = s.execute(
                update(Job)
                .where(
                    Job.id == job_id,
                    Job.tenant_id == tenant_id,
                    Job.state == "running",
                    Job.lease_owner == worker,
                    Job.lease_until > time.time(),
                )
                .values(checkpoint=data, lease_until=time.time() + 120)
            )
            if not result.rowcount:
                raise Conflict("Worker no longer owns job")

    def finish(self, tenant_id, job_id, state, worker=None):
        if state not in TERMINAL:
            raise ValueError("Invalid terminal state")
        with self.sessions.begin() as s:
            row = s.execute(
                select(Job).where(Job.id == job_id, Job.tenant_id == tenant_id).with_for_update()
            ).scalar_one_or_none()
            if row is None:
                raise AccessError("Not found")
            if row.state in TERMINAL:
                return row
            if state != "cancelled" and (
                row.lease_owner != worker or row.lease_until <= time.time()
            ):
                raise Conflict("Worker does not hold a live lease")
            row.state, row.finished_at = state, time.time()
            s.add(
                Event(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    sequence=row.next_sequence,
                    type="run_" + state,
                    payload={},
                )
            )
            row.next_sequence += 1
            s.execute(
                update(Tenant)
                .where(Tenant.id == tenant_id, Tenant.active_job == job_id)
                .values(active_job=None)
            )
            return row

    def emit(self, tenant_id, job_id, type, payload):
        with self.sessions.begin() as s:
            sequence = s.execute(
                update(Job)
                .where(Job.id == job_id, Job.tenant_id == tenant_id)
                .values(next_sequence=Job.next_sequence + 1)
                .returning(Job.next_sequence)
            ).scalar_one_or_none()
            if sequence is None:
                raise AccessError("Not found")
            row = Event(
                job_id=job_id,
                tenant_id=tenant_id,
                sequence=sequence - 1,
                type=type,
                payload=payload,
            )
            s.add(row)
            s.flush()
            return row

    def events(self, tenant_id, job_id, after=-1):
        self.job(tenant_id, job_id)
        with self.sessions() as s:
            return list(
                s.scalars(
                    select(Event)
                    .where(
                        Event.job_id == job_id, Event.tenant_id == tenant_id, Event.sequence > after
                    )
                    .order_by(Event.sequence)
                    .limit(200)
                )
            )
