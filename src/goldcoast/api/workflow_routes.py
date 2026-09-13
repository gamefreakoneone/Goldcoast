from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from goldcoast.api.studio_auth import IdentityDep
from goldcoast.api.studio_views import job_view
from goldcoast.studio.brand import resource_view
from goldcoast.studio.schedule import ScheduleSave, ScheduleService
from goldcoast.studio.workflow import WorkflowStart, snapshot_business, start_campaign

router = APIRouter(prefix="/api/v2")
KeyDep = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]


@router.post("/workflows", status_code=202)
def start(body: WorkflowStart, request: Request, identity: IdentityDep, key: KeyDep):
    return job_view(
        start_campaign(
            request.app.state.repo,
            request.app.state.assets,
            identity.tenant_id,
            body,
            key,
        )
    )


@router.post("/brand/analyze", status_code=202)
def analyze(request: Request, identity: IdentityDep, key: KeyDep):
    repo, assets = request.app.state.repo, request.app.state.assets
    snapshot = snapshot_business(repo, assets, identity.tenant_id, require_brand=False)
    if not any(r["data"]["mime"].startswith("image/") for r in snapshot.assets):
        raise HTTPException(409, "Upload a visual reference first")
    return job_view(
        repo.create_job(
            identity.tenant_id,
            "brand",
            "live",
            key,
            {
                "snapshot": snapshot.model_dump(mode="json"),
            },
        )
    )


@router.get("/runs/{job_id}/result")
def result(job_id: str, request: Request, identity: IdentityDep):
    job = request.app.state.repo.job(identity.tenant_id, job_id)
    key = "brand_analysis" if job.kind == "brand" else "campaign"
    step = job.checkpoint.get(key, {})
    return step.get("output") if step.get("state") == "completed" else None


@router.get("/runs/{job_id}/graph")
def graph(job_id: str, request: Request, identity: IdentityDep):
    value = result(job_id, request, identity)
    return value.get("graph") if value else None


@router.post("/replays/sample", status_code=202)
def sample(request: Request, identity: IdentityDep, key: KeyDep):
    from goldcoast.studio.replay import start_sample

    return job_view(start_sample(request.app.state.repo, identity.tenant_id, key))


@router.get("/schedule")
def schedule(request: Request, identity: IdentityDep):
    service = ScheduleService(request.app.state.repo, request.app.state.assets)
    row = service.current(identity.tenant_id)
    return resource_view(row) if row else None


@router.put("/schedule")
def save_schedule(body: ScheduleSave, request: Request, identity: IdentityDep):
    service = ScheduleService(request.app.state.repo, request.app.state.assets)
    return service.save(identity.tenant_id, body)
