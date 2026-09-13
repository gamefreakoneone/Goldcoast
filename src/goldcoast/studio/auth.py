from collections.abc import Callable

import jwt
from pydantic import BaseModel

from goldcoast.studio.config import StudioSettings


class Principal(BaseModel):
    subject: str
    issuer: str
    name: str
    role: str
    expires_at: int


class TokenVerifier:
    def __init__(self, settings: StudioSettings, key_resolver: Callable | None = None):
        self.settings = settings
        self.jwks = jwt.PyJWKClient(settings.jwks_url, cache_keys=True, timeout=5)
        self.key_resolver = key_resolver or (
            lambda token: self.jwks.get_signing_key_from_jwt(token).key
        )

    def verify(self, token: str):
        cognito = self.settings.auth_provider == "cognito"
        claims = jwt.decode(
            token,
            self.key_resolver(token),
            algorithms=["RS256"],
            issuer=self.settings.issuer,
            audience=None if cognito else self.settings.client_id,
            options={"require": ["exp", "iat", "sub", "iss"], "verify_aud": not cognito},
        )
        if cognito and (
            claims.get("token_use") != "access"
            or claims.get("client_id") != self.settings.client_id
        ):
            raise jwt.InvalidTokenError("Wrong token purpose or client")
        if not cognito and claims.get("typ") not in {"Bearer", "at+jwt"}:
            raise jwt.InvalidTokenError("An access token is required")
        groups = (
            claims.get("cognito:groups", [])
            if cognito
            else claims.get("realm_access", {}).get("roles", [])
        )
        role = (
            "owner"
            if "goldcoast-owner" in groups
            else "demo"
            if "goldcoast-demo" in groups
            else "business"
        )
        return Principal(
            subject=claims["sub"],
            issuer=claims["iss"],
            name=claims.get("name") or claims.get("preferred_username") or "Business owner",
            role=role,
            expires_at=claims["exp"],
        )
