import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from goldcoast.api.studio_app import create_app
from goldcoast.studio.admin import set_allowance
from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.auth import TokenVerifier
from goldcoast.studio.config import StudioSettings
from goldcoast.studio.database import Base, Controls, Job, Tenant, session_factory
from goldcoast.studio.repository import AccessError, Conflict, Repository


@pytest.fixture
def foundation(tmp_path):
    settings = StudioSettings(
        database_url=f"sqlite:///{tmp_path / 'studio.db'}", asset_root=tmp_path / "assets"
    )
    engine, sessions = session_factory(settings.database_url)
    Base.metadata.create_all(engine)
    with sessions.begin() as s:
        s.add(Controls(id=1))
    repo = Repository(sessions)
    first = repo.ensure_tenant("first", settings.issuer, "First", "business")
    second = repo.ensure_tenant("second", settings.issuer, "Second", "business")
    yield settings, sessions, repo, first, second
    engine.dispose()


def test_resources_are_tenant_scoped_and_versioned(foundation):
    _, _, repo, first, second = foundation
    row = repo.put(first.id, "business", {"name": "Cafe"})
    assert repo.list(second.id, "business") == []
    with pytest.raises(AccessError):
        repo.get(second.id, "business", row.id)
    with pytest.raises(AccessError):
        repo.put(second.id, "business", {}, row.id)
    changed = repo.put(first.id, "business", {"name": "Cafe 2"}, row.id, expected_version=1)
    assert changed.version == 2
    with pytest.raises(Conflict):
        repo.put(first.id, "business", {}, row.id, expected_version=1)


def test_live_reservation_idempotency_and_cancellation(foundation):
    _, sessions, repo, first, second = foundation
    with pytest.raises(Conflict, match="disabled"):
        repo.create_job(first.id, "campaign", "live", "one", {})
    repo.controls(enabled=True)
    with pytest.raises(Conflict, match="exhausted"):
        repo.create_job(first.id, "campaign", "live", "one", {})
    repo.grant(first.id, 1, 0)
    row = repo.create_job(first.id, "campaign", "live", "one", {})
    assert repo.create_job(first.id, "campaign", "live", "one", {}).id == row.id
    with pytest.raises(Conflict, match="another request"):
        repo.create_job(first.id, "campaign", "live", "one", {"changed": True})
    with pytest.raises(Conflict, match="active"):
        repo.create_job(first.id, "brand", "live", "two", {})
    with pytest.raises(AccessError):
        repo.finish(second.id, row.id, "cancelled")
    repo.finish(first.id, row.id, "cancelled")
    assert repo.tenant(first.id).active_job is None
    assert repo.tenant(first.id).campaign_grants == 0
    with sessions() as s:
        assert s.get(Controls, 1).campaign_grants == 2


def test_replay_cannot_consume_provider_allowance(foundation):
    _, _, repo, first, _ = foundation
    row = repo.create_job(first.id, "campaign", "replay", "replay", {})
    with pytest.raises(Conflict):
        repo.reserve_call(first.id, row.id, "model", "worker-b")
    assert repo.tenant(first.id).campaign_grants == 0


def test_durable_counts_kill_switch_and_job_recovery(foundation):
    _, _, repo, first, _ = foundation
    repo.controls(enabled=True)
    repo.grant(first.id, 1, 0)
    row = repo.create_job(first.id, "campaign", "live", "live", {})
    assert repo.claim("worker-a").id == row.id
    for _ in range(6):
        repo.reserve_call(first.id, row.id, "image", "worker-a")
    with pytest.raises(Conflict, match="exhausted"):
        repo.reserve_call(first.id, row.id, "image", "worker-a")
    assert Repository(repo.sessions).job(first.id, row.id).counters["image"] == 6
    with repo.sessions.begin() as session:
        session.execute(update(Job).where(Job.id == row.id).values(lease_until=0))
    assert repo.claim("worker-b").id == row.id
    with pytest.raises(Conflict):
        repo.checkpoint(first.id, row.id, "worker-a", {})
    repo.checkpoint(first.id, row.id, "worker-b", {"stage": "judge"})
    repo.controls(enabled=False)
    with pytest.raises(Conflict):
        repo.reserve_call(first.id, row.id, "model", "worker-b")


def test_events_are_durable_ordered_and_scoped(foundation):
    _, _, repo, first, second = foundation
    row = repo.create_job(first.id, "campaign", "replay", "events", {})
    for i in range(3):
        repo.emit(first.id, row.id, "progress", {"step": i})
    assert [e.sequence for e in Repository(repo.sessions).events(first.id, row.id, 0)] == [1, 2]
    with pytest.raises(AccessError):
        repo.events(second.id, row.id)


