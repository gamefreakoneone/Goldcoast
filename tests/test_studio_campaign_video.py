import hashlib
from types import SimpleNamespace

import pytest
from test_studio_brand import png
from test_studio_foundation import foundation as foundation
from test_studio_notify import bot as bot
from test_studio_workflow import campaign as campaign
from test_studio_workflow import factory

from goldcoast.api.creative_routes import video_frame
from goldcoast.studio.brand import AssetEdit, AssetMetadata, BrandService
from goldcoast.studio.notify import campaign_video
from goldcoast.studio.repository import AccessError, Conflict
from goldcoast.studio.video import analyze_campaign_video, frame_bytes
from goldcoast.studio.worker import process_job
from goldcoast.studio.workflow import VideoAnalysis, WorkflowStart, start_campaign


def add_video(repo, assets, tenant, title, product_id=None):
    raw = b"\x00\x00\x00\x18ftypisomfixture"
    row = repo.put(
        tenant,
        "asset",
        AssetMetadata(
            business_id=BrandService(repo, assets).current(tenant, "business").id,
            filename=title.lower().replace(" ", "-") + ".mp4",
            title=title,
            description="A close-up pour and finished drink on the counter.",
            role="video",
            product_id=product_id,
            mime="video/mp4",
            size=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            rights_confirmed=True,
        ).model_dump(mode="json"),
    )
    assets.put(tenant, row.id, raw)
    return row


def test_campaign_video_requires_owner_label_and_can_link_product(campaign, monkeypatch):
    repo, assets, tenant, _, _ = campaign
    product_id = repo.list(tenant, "business")[0].data["products"][0]["id"]
    monkeypatch.setattr(
        "goldcoast.studio.brand.validate_asset", lambda raw, mime, role: (raw, mime, None, None)
    )
    service = BrandService(repo, assets)
    with pytest.raises(ValueError, match="name and description"):
        service.upload(tenant, "drink.mp4", "video/mp4", "video", b"video", True)
    row = service.upload(
        tenant,
        "drink.mp4",
        "video/mp4",
        "video",
        b"video",
        True,
        product_id=product_id,
        title="Limited Edition Boba Tea",
        description="A hand finishes a purple boba tea with ice.",
    )
    assert row.data["title"] == "Limited Edition Boba Tea"
    assert row.data["product_id"] == product_id
    changed = service.edit_asset(
        tenant,
        row.id,
        AssetEdit(
            version=row.version,
            role="video",
            product_id=product_id,
            title="Today's Boba",
            description="A finished purple boba tea beside the menu.",
        ),
    )
    assert changed.data["title"] == "Today's Boba"


def test_video_agent_stores_typed_best_frame(campaign, monkeypatch):
    repo, assets, tenant, _, _ = campaign
    product_id = repo.list(tenant, "business")[0].data["products"][0]["id"]
    video = add_video(repo, assets, tenant, "Limited Edition Boba Tea", product_id)
    job = start_campaign(
        repo,
        assets,
        tenant,
        WorkflowStart(
            mode="live",
            goal="Use my boba video with current topics",
            video_asset_id=video.id,
        ),
        "video-agent",
    )
    captured = {}

    class Client:
        def generate(self, stage, model, parts, config, **kwargs):
            captured.update(
                stage=stage,
                model=model,
                prompt=parts[0],
                schema=config.response_json_schema,
                refs=kwargs["input_refs"],
            )
            return SimpleNamespace(
                response_text=VideoAnalysis(
                    subject="Purple boba tea",
                    observations="A clear cup of purple tea is finished with ice and tapioca.",
                    search_queries=["Los Angeles boba tea current trends"],
                    uncertainty="The flavor is not readable.",
                    best_frame_s=2.4,
                    frame_reason="The finished drink is centered and unobstructed.",
                ).model_dump_json()
            )

    monkeypatch.setattr("goldcoast.studio.video.frame_bytes", lambda raw, stamp: png())
    evidence = analyze_campaign_video(
        repo,
        assets,
        job,
        Client(),
        SimpleNamespace(video_model="fixture-video"),
        lambda kind: captured.update(reserved=kind),
    )
    assert captured["stage"] == "studio_video"
    assert captured["reserved"] == "video"
    assert captured["refs"] == [video.id]
    assert "best_frame_s" in captured["schema"]["required"]
    assert "owner label is context" in captured["prompt"]
    assert evidence.title == "Limited Edition Boba Tea"
    assert evidence.product_id == product_id
    assert assets.get(tenant, evidence.frame_asset_id).startswith(b"\x89PNG")
    assert repo.get(tenant, "campaign_frame", evidence.frame_asset_id).data["job_id"] == job.id


def test_timestamp_must_be_inside_clip(monkeypatch):
    monkeypatch.setattr("goldcoast.studio.video.duration_seconds", lambda path: 2.0)
    monkeypatch.setattr(
        "goldcoast.studio.video.extract_frame",
        lambda *args: pytest.fail("Out-of-range frame was extracted"),
    )
    with pytest.raises(ValueError, match="outside"):
        frame_bytes(b"video", 2.0)


