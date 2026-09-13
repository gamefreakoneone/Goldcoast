from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from goldcoast.studio.auth import Principal

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
