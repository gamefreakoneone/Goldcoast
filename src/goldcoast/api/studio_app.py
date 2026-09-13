import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.auth import Principal, TokenVerifier
from goldcoast.studio.config import StudioSettings
from goldcoast.studio.database import Controls, session_factory
from goldcoast.studio.repository import TERMINAL, AccessError, Conflict, Repository

bearer = HTTPBearer(auto_error=False)


@dataclass
class Identity:
    tenant_id: str
    principal: Principal


def authenticated(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Identity:
    if credentials is None:
        raise HTTPException(401, "Sign in to continue", headers={"WWW-Authenticate": "Bearer"})
    try:
        principal = request.app.state.verifier.verify(credentials.credentials)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Invalid or expired access token") from None
    tenant = request.app.state.repo.ensure_tenant(
        principal.subject, principal.issuer, principal.name, principal.role
    )
    return Identity(tenant.id, principal)


IdentityDep = Annotated[Identity, Depends(authenticated)]


def owner(identity: IdentityDep):
    if identity.principal.role != "owner":
        raise HTTPException(403, "Owner access required")
    return identity


OwnerDep = Annotated[Identity, Depends(owner)]


class GrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign: int = Field(default=0, ge=0, le=100)
    brand: int = Field(default=0, ge=0, le=100)


class ControlRequest(GrantRequest):
    enabled: bool | None = None


def job_view(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "mode": row.mode,
        "state": row.state,
        "input": row.input,
        "checkpoint": row.checkpoint,
        "counters": row.counters,
        "created_at": row.created_at,
        "finished_at": row.finished_at,
    }


def create_app(settings: StudioSettings | None = None, sessions=None, verifier=None):
    @asynccontextmanager
    async def lifespan(app):
        configured = settings or StudioSettings.from_env()
        app.state.settings = configured
        engine, factory = (
            session_factory(configured.database_url) if sessions is None else (None, sessions)
        )
        app.state.repo = Repository(factory)
        app.state.verifier = verifier or TokenVerifier(configured)
        app.state.assets = LocalAssetStore(configured.asset_root)
        with factory() as session:
            session.execute(select(Controls).where(Controls.id == 1)).scalar_one()
        yield
        if engine:
            engine.dispose()

    app = FastAPI(title="Goldcoast Marketing Studio", version="2.0", lifespan=lifespan)
    origins = [settings.frontend_origin] if settings else ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Last-Event-ID"],
    )

    @app.exception_handler(AccessError)
    async def access_error(request, exc):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    @app.exception_handler(Conflict)
    async def conflict_error(request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/health")
    def health():
        return {"status": "ok", "application": "goldcoast-studio"}

    @app.get("/api/v2/auth/config")
    def auth_config(request: Request):
        configured = request.app.state.settings
        return {
            "issuer": configured.issuer,
            "client_id": configured.client_id,
            "authorization_endpoint": configured.auth_url,
            "token_endpoint": configured.token_url,
            "logout_endpoint": configured.logout_url,
            "registration": "invitation-only",
        }

    @app.get("/api/v2/me")
    def me(request: Request, identity: IdentityDep):
        row = request.app.state.repo.tenant(identity.tenant_id)
        return {"id": row.id, "name": row.name, "role": identity.principal.role}

    @app.get("/api/v2/usage")
    def usage(request: Request, identity: IdentityDep):
        row = request.app.state.repo.tenant(identity.tenant_id)
        controls = request.app.state.repo.controls()
        return {
            "campaign_remaining": row.campaign_grants,
            "brand_remaining": row.brand_grants,
            "active_job": row.active_job,
            "live_enabled": controls.live_enabled,
            "global_campaign_remaining": controls.campaign_grants,
            "global_brand_remaining": controls.brand_grants,
        }

    @app.post("/api/v2/admin/grants/{tenant_id}")
    def grants(tenant_id: str, body: GrantRequest, request: Request, identity: OwnerDep):
        request.app.state.repo.grant(tenant_id, body.campaign, body.brand)
        return {"updated": True}

    @app.post("/api/v2/admin/controls")
    def controls(body: ControlRequest, request: Request, identity: OwnerDep):
        row = request.app.state.repo.controls(
            enabled=body.enabled, campaign=body.campaign, brand=body.brand
        )
        return {
            "live_enabled": row.live_enabled,
            "campaign_remaining": row.campaign_grants,
            "brand_remaining": row.brand_grants,
        }

    @app.get("/api/v2/runs")
    def runs(request: Request, identity: IdentityDep):
        return [job_view(row) for row in request.app.state.repo.jobs(identity.tenant_id)]

    @app.get("/api/v2/runs/{job_id}")
    def run(job_id: str, request: Request, identity: IdentityDep):
        return job_view(request.app.state.repo.job(identity.tenant_id, job_id))

    @app.post("/api/v2/runs/{job_id}/cancel")
    def cancel(job_id: str, request: Request, identity: IdentityDep):
        repo = request.app.state.repo
        row = repo.finish(identity.tenant_id, job_id, "cancelled")
        return job_view(row)

    @app.get("/api/v2/runs/{job_id}/events")
    async def events(
        job_id: str,
        request: Request,
        identity: IdentityDep,
        last_event_id: Annotated[str | None, Header()] = None,
    ):
        repo = request.app.state.repo
        repo.job(identity.tenant_id, job_id)
        try:
            after = int(last_event_id) if last_event_id is not None else -1
            if after < -1:
                raise ValueError()
        except ValueError:
            raise HTTPException(400, "Invalid event cursor") from None

        async def stream():
            cursor = after
            heartbeat = time.monotonic()
            while time.time() < identity.principal.expires_at:
                rows = await asyncio.to_thread(repo.events, identity.tenant_id, job_id, cursor)
                for row in rows:
                    cursor = row.sequence
                    payload = {
                        "id": str(cursor),
                        "type": row.type,
                        "timestamp": row.timestamp,
                        "payload": row.payload,
                    }
                    yield f"id: {cursor}\ndata: {json.dumps(payload)}\n\n"
                if len(rows) == 200:
                    continue
                job = await asyncio.to_thread(repo.job, identity.tenant_id, job_id)
                if job.state in TERMINAL:
                    break
                if await request.is_disconnected():
                    break
                if time.monotonic() - heartbeat >= 15:
                    yield ": heartbeat\n\n"
                    heartbeat = time.monotonic()
                await asyncio.sleep(0.5)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