def test_video_flows_through_discovery_and_is_reused_for_regeneration(campaign, monkeypatch):
    repo, assets, tenant, _, _ = campaign
    product_id = repo.list(tenant, "business")[0].data["products"][0]["id"]
    video = add_video(repo, assets, tenant, "Boba launch", product_id)
    job = start_campaign(
        repo,
        assets,
        tenant,
        WorkflowStart(mode="live", goal="Use the launch video", video_asset_id=video.id),
        "video-workflow",
    )
    contexts = []

    def video_factory(repo, assets, job, worker):
        runtime, discovery, _, _, reserve, root = factory(repo, assets, job, worker)
        original = runtime.run

        async def run(name, instructions, payload, output, tools=None):
            contexts.append((name, payload))
            return await original(name, instructions, payload, output, tools)

        runtime.run = run

        class Client:
            def generate(self, *args, **kwargs):
                repo.reserve_call(job.tenant_id, job.id, "model", worker)
                return SimpleNamespace(
                    response_text=VideoAnalysis(
                        subject="Boba tea",
                        observations="A finished iced boba tea is held against a clean counter.",
                        search_queries=["Los Angeles boba events today"],
                        uncertainty="No offer is visible.",
                        best_frame_s=1.5,
                        frame_reason="The full cup and toppings are visible.",
                    ).model_dump_json()
                )

        return (
            runtime,
            discovery,
            Client(),
            SimpleNamespace(video_model="fixture-video"),
            reserve,
            root,
        )

    monkeypatch.setattr("goldcoast.studio.video.frame_bytes", lambda raw, stamp: png())
    process_job(
        repo,
        assets,
        repo.claim("video-worker"),
        "video-worker",
        video_factory,
        creative_producer=None,
    )
    finished = repo.job(tenant, job.id)
    evidence = finished.checkpoint["video_evidence"]["output"]
    assert finished.state == "completed"
    assert finished.input["product_id"] == product_id
    assert finished.checkpoint["campaign"]["output"]["video_evidence"] == evidence
    relevant = [
        payload for name, payload in contexts if name.endswith("scout") or name == "chief_planner"
    ]
    assert all(payload["video_evidence"] == evidence for payload in relevant)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(repo=repo, assets=assets)))
    response = video_frame(job.id, request, SimpleNamespace(tenant_id=tenant))
    assert response.body.startswith(b"\x89PNG")
    with pytest.raises(AccessError, match="Not found"):
        video_frame(job.id, request, SimpleNamespace(tenant_id="f" * 32))

    revision = start_campaign(
        repo,
        assets,
        tenant,
        WorkflowStart(mode="live", regenerate_from=job.id, owner_feedback="More energy"),
        "video-revision",
    )
    assert revision.input["video_evidence"] == evidence
    process_job(
        repo,
        assets,
        repo.claim("revision-worker"),
        "revision-worker",
        factory,
        creative_producer=None,
    )
    revised = repo.job(tenant, revision.id)
    assert revised.state == "completed"
    assert revised.checkpoint["video_evidence"]["output"] == evidence
    assert revised.counters == {}

    replay = start_campaign(
        repo, assets, tenant, WorkflowStart(replay_source=job.id), "video-replay"
    )
    process_job(
        repo,
        assets,
        repo.claim("replay-worker"),
        "replay-worker",
        lambda *args: pytest.fail("Replay constructed live providers"),
        creative_producer=None,
    )
    replayed = repo.job(tenant, replay.id)
    assert replayed.state == "completed"
    assert replayed.checkpoint["video_evidence"]["output"] == evidence
    assert replayed.counters == {}


def test_telegram_video_resolution_is_tenant_scoped_and_deterministic(campaign):
    repo, assets, tenant, other, _ = campaign
    older = add_video(repo, assets, tenant, "Morning matcha")
    newer = add_video(repo, assets, tenant, "Limited Edition Boba Tea")
    assert (
        campaign_video(repo, tenant, "Use the video I just uploaded for today's ad").id == newer.id
    )
    assert (
        campaign_video(repo, tenant, "Build around Morning Matcha and current news").id == older.id
    )
    assert campaign_video(repo, tenant, "A campaign without media") is None
    with pytest.raises(Conflict, match="Name the campaign video"):
        campaign_video(repo, tenant, "Use a video with current topics")
    with pytest.raises(Conflict, match="Upload and name"):
        campaign_video(repo, other, "Use my latest video")


def test_telegram_campaign_uses_latest_video_once(bot):
    product_id = bot.job.input["snapshot"]["profile"]["products"][0]["id"]
    video = add_video(bot.repo, bot.assets, bot.tenant, "Limited Edition Boba Tea", product_id)
    before = bot.repo.tenant(bot.tenant).campaign_grants
    message = {
        "chat": {"id": 42},
        "text": "/campaign Use the video I just uploaded with current topics",
    }
    bot.service.command(message, 777)
    created = next(
        job for job in bot.repo.jobs(bot.tenant) if job.request_key == "telegram-campaign:777"
    )
    assert created.input["video_asset_id"] == video.id
    assert created.input["product_id"] == product_id
    assert "Limited Edition Boba Tea" in bot.calls[-1][1]["text"]
    assert bot.repo.tenant(bot.tenant).campaign_grants == before - 1
    bot.service.command(message, 777)
    assert bot.repo.tenant(bot.tenant).campaign_grants == before - 1
