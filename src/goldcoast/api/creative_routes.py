from fastapi import APIRouter, Request
from fastapi.responses import Response

from goldcoast.api.studio_auth import IdentityDep
from goldcoast.studio.creative import CreativeArtifact, CreativeService, DecisionRequest

router = APIRouter(prefix="/api/v2")


def service(request):
    return CreativeService(request.app.state.repo, request.app.state.assets)


@router.get("/runs/{job_id}/creatives")
def creatives(job_id: str, request: Request, identity: IdentityDep):
    return service(request).list(identity.tenant_id, job_id)


@router.post("/creatives/{creative_id}/decision")
def decide(creative_id: str, body: DecisionRequest, request: Request, identity: IdentityDep):
    return service(request).decide(identity.tenant_id, creative_id, body)


@router.get("/creatives/{creative_id}/content")
def content(creative_id: str, request: Request, identity: IdentityDep):
    row = request.app.state.repo.get(identity.tenant_id, "creative", creative_id)
    CreativeArtifact.model_validate(row.data)
    return Response(
        request.app.state.assets.get(identity.tenant_id, row.id),
        media_type="image/png",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/runs/{job_id}/export")
def export(job_id: str, request: Request, identity: IdentityDep):
    return Response(
        service(request).export(identity.tenant_id, job_id),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="goldcoast-campaign.zip"',
            "Cache-Control": "private, no-store",
        },
    )
