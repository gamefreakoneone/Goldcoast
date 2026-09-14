from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request

from goldcoast.api.studio_auth import IdentityDep
from goldcoast.api.studio_views import job_view
from goldcoast.studio.brand import resource_view
from goldcoast.studio.feed import FeedRequest
from goldcoast.studio.schedule import ScheduleSave, ScheduleService
from goldcoast.studio.testimonials import TestimonialSave, TestimonialStart
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
    key = {"brand": "brand_analysis", "feed": "feed", "testimonial": "testimonial"}.get(
        job.kind, "campaign"
    )
    step = job.checkpoint.get(key, {})
    if step.get("state") != "completed":
        return None
    output = step.get("output")
    if job.kind == "campaign" and output is not None:
        signals = job.checkpoint.get("local_signals", {})
        return {
            **output,
            "local_signals": signals.get("output") if signals.get("state") == "completed" else None,
        }
    return output


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


@router.get("/feed")
def feed(request: Request, identity: IdentityDep, topic: str = ""):
    from goldcoast.studio.brand import BrandService
    from goldcoast.studio.feed import latest_feed

    repo, assets = request.app.state.repo, request.app.state.assets
    if not BrandService(repo, assets).current(identity.tenant_id, "business"):
        return None
    snapshot = snapshot_business(repo, assets, identity.tenant_id, require_brand=False)
    job = latest_feed(repo, identity.tenant_id, snapshot, topic)
    return job_view(job) if job else None


@router.post("/feed/refresh", status_code=202)
def refresh_feed(body: FeedRequest, request: Request, identity: IdentityDep, key: KeyDep):
    from goldcoast.studio.feed import start_feed

    return job_view(
        start_feed(request.app.state.repo, request.app.state.assets, identity.tenant_id, body, key)
    )


@router.get("/testimonials")
def testimonials(request: Request, identity: IdentityDep):
    return [
        resource_view(r) for r in request.app.state.repo.list(identity.tenant_id, "testimonial")
    ]


@router.post("/testimonials/analyze", status_code=202)
def testimonial_analyze(
    body: TestimonialStart, request: Request, identity: IdentityDep, key: KeyDep
):
    repo, assets = request.app.state.repo, request.app.state.assets
    row = repo.get(identity.tenant_id, "asset", body.asset_id)
    if row.data["role"] != "testimonial":
        raise HTTPException(409, "Select a testimonial video")
    snapshot = snapshot_business(repo, assets, identity.tenant_id, require_brand=False)
    return job_view(
        repo.create_job(
            identity.tenant_id,
            "testimonial",
            "live",
            key,
            {"snapshot": snapshot.model_dump(mode="json"), "asset_id": body.asset_id},
        )
    )


@router.put("/testimonials/{resource_id}")
def testimonial_save(
    resource_id: str, body: TestimonialSave, request: Request, identity: IdentityDep
):
    from goldcoast.studio.testimonials import save_testimonial

    return resource_view(
        save_testimonial(request.app.state.repo, identity.tenant_id, resource_id, body)
    )
