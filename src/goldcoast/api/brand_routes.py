from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from goldcoast.api.studio_app import IdentityDep
from goldcoast.studio.brand import (
    AssetRole,
    BrandSave,
    BrandService,
    ProfileSave,
    resource_view,
)

router = APIRouter(prefix="/api/v2")


def service(request):
    return BrandService(request.app.state.repo, request.app.state.assets)


@router.get("/business")
def business(request: Request, identity: IdentityDep):
    row = service(request).current(identity.tenant_id, "business")
    return resource_view(row) if row else None


@router.put("/business")
def save_business(body: ProfileSave, request: Request, identity: IdentityDep):
    return resource_view(
        service(request).save(identity.tenant_id, "business", body.profile, body.version)
    )


@router.get("/brand")
def brand(request: Request, identity: IdentityDep):
    row = service(request).current(identity.tenant_id, "brand")
    return resource_view(row) if row else None


@router.put("/brand")
def save_brand(body: BrandSave, request: Request, identity: IdentityDep):
    try:
        return resource_view(service(request).save_kit(identity.tenant_id, body))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("/assets")
def assets(request: Request, identity: IdentityDep):
    return [resource_view(row) for row in request.app.state.repo.list(identity.tenant_id, "asset")]


@router.post("/assets", status_code=201)
async def upload(
    request: Request,
    identity: IdentityDep,
    role: Annotated[AssetRole, Form()],
    rights_confirmed: Annotated[bool, Form()],
    file: Annotated[UploadFile, File()],
):
    raw = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    try:
        row = service(request).upload(
            identity.tenant_id,
            file.filename or "upload",
            file.content_type,
            role,
            raw,
            rights_confirmed,
        )
        return resource_view(row)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("/assets/{asset_id}/content")
def content(asset_id: str, request: Request, identity: IdentityDep):
    row = request.app.state.repo.get(identity.tenant_id, "asset", asset_id)
    raw = request.app.state.assets.get(identity.tenant_id, asset_id)
    return Response(
        raw,
        media_type=row.data["mime"],
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline"
            if row.data["mime"].startswith("image/")
            else "attachment",
        },
    )
