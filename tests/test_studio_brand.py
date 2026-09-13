import io
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError
from test_studio_foundation import foundation as foundation

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.brand import (
    BrandKit,
    BrandSave,
    BrandService,
    BusinessProfile,
    validate_asset,
)
from goldcoast.studio.repository import AccessError, Conflict


def png():
    buffer = io.BytesIO()
    Image.new("RGB", (64, 32), "#245343").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def library(foundation):
    settings, _, repo, first, second = foundation
    service = BrandService(repo, LocalAssetStore(settings.asset_root))
    profile = BusinessProfile(name="Juniper Cafe", city="Los Angeles", confirmed=True)
    service.save(first.id, "business", profile, 0)
    return service, first.id, second.id


def test_upload_and_confirm_visual_brand(library):
    service, tenant, _ = library
    row = service.upload(tenant, "past-ad.png", "image/png", "reference", png(), True)
    assert service.assets.get(tenant, row.id).startswith(b"\x89PNG")
    assert row.data["width"] == 64
    saved = service.save_kit(
        tenant,
        BrandSave(
            version=0,
            kit=BrandKit(
                confirmed=True,
                reference_asset_ids=[row.id],
            ),
        ),
    )
    assert saved.data["confirmed"] is True
    with pytest.raises(Conflict):
        service.save_kit(tenant, BrandSave(version=0, kit=BrandKit()))


def test_foreign_assets_and_wrong_roles_rejected(library):
    service, tenant, other = library
    row = service.upload(tenant, "logo.png", "image/png", "logo", png(), True)
    with pytest.raises(AccessError):
        service.save_kit(other, BrandSave(version=0, kit=BrandKit(reference_asset_ids=[row.id])))
    with pytest.raises(ValueError, match="font"):
        service.save_kit(tenant, BrandSave(version=0, kit=BrandKit(font_asset_id=row.id)))


def test_upload_validation_and_rights(library):
    service, tenant, _ = library
    for raw, mime, role in [
        (b"<svg/>", "image/svg+xml", "logo"),
        (b"not an image", "image/png", "reference"),
        (b"<html>", "application/pdf", "guidelines"),
        (b"badfont", "font/woff2", "font"),
        (b"x" * (10 * 1024 * 1024 + 1), "image/png", "product"),
    ]:
        with pytest.raises(ValueError):
            validate_asset(raw, mime, role)
    with pytest.raises(ValueError, match="permission"):
        service.upload(tenant, "photo.png", "image/png", "product", png(), False)
    with pytest.raises(ValidationError):
        BrandSave(version=0, kit=BrandKit(confirmed=True))
    with pytest.raises(ValidationError):
        BusinessProfile(name="Cafe", city="LA", timezone="invalid/timezone")


def test_analysis_reads_images_but_cannot_self_confirm(library):
    service, tenant, _ = library
    row = service.upload(tenant, "photo.png", "image/png", "reference", png(), True)

    class Client:
        def generate(self, stage, model, parts, config, **kwargs):
            assert parts[1].inline_data.data == service.assets.get(tenant, row.id)
            assert kwargs["input_refs"] == [row.id]
            return SimpleNamespace(
                response_text=BrandKit(
                    confirmed=True,
                    reference_asset_ids=["invented"],
                ).model_dump_json()
            )

    kit = service.analyze(tenant, Client(), "fixture-model")
    assert kit.confirmed is False
    assert kit.reference_asset_ids == [row.id]
    assert service.current(tenant, "brand") is None


def test_product_identity_and_asset_edit(library):
    from goldcoast.studio.brand import AssetEdit, Product

    service, tenant, other = library
    old = service.current(tenant, "business")
    profile = BusinessProfile(name="Cafe", city="LA", products=[Product(name="Matcha")])
    product_id = profile.products[0].id
    service.save(tenant, "business", profile, old.version)
    profile.products[0].name = "Iced matcha"
    assert BusinessProfile.model_validate(profile.model_dump()).products[0].id == product_id
    row = service.upload(tenant, "matcha.png", "image/png", "product", png(), True, product_id)
    assert row.data["product_id"] == product_id
    with pytest.raises(ValueError, match="product"):
        service.edit_asset(
            tenant, row.id, AssetEdit(version=row.version, role="product", product_id="foreign")
        )
    changed = service.edit_asset(
        tenant,
        row.id,
        AssetEdit(
            version=row.version,
            role="reference",
            marketing_kind="inspiration",
            source_url="https://example.com/campaign",
        ),
    )
    assert changed.data["product_id"] is None
    with pytest.raises(Conflict):
        service.edit_asset(tenant, row.id, AssetEdit(version=row.version, role="product"))
    with pytest.raises(AccessError):
        service.edit_asset(other, row.id, AssetEdit(version=changed.version, role="product"))


def test_legacy_product_ids_are_repeatable_and_unassigned_assets_stay_unassigned(library):
    legacy = {"name": "Cafe", "city": "LA", "products": [{"name": "Latte"}]}
    assert (
        BusinessProfile.model_validate(legacy).products[0].id
        == BusinessProfile.model_validate(legacy).products[0].id
    )
    service, tenant, _ = library
    row = service.upload(tenant, "photo.png", "image/png", "product", png(), True)
    assert row.data["product_id"] is None
