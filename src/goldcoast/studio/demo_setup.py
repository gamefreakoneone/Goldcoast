import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.brand import AssetMetadata, BrandKit, BusinessProfile, Product, validate_asset
from goldcoast.studio.config import StudioSettings
from goldcoast.studio.database import Controls, Resource, Tenant, identifier, session_factory
from goldcoast.studio.repository import Conflict, Repository

ROOT = Path(__file__).resolve().parents[3] / "data" / "margin_demo"
CATALOG = [
    ("matcha", "Iced matcha", "$6", "Iced matcha with milk; a little green pause."),
    ("latte", "Oat latte", "$5.50", "Espresso and steamed oat milk."),
    ("cold-brew", "Cold brew", "$4.50", "Cold brewed coffee over ice."),
    ("croissant", "Butter croissant", "$4", "A flaky butter pastry."),
    ("tote", "Canvas tote", "$18", "A simple canvas carryall for everyday essentials."),
    ("notebook", "Pocket notebook", "$8", "A notebook for ideas between classes."),
]


def demo_profile():
    return BusinessProfile(
        name="Margin Caf\u00e9 & Goods",
        category="cafe_goods",
        city="Los Angeles",
        neighborhood="USC Village",
        address="Near 3215 S Hoover Street, Los Angeles, CA 90007 (demo location anchor only)",
        description=(
            "Coffee, small comforts, and everyday goods for life between classes. "
            "Fictional demonstration business; not a USC tenant or affiliate. "
            "All products, prices and hours are illustrative."
        ),
        hours="Demo hours: Monday-Saturday, 8 am-6 pm",
        audience="USC-area students, neighbors and people looking for an everyday pause.",
        products=[
            Product(id=key, name=name, price=price, description=description)
            for key, name, price, description in CATALOG
        ],
        confirmed=True,
    )


def demo_brand():
    return BrandKit(
        palette=["#263F35", "#F6F0E4", "#EF7F59"],
        typography="serif",
        voice=(
            "Warm, observant and gently witty. Short human sentences. "
            "A small pause between classes."
        ),
        layout=(
            "Editorial product photography, cream space, deep green type and a small orange accent."
        ),
        image_direction=(
            "Natural window light, tactile paper and canvas, honest drink photography. "
            "For comics use warm hand-drawn illustrations and consistent characters."
        ),
        prohibited=["official USC partner", "guaranteed grades", "cures anxiety"],
        confirmed=True,
    )


def seed_demo(repo, assets, tenant_id, root=ROOT, allowances=None):
    allowance = (
        allowances
        if allowances is not None
        else {"campaign": 3, "brand": 2, "feed": 10, "testimonial": 2}
    )
    sources = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    source_by_file = {s["file"]: s for s in sources}
    inventory = [(f"{key}.jpg", "product", key, "owned") for key, *_ in CATALOG]
    inventory += [
        ("margin-logo.png", "logo", None, "owned"),
        ("brand-guidelines.pdf", "guidelines", None, "owned"),
        ("margin-matcha-post.png", "reference", None, "owned"),
        ("margin-notebook-post.png", "reference", None, "owned"),
        ("chamberlain-inspiration.png", "reference", None, "inspiration"),
        ("oatly-inspiration.webp", "reference", None, "inspiration"),
    ]
    with repo.sessions.begin() as session:
        tenant = session.execute(
            select(Tenant).where(Tenant.id == tenant_id).with_for_update()
        ).scalar_one()
        if tenant.role != "demo":
            raise Conflict("Sample setup is restricted to demo accounts")
        marker = session.scalar(
            select(Resource).where(Resource.tenant_id == tenant_id, Resource.kind == "demo_setup")
        )
        if marker:
            return {"created": False, "business_id": marker.data["business_id"]}
        if session.scalar(
            select(Resource).where(Resource.tenant_id == tenant_id, Resource.kind == "business")
        ):
            raise Conflict("Existing business preserved; sample setup did not overwrite it")
        business_id = identifier()
        session.add(
            Resource(
                id=business_id,
                tenant_id=tenant_id,
                kind="business",
                data=demo_profile().model_dump(mode="json"),
            )
        )
        kit = demo_brand()
        for name, role, product, ownership in inventory:
            mime = (
                "application/pdf"
                if name.endswith(".pdf")
                else "image/jpeg"
                if name.endswith(".jpg")
                else "image/webp"
                if name.endswith(".webp")
                else "image/png"
            )
            raw, mime, width, height = validate_asset((root / name).read_bytes(), mime, role)
            asset_id = identifier()
            metadata = AssetMetadata(
                business_id=business_id,
                filename=name,
                role=role,
                product_id=product,
                marketing_kind=ownership,
                source_url=source_by_file.get(name, {}).get("source_url"),
                mime=mime,
                size=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                width=width,
                height=height,
                rights_confirmed=True,
            )
            assets.put(tenant_id, asset_id, raw)
            session.add(
                Resource(
                    id=asset_id,
                    tenant_id=tenant_id,
                    kind="asset",
                    data=metadata.model_dump(mode="json"),
                )
            )
            if role == "logo":
                kit.logo_asset_id = asset_id
            elif role == "reference" and ownership == "owned":
                kit.reference_asset_ids.append(asset_id)
        session.add(Resource(tenant_id=tenant_id, kind="brand", data=kit.model_dump(mode="json")))
        controls = session.execute(
            select(Controls).where(Controls.id == 1).with_for_update()
        ).scalar_one()
        for kind in ("campaign", "brand", "feed", "testimonial"):
            count = allowance.get(kind, 0)
            if not 0 <= count <= 100:
                raise ValueError("Invalid demo allowance")
            field = kind + "_grants"
            setattr(tenant, field, getattr(tenant, field) + count)
            setattr(controls, field, getattr(controls, field) + count)
        controls.live_enabled = True
        session.add(
            Resource(
                tenant_id=tenant_id,
                kind="demo_setup",
                data={"version": 1, "business_id": business_id, "allowances": allowance},
            )
        )
        return {"created": True, "business_id": business_id}


def main():
    parser = argparse.ArgumentParser(
        description="Populate an empty local demo account without resetting usage"
    )
    parser.add_argument("--tenant", required=True)
    args = parser.parse_args()
    settings = StudioSettings.from_env()
    if urlsplit(settings.database_url).hostname not in {"localhost", "127.0.0.1"}:
        raise ValueError("Demo provisioning is restricted to a local database")
    engine, sessions = session_factory(settings.database_url)
    try:
        print(
            json.dumps(
                seed_demo(Repository(sessions), LocalAssetStore(settings.asset_root), args.tenant)
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
