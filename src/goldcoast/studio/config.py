import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class StudioSettings(BaseModel):
    database_url: str = Field(repr=False)
    asset_root: Path = Path("output/studio/assets")
    issuer: str = "http://localhost:8080/realms/goldcoast"
    jwks_url: str = "http://localhost:8080/realms/goldcoast/protocol/openid-connect/certs"
    client_id: str = "goldcoast-web"
    auth_provider: str = "keycloak"
    auth_url: str = "http://localhost:8080/realms/goldcoast/protocol/openid-connect/auth"
    token_url: str = "http://localhost:8080/realms/goldcoast/protocol/openid-connect/token"
    logout_url: str = "http://localhost:8080/realms/goldcoast/protocol/openid-connect/logout"
    frontend_origin: str = "http://localhost:5173"
    telegram_token: str = Field(default="", repr=False, exclude=True)
    telegram_bot_link: str = ""

    @classmethod
    def from_env(cls):
        load_dotenv()
        url = os.getenv("GOLDCOAST_DATABASE_URL")
        if not url:
            from sqlalchemy import URL

            password = os.getenv("GOLDCOAST_DB_PASSWORD")
            if not password:
                raise ValueError("Set GOLDCOAST_DB_PASSWORD or GOLDCOAST_DATABASE_URL")
            url = URL.create(
                "postgresql+psycopg",
                username="goldcoast",
                password=password,
                host="127.0.0.1",
                port=5433,
                database="goldcoast",
            ).render_as_string(hide_password=False)
        mapping = {
            "asset_root": "GOLDCOAST_ASSET_ROOT",
            "issuer": "GOLDCOAST_OIDC_ISSUER",
            "jwks_url": "GOLDCOAST_OIDC_JWKS_URL",
            "client_id": "GOLDCOAST_OIDC_CLIENT_ID",
            "auth_provider": "GOLDCOAST_AUTH_PROVIDER",
            "auth_url": "GOLDCOAST_OIDC_AUTH_URL",
            "token_url": "GOLDCOAST_OIDC_TOKEN_URL",
            "logout_url": "GOLDCOAST_OIDC_LOGOUT_URL",
            "frontend_origin": "GOLDCOAST_FRONTEND_ORIGIN",
            "telegram_token": "telegram_token",
            "telegram_bot_link": "telegram_bot_link",
        }
        return cls(
            database_url=url, **{k: os.environ[v] for k, v in mapping.items() if v in os.environ}
        )
