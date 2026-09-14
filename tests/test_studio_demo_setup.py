import pytest
from test_studio_foundation import foundation as foundation

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.demo_setup import seed_demo
from goldcoast.studio.repository import Conflict


def test_demo_setup_is_idempotent_and_does_not_replenish_usage(foundation):
    settings, _, repo, _, _ = foundation
    tenant = repo.ensure_tenant("demo-seed", settings.issuer, "Demo", "demo")
    assets = LocalAssetStore(settings.asset_root)
    result = seed_demo(repo, assets, tenant.id)
    assert result["created"]
    assert len(repo.list(tenant.id, "asset")) == 12
    assert len(repo.list(tenant.id, "business")[0].data["products"]) == 6
    repo.create_job(tenant.id, "feed", "live", "usage-test", {})
    assert repo.tenant(tenant.id).feed_grants == 9
    assert not seed_demo(repo, assets, tenant.id)["created"]
    assert repo.tenant(tenant.id).feed_grants == 9
    assert len(repo.list(tenant.id, "asset")) == 12


def test_demo_setup_preserves_existing_business(foundation):
    settings, _, repo, first, _ = foundation
    assets = LocalAssetStore(settings.asset_root)
    with pytest.raises(Conflict, match="demo accounts"):
        seed_demo(repo, assets, first.id)
    tenant = repo.ensure_tenant("existing-demo", settings.issuer, "Demo", "demo")
    repo.put(tenant.id, "business", {"name": "Keep my business"})
    with pytest.raises(Conflict, match="preserved"):
        seed_demo(repo, assets, tenant.id)
    assert repo.list(tenant.id, "business")[0].data["name"] == "Keep my business"