def test_local_assets_confine_paths_and_tenants(tmp_path):
    store = LocalAssetStore(tmp_path)
    store.put("a" * 32, "b" * 32, b"private")
    assert store.get("a" * 32, "b" * 32) == b"private"
    with pytest.raises(FileNotFoundError):
        store.get("c" * 32, "b" * 32)
    with pytest.raises(ValueError):
        store.get("a" * 32, "../escape")


def test_signed_jwt_auth_and_owner_routes(foundation):
    settings, sessions, _, _, _ = foundation
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = TokenVerifier(settings, key_resolver=lambda _: key.public_key())

    def token(subject="person", roles=None, **changes):
        claims = {
            "sub": subject,
            "iss": settings.issuer,
            "aud": settings.client_id,
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
            "typ": "Bearer",
            "realm_access": {"roles": roles or []},
        }
        claims.update(changes)
        return {"Authorization": "Bearer " + jwt.encode(claims, key, algorithm="RS256")}

    with TestClient(create_app(settings, sessions, verifier)) as client:
        assert client.get("/api/v2/me").status_code == 401
        assert client.get("/api/v2/me", headers=token(aud="wrong")).status_code == 401
        assert client.get("/api/v2/me", headers=token(exp=1)).status_code == 401
        assert client.get("/api/v2/me", headers=token(typ="ID")).status_code == 401
        response = client.get("/api/v2/me", headers=token())
        assert response.status_code == 200
        tenant_id = response.json()["id"]
        for headers in [
            token(),
            token("owner", ["goldcoast-owner"]),
            token("judge", ["goldcoast-demo"]),
            {},
        ]:
            assert (
                client.post(
                    "/api/v2/admin/controls", headers=headers, json={"enabled": True}
                ).status_code
                == 404
            )
            assert (
                client.post(
                    f"/api/v2/admin/grants/{tenant_id}", headers=headers, json={"campaign": 5}
                ).status_code
                == 404
            )
        assert client.get("/api/v2/usage", headers=token()).json()["campaign_remaining"] == 0
        assert client.get("/runs").status_code == 404
    with sessions() as s:
        assert s.scalar(select(Tenant).where(Tenant.id == tenant_id)).role == "business"


def test_cognito_requires_access_token_and_matching_client():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = StudioSettings(
        database_url="sqlite://", auth_provider="cognito", issuer="https://issuer.example"
    )
    verifier = TokenVerifier(settings, key_resolver=lambda _: key.public_key())
    claims = {
        "sub": "one",
        "iss": settings.issuer,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "client_id": settings.client_id,
        "token_use": "access",
        "cognito:groups": ["goldcoast-demo"],
    }
    assert verifier.verify(jwt.encode(claims, key, algorithm="RS256")).role == "demo"
    for changes in [{"token_use": "id"}, {"client_id": "wrong"}]:
        with pytest.raises(jwt.InvalidTokenError):
            verifier.verify(jwt.encode({**claims, **changes}, key, algorithm="RS256"))


def test_exact_allowances_preserve_other_users_and_shared_budget(foundation):
    _, _, repo, first, second = foundation
    values = dict(campaigns=5, brand_analyses=5, feed_refreshes=5)
    for _ in range(2):
        result = set_allowance(repo.sessions, first.id, values)
        assert result["after"] == values
    assert repo.tenant(second.id).campaign_grants == 0
    assert repo.controls().campaign_grants == 3
    assert not repo.controls().live_enabled
    set_allowance(repo.sessions, first.id, {"campaigns": 0})
    assert repo.tenant(first.id).brand_grants == 5
    assert repo.tenant(first.id).campaign_grants == 0
    set_allowance(repo.sessions, None, values)
    assert repo.controls().feed_grants == 5
    assert not repo.controls().live_enabled


def test_invalid_changes_are_atomic_and_roles_do_not_bypass_limits(foundation):
    settings, _, repo, first, _ = foundation
    for values in ({"campaigns": -1}, {"campaigns": 5, "feed_refreshes": -1}, {}):
        with pytest.raises(ValueError):
            set_allowance(repo.sessions, first.id, values)
    with pytest.raises(ValueError):
        set_allowance(repo.sessions, "missing", {"campaigns": 5})
    for role in ("owner", "demo"):
        user = repo.ensure_tenant(role, settings.issuer, role, role)
        set_allowance(repo.sessions, user.id, {"campaigns": 5})
        assert repo.tenant(user.id).campaign_grants == 5
    assert repo.tenant(first.id).campaign_grants == 0
