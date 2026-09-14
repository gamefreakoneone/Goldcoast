import io

import pytest
from PIL import Image
from pydantic import ValidationError
from test_studio_foundation import foundation as foundation
from test_studio_workflow import campaign as campaign

from goldcoast.studio.creative import ComicPanel, CreativeBrief
from goldcoast.studio.repository import Conflict
from goldcoast.studio.social import (
    product_campaign,
    reference_assets,
    render_social,
    validate_social_brief,
)
from goldcoast.studio.testimonials import TestimonialTranscript as Transcript
from goldcoast.studio.testimonials import approved_quote
from goldcoast.studio.workflow import snapshot_business


def test_social_dimensions_comic_and_product_reference_isolation(campaign):
    repo, assets, tenant, _, _ = campaign
    snapshot = snapshot_business(repo, assets, tenant)
    product = snapshot.profile.products[0]
    snapshot.assets = [
        {"id": "right", "data": {"role": "product", "product_id": product.id}},
        {"id": "wrong", "data": {"role": "product", "product_id": "other"}},
        {"id": "legacy", "data": {"role": "product"}},
        {"id": "style", "data": {"role": "reference"}},
    ]
    snapshot.brand.reference_asset_ids = ["style", "wrong"]
    products, styles = reference_assets(snapshot, product.id)
    assert [r["id"] for r in products] == ["right"]
    assert [r["id"] for r in styles] == ["style"]
    brief = CreativeBrief(
        headline="A small pause",
        subheading="Enjoy your afternoon latte.",
        cta="Visit today",
        product_name=product.name,
        image_prompt="Latte",
        caption="A little time for yourself.",
    )
    data = io.BytesIO()
    Image.new("RGB", (300, 300), "#c3a080").save(data, format="PNG")
    raw = data.getvalue()
    for placement, size in [("post", (1080, 1440)), ("story", (1080, 1920))]:
        assert (
            Image.open(
                io.BytesIO(render_social(snapshot.profile, snapshot.brand, brief, [raw], placement))
            ).size
            == size
        )
        comic = brief.model_copy(
            update={
                "creative_type": "comic",
                "panels": [
                    ComicPanel(scene="A student pauses", dialogue=text)
                    for text in [
                        "One more page?",
                        "Make that ten.",
                        "First, a coffee.",
                        "Now we are on the same page.",
                    ]
                ],
            }
        )
        assert (
            Image.open(
                io.BytesIO(
                    render_social(snapshot.profile, snapshot.brand, comic, [raw] * 4, placement)
                )
            ).size
            == size
        )


def test_testimonial_quotes_require_review_and_exact_source(campaign):
    repo, assets, tenant, _, _ = campaign
    transcript = Transcript(
        asset_id="video",
        segments=[
            {"id": "s1", "start": 1, "end": 5, "text": "This is my favorite afternoon latte."}
        ],
        quotes=[{"id": "q1", "segment_id": "s1", "text": "my favorite afternoon latte"}],
    )
    row = repo.put(tenant, "testimonial", transcript.model_dump(mode="json"))
    with pytest.raises(Conflict):
        approved_quote(repo, tenant, row.id, "q1")
    transcript.reviewed, transcript.attribution, transcript.approved_quote_ids = (
        True,
        "A customer",
        ["q1"],
    )
    repo.put(tenant, "testimonial", transcript.model_dump(mode="json"), row.id, row.version)
    quote = approved_quote(repo, tenant, row.id, "q1")
    assert quote["start"] == 1 and quote["end"] == 5
    altered = transcript.model_dump()
    altered["quotes"][0]["text"] = "It changed my life"
    with pytest.raises(ValidationError, match="exact excerpt"):
        Transcript.model_validate(altered)
    snapshot = snapshot_business(repo, assets, tenant)
    brief = CreativeBrief(
        headline="An afternoon favorite",
        subheading="Visit us",
        cta="Stop by",
        product_name="Iced latte",
        image_prompt="Latte",
        creative_type="testimonial",
        quote=quote["text"],
        attribution=quote["attribution"],
    )
    validate_social_brief(brief, snapshot, product_campaign(snapshot, None), "testimonial", quote)
    brief.quote = "Invented endorsement"
    with pytest.raises(ValueError, match="exact reviewed"):
        validate_social_brief(
            brief, snapshot, product_campaign(snapshot, None), "testimonial", quote
        )


@pytest.mark.parametrize("kind,image_calls", [("product", 1), ("comic", 4)])
def test_social_pipeline_reuses_art_for_story_and_exports_caption(campaign, kind, image_calls):
    import asyncio
    import zipfile
    from types import SimpleNamespace

    from goldcoast.studio.creative import CreativeService, CreativeVerdict, DecisionRequest
    from goldcoast.studio.social import produce_social
    from goldcoast.studio.worker import MeteredClient
    from goldcoast.studio.workflow import Stages, WorkflowStart, start_campaign

    repo, assets, tenant, _, root = campaign
    job = start_campaign(
        repo,
        assets,
        tenant,
        WorkflowStart(mode="live", creative_type=kind, include_story=True),
        "social",
    )
    job = repo.claim("worker")
    snapshot = snapshot_business(repo, assets, tenant)
    direction = product_campaign(snapshot, None)
    brief = CreativeBrief(
        headline="Make time for a little pause",
        subheading="Enjoy an iced latte today.",
        cta="Stop by",
        product_name="Iced latte",
        image_prompt="A latte",
        creative_type=kind,
        caption="An afternoon pause at Juniper.",
        panels=[
            ComicPanel(scene="A student with coffee", dialogue=t)
            for t in ["A busy day.", "A small pause.", "An iced latte.", "Ready for the next page."]
        ]
        if kind == "comic"
        else [],
    )

    class Runtime:
        calls = 0

        async def run(self, *args):
            self.calls += 1
            if self.calls == 1:
                CreativeBrief.model_validate({**brief.model_dump(), "cta": "Too long " * 8})
            assert "schema errors" in args[2]["correction"]
            return brief

    class Client:
        calls = 0

        def generate_image(self, *args, output_path, **kwargs):
            self.calls += 1
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (128, 128), "#ae9675").save(output_path)
            return SimpleNamespace(image_path=output_path)

        def generate(self, *args, **kwargs):
            verdict = CreativeVerdict(
                factuality=9,
                brand_fidelity=9,
                visual_quality=9,
                legibility=9,
                feedback="Pass",
                detected_text=brief.headline,
            )
            return SimpleNamespace(response_text=verdict.model_dump_json())

    client = Client()
    stages = Stages(repo, job, "worker")
    asyncio.run(stages.run("campaign", lambda: direction))
    ids = asyncio.run(
        produce_social(
            repo,
            assets,
            job,
            snapshot,
            direction,
            Runtime(),
            MeteredClient(client, lambda kind: repo.reserve_call(tenant, job.id, kind, "worker")),
            SimpleNamespace(image_model="fixture", judge_model="fixture"),
            stages,
            root,
        )
    )
    assert len(ids) == 2 and client.calls == image_calls
    repo.finish(tenant, job.id, "completed", "worker")
    service = CreativeService(repo, assets)
    for identity in ids:
        service.decide(tenant, identity, DecisionRequest(version=1, decision="approved"))
    with zipfile.ZipFile(io.BytesIO(service.export(tenant, job.id))) as archive:
        assert set(archive.namelist()) == {"post.png", "story.png", "caption.txt", "manifest.json"}
        assert archive.read("caption.txt").decode() == brief.caption
