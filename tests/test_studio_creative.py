import asyncio
import io
import zipfile
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError
from test_studio_foundation import foundation as foundation
from test_studio_workflow import campaign as campaign

from goldcoast.studio.brand import BrandKit, BrandService
from goldcoast.studio.compositor import SIZES, compose_html
from goldcoast.studio.creative import (
    CreativeArtifact,
    CreativeBrief,
    CreativeService,
    CreativeVerdict,
    DecisionRequest,
    produce_creatives,
    validate_brief,
)
from goldcoast.studio.graph import build_graph
from goldcoast.studio.repository import AccessError, Conflict
from goldcoast.studio.worker import MeteredClient
from goldcoast.studio.workflow import (
    CampaignResult,
    Candidate,
    Snapshot,
    Stages,
    WorkflowStart,
    start_campaign,
)


def judged_json(verdict):
    return CreativeVerdict.model_validate(
        {
            **verdict.model_dump(),
            "rubric_version": "2026-09-v1",
            "score_reasons": {
                "factuality": "The depicted latte matches the verified product.",
                "brand_fidelity": "The supplied logo and brand palette are retained.",
                "visual_quality": "Lighting and composition are assessed against the reference.",
                "legibility": "Headline and CTA are readable without clipping.",
            },
        }
    ).model_dump_json()


def png(size=(64, 64)):
    stream = io.BytesIO()
    Image.new("RGB", size, "#234235").save(stream, format="PNG")
    return stream.getvalue()


async def produce(campaign, always_fail=False):
    repo, assets, tenant, other, root = campaign
    service = BrandService(repo, assets)
    reference = service.upload(tenant, "latte.png", "image/png", "product", png(), True)
    service.save(tenant, "brand", BrandKit(confirmed=True, reference_asset_ids=[reference.id]), 1)
    job = start_campaign(
        repo, assets, tenant, WorkflowStart(mode="live", creative_type=None), "creative"
    )
    job = repo.claim("worker")
    snapshot = Snapshot.model_validate(job.input["snapshot"])
    brief = CreativeBrief(
        headline="Your daily pause",
        subheading="Come in for an iced latte.",
        cta="Visit today",
        product_name="Iced latte",
        image_prompt="Natural light latte",
    )
    selected = Candidate(
        id="latte",
        category="evergreen",
        title="Coffee time",
        angle="Daily coffee",
        product_name="Iced latte",
        source_ids=[],
        expires_at=datetime.now(UTC) + timedelta(hours=2),
        fit=8,
        timeliness=0,
    )
    result = CampaignResult(
        candidates=[selected],
        selected=selected,
        rationale="Real product",
        graph=build_graph([], []),
        rejected=[],
    )
    stages = Stages(repo, job, "worker")
    await stages.run("campaign", lambda: result)

    class Runtime:
        async def run(self, *args):
            repo.reserve_call(tenant, job.id, "model", "worker")
            return brief

    class Client:
        calls = 0

        def generate_image(self, stage, model, parts, config, output_path, input_refs):
            self.calls += 1
            assert parts[1].inline_data.data == assets.get(tenant, reference.id)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(png())
            return SimpleNamespace(image_path=output_path)

        def generate(self, *args, **kwargs):
            verdict = CreativeVerdict(
                factuality=8,
                brand_fidelity=8,
                visual_quality=5 if always_fail else 8,
                legibility=8,
                critical_issues=[],
                feedback="Improve lighting",
                detected_text="Your daily pause",
            )
            return SimpleNamespace(response_text=judged_json(verdict))

    client = Client()

    async def render(profile, kit, brief, background, format, logo, font):
        return png(SIZES[format])

    ids = await produce_creatives(
        repo,
        assets,
        job,
        snapshot,
        result,
        Runtime(),
        MeteredClient(client, lambda kind: repo.reserve_call(tenant, job.id, kind, "worker")),
        SimpleNamespace(image_model="fixture", judge_model="fixture"),
        stages,
        root,
        renderer=render,
    )
    repo.finish(tenant, job.id, "completed", "worker")
    return CreativeService(repo, assets), job, ids, client, snapshot, brief, selected


def test_reference_generation_judge_approval_and_export(campaign):
    service, job, ids, client, _, _, _ = asyncio.run(produce(campaign))
    tenant = job.tenant_id
    assert len(ids) == 2 and client.calls == 2
    with pytest.raises(Conflict):
        service.export(tenant, job.id)
    for creative_id in ids:
        row = service.repo.get(tenant, "creative", creative_id)
        assert row.data["verdict"]["visual_quality"] == 8
        service.decide(tenant, creative_id, DecisionRequest(version=1, decision="approved"))
    with zipfile.ZipFile(io.BytesIO(service.export(tenant, job.id))) as archive:
        assert set(archive.namelist()) == {"landscape.png", "portrait.png", "manifest.json"}
    with pytest.raises(AccessError):
        service.decide(campaign[3], ids[0], DecisionRequest(version=2, decision="approved"))


def test_retry_budget_and_failed_verdict_cannot_be_approved(campaign):
    service, job, ids, client, _, _, _ = asyncio.run(produce(campaign, always_fail=True))
    assert ids == [] and client.calls == 6
    assert service.repo.job(job.tenant_id, job.id).counters["image"] == 6
    rows = service.list(job.tenant_id, job.id)
    assert len(rows) == 6
    with pytest.raises(Conflict):
        service.decide(
            job.tenant_id, rows[0]["id"], DecisionRequest(version=1, decision="approved")
        )
    invalid = dict(rows[0]["data"])
    invalid.pop("verdict")
    with pytest.raises(ValidationError):
        CreativeArtifact.model_validate(invalid)


def test_profile_edits_invalidate_approval_and_export(campaign):
    service, job, ids, _, snapshot, _, _ = asyncio.run(produce(campaign))
    for creative_id in ids:
        service.decide(job.tenant_id, creative_id, DecisionRequest(version=1, decision="approved"))
    snapshot.profile.name = "Changed business"
    BrandService(service.repo, service.assets).save(job.tenant_id, "business", snapshot.profile, 1)
    assert all(row["stale"] for row in service.list(job.tenant_id, job.id))
    with pytest.raises(Conflict):
        service.export(job.tenant_id, job.id)


def test_brief_rejects_invented_offers_and_escapes_html(campaign):
    _, _, _, _, snapshot, brief, selected = asyncio.run(produce(campaign))
    with pytest.raises(ValueError):
        validate_brief(brief.model_copy(update={"offer_text": "50% off"}), snapshot, selected)
    with pytest.raises(ValueError):
        validate_brief(brief.model_copy(update={"headline": "Free coffee"}), snapshot, selected)
    brief.headline = "<script>alert(1)</script>"
    markup = compose_html(snapshot.profile, snapshot.brand, brief, png(), "landscape")
    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup
