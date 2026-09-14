import asyncio
import copy
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from test_studio_creative import judged_json, png
from test_studio_foundation import foundation as foundation
from test_studio_workflow import campaign as campaign
from test_studio_workflow import factory

from goldcoast.studio.config import StudioSettings
from goldcoast.studio.creative import (
    CreativeArtifact,
    CreativeBrief,
    CreativeService,
    CreativeVerdict,
    DecisionRequest,
)
from goldcoast.studio.database import Job, Tenant
from goldcoast.studio.notify import (
    NotificationService,
    TelegramClient,
    TelegramError,
    TelegramPoller,
    creative_caption,
    creative_keyboard,
)
from goldcoast.studio.repository import AccessError, Conflict
from goldcoast.studio.social import product_campaign
from goldcoast.studio.worker import process_job
from goldcoast.studio.workflow import Snapshot, WorkflowStart, start_campaign


@pytest.fixture
def bot(campaign):
    repo, assets, tenant, other, root = campaign
    calls = []
    updates = []

    def transport(request):
        method = request.url.path.rsplit("/", 1)[-1]
        raw = request.read()
        data = (
            json.loads(raw)
            if "application/json" in request.headers.get("content-type", "")
            else raw
        )
        calls.append((method, data, request.extensions["timeout"]))
        result = (
            list(updates)
            if method == "getUpdates"
            else {"message_id": len(calls), "chat": {"id": 42}}
        )
        return httpx.Response(200, json={"ok": True, "result": result})

    settings = StudioSettings(
        database_url="sqlite://",
        telegram_token="test-secret",
        telegram_bot_link="https://t.me/goldcoast_test",
    )
    service = NotificationService(
        repo,
        assets,
        settings,
        TelegramClient(settings.telegram_token, httpx.MockTransport(transport)),
    )
    link = service.link(tenant)
    service.handle(
        {
            "update_id": 1,
            "message": {
                "chat": {"id": 42},
                "from": {"first_name": "Owner"},
                "text": "/start " + link.code,
            },
        }
    )
    job = start_campaign(
        repo,
        assets,
        tenant,
        WorkflowStart(mode="live", creative_type="product", include_story=True),
        "source",
    )
    job = repo.claim("worker")
    snapshot = Snapshot.model_validate(job.input["snapshot"])
    campaign_result = product_campaign(snapshot, None)
    brief = CreativeBrief(
        headline="An afternoon pause",
        subheading="Your iced latte awaits",
        cta="Visit today",
        product_name="Iced latte",
        image_prompt="A cold latte",
        caption="Cool down & enjoy <a latte>.",
    )
    artifact = CreativeArtifact(
        job_id=job.id,
        business_id=snapshot.business_id,
        brand_id=snapshot.brand_id,
        format="post",
        attempt=1,
        width=1080,
        height=1440,
        sha256="",
        brief=brief,
        verdict=CreativeVerdict(
            factuality=9,
            brand_fidelity=8,
            visual_quality=8,
            legibility=9,
            feedback="Looks good",
            detected_text="Latte",
        ),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    creative = CreativeService(repo, assets).save(tenant, artifact, png((1080, 1440)))
    repo.checkpoint(
        tenant,
        job.id,
        "worker",
        {
            "campaign": {"state": "completed", "output": campaign_result.model_dump(mode="json")},
            "creative_result": {
                "state": "completed",
                "output": {"passing_creative_ids": [creative["id"]]},
            },
        },
    )
    repo.finish(tenant, job.id, "completed", "worker")
    return SimpleNamespace(
        repo=repo,
        assets=assets,
        tenant=tenant,
        other=other,
        root=root,
        service=service,
        settings=settings,
        calls=calls,
        updates=updates,
        job=repo.job(tenant, job.id),
        creative=creative,
        artifact=artifact,
    )


def callback(bot, data, update_id=10, chat=42, message_id=100):
    return {
        "update_id": update_id,
        "callback_query": {
            "id": "callback-" + str(update_id),
            "data": data,
            "message": {
                "chat": {"id": chat},
                "message_id": message_id,
                "caption": "A latte & a pause",
            },
        },
    }


def command(bot, text, update_id=500, chat=42):
    bot.service.handle({"update_id": update_id, "message": {"chat": {"id": chat}, "text": text}})
    return bot.calls[-1][1]["text"]


@pytest.mark.parametrize("text", ["/start", "/commands", "/commnads", "/help"])
def test_command_help_is_free_and_available_before_linking(bot, text):
    before = bot.repo.tenant(bot.tenant).campaign_grants
    assert "/campaign" in command(bot, text, chat=99)
    assert bot.repo.tenant(bot.tenant).campaign_grants == before


def test_campaign_command_reuses_update_key_and_preserves_brief(bot):
    before = bot.repo.tenant(bot.tenant).campaign_grants
    assert "queued" in command(bot, "/campaign Feature our iced latte")
    assert "queued" in command(bot, "/campaign Feature our iced latte")
    assert bot.repo.tenant(bot.tenant).campaign_grants == before - 1
    jobs = [job for job in bot.repo.jobs(bot.tenant) if job.id != bot.job.id]
    assert len(jobs) == 1
    assert jobs[0].input["goal"] == "Feature our iced latte"
    assert jobs[0].mode == "live"
    assert "could not start" in command(bot, "/campaign Another", update_id=501)
    assert bot.repo.tenant(bot.tenant).campaign_grants == before - 1


def test_command_status_credits_and_tenant_isolation(bot):
    before = bot.repo.tenant(bot.tenant).campaign_grants
    assert "completed" in command(bot, "/status")
    assert bot.job.id in command(bot, "/status")
    assert f"Campaign credits: {before}" in command(bot, "/credits")
    assert "Connect exactly one" in command(bot, "/campaign", chat=99)
    assert "1500" in command(bot, "/campaign " + "x" * 1501)
    assert bot.repo.tenant(bot.tenant).campaign_grants == before


def test_campaign_command_disabled_or_depleted_does_not_start(bot):
    bot.service.toggle(bot.tenant, False)
    assert "Enable Telegram" in command(bot, "/campaign")
    bot.service.toggle(bot.tenant, True)
    with bot.repo.sessions.begin() as session:
        session.get(Tenant, bot.tenant).campaign_grants = 0
    assert "could not start" in command(bot, "/campaign")
    assert len(bot.repo.jobs(bot.tenant)) == 1


def test_native_command_menu_transport(bot):
    bot.service.client.set_commands()
    method, payload, timeout = bot.calls[-1]
    assert method == "setMyCommands"
    assert [item["command"] for item in payload["commands"]] == [
        "start",
        "commands",
        "campaign",
        "status",
        "credits",
    ]
    assert "1 credit" in payload["commands"][2]["description"]
    assert timeout["read"] == 10


def reply(bot, prompt, note, update_id=11, chat=42):
    return {
        "update_id": update_id,
        "message": {
            "chat": {"id": chat},
            "text": note,
            "reply_to_message": {"message_id": prompt.prompt_message_id, "from": {"is_bot": True}},
        },
    }


def test_link_lifecycle_expiry_and_safe_view(bot):
    assert bot.service.view(bot.tenant).chat_title == "Owner"
    assert "pending" not in bot.service.view(bot.tenant).model_dump()
    first = bot.service.link(bot.other)
    second = bot.service.link(bot.other)
    assert len(first.code) == 8 and first.code != second.code
    assert second.deep_link.endswith("?start=" + second.code)
    bot.service.connect({"chat": {"id": 51}, "text": "/start " + first.code}, 2)
    assert bot.service.current(bot.other) is None
    rows = bot.repo.list(bot.other, "telegram_link")
    bot.repo.put(
        bot.other, "telegram_link", {**rows[0].data, "expires_at": 0}, rows[0].id, rows[0].version
    )
    bot.service.connect({"chat": {"id": 51}, "text": "/start " + second.code}, 3)
    assert bot.service.current(bot.other) is None
    assert "expired" in bot.calls[-1][1]["text"]
    assert bot.service.toggle(bot.tenant, False).enabled is False
    bot.service.unlink(bot.tenant)
    assert bot.service.current(bot.tenant) is None and not bot.repo.list(
        bot.tenant, "telegram_link"
    )


def test_transport_multipart_timeouts_caption_and_secret_safety(bot):
    bot.service.notify_job(bot.job)
    photo = next(c for c in bot.calls if c[0] == "sendPhoto")
    assert b"image/png" in photo[1] and b'filename="creative.png"' in photo[1]
    assert b"&amp;" in photo[1] and b"&lt;a latte&gt;" in photo[1]
    assert b"full-resolution" in photo[1] and b"inline_keyboard" in photo[1]
    assert photo[2]["read"] == 10
    bot.service.client.get_updates(99)
    assert bot.calls[-1][1]["timeout"] == 20 and bot.calls[-1][2]["read"] == 30
    assert "test-secret" not in repr(bot.settings) + bot.settings.model_dump_json()
    artifact = bot.artifact.model_copy(deep=True)
    artifact.brief.caption = "<&😀" * 500
    caption = creative_caption(bot.settings, bot.job, artifact)
    assert len(caption.encode("utf-16-le")) // 2 <= 920
    assert caption.count("<b>") == caption.count("</b>") == 2
    keyboard = creative_keyboard(bot.creative["id"], 1, bot.job.id)
    assert all(
        len(b["callback_data"].encode()) <= 64 for row in keyboard["inline_keyboard"] for b in row
    )

    def fail(request):
        raise httpx.ConnectError("secret " + str(request.url))

    client = TelegramClient("test-secret", httpx.MockTransport(fail))
    with pytest.raises(TelegramError) as error:
        client.send_message(42, "Hello")
    assert "test-secret" not in str(error.value)


def test_approve_is_shared_authorized_and_duplicate_safe(bot):
    data = f"d:{bot.creative['id']}:1:approved"
    bot.service.handle(callback(bot, data, chat=7))
    assert bot.calls[-1][1]["text"] == "Not authorized"
    assert bot.repo.get(bot.tenant, "creative", bot.creative["id"]).version == 1
    update = callback(bot, data, update_id=11)
    bot.service.handle(update)
    row = bot.repo.get(bot.tenant, "creative", bot.creative["id"])
    assert (
        row.version == 2
        and row.data["decision"] == "approved"
        and row.data["decided_via"] == "telegram"
    )
    count = len(bot.calls)
    bot.service.handle(update)
    assert len(bot.calls) == count
    assert any(
        c[0] == "editMessageCaption" and "Approved on Telegram" in c[1]["caption"]
        for c in bot.calls
    )


def test_studio_decision_makes_phone_buttons_stale(bot):
    CreativeService(bot.repo, bot.assets).decide(
        bot.tenant,
        bot.creative["id"],
        DecisionRequest(version=1, decision="rejected", note="Wrong angle"),
    )
    bot.service.handle(callback(bot, f"d:{bot.creative['id']}:1:approved"))
    assert any(
        c[0] == "answerCallbackQuery" and c[1]["show_alert"] and "changed" in c[1]["text"]
        for c in bot.calls
    )
    assert bot.calls[-1][0] == "editMessageReplyMarkup"
    row = bot.repo.get(bot.tenant, "creative", bot.creative["id"])
    assert row.data["decision"] == "rejected" and row.data["decided_via"] == "studio"


@pytest.mark.parametrize("skip", [False, True])
def test_reject_with_reason_or_skip_never_regenerates(bot, skip):
    data = f"d:{bot.creative['id']}:1:rejected"
    bot.service.handle(callback(bot, data))
    pending = next(iter(bot.service.current(bot.tenant).pending.values()))
    assert any(
        c[0] == "sendMessage" and c[1].get("reply_markup", {}).get("force_reply") for c in bot.calls
    )
    if skip:
        bot.service.handle(
            callback(bot, data + ":skip", update_id=11, message_id=pending.skip_message_id)
        )
    else:
        bot.service.handle(reply(bot, pending, "Too busy", chat=99))
        assert bot.repo.get(bot.tenant, "creative", bot.creative["id"]).version == 1
        bot.service.handle(reply(bot, pending, "Too busy", update_id=12))
    row = bot.repo.get(bot.tenant, "creative", bot.creative["id"])
    assert row.data["decision"] == "rejected" and row.data["decision_note"] == (
        "" if skip else "Too busy"
    )
    assert not bot.service.current(bot.tenant).pending
    assert len(bot.repo.jobs(bot.tenant)) == 1


def test_regeneration_reuses_contract_and_consumes_one_grant(bot):
    before = bot.repo.tenant(bot.tenant).campaign_grants
    bot.service.handle(callback(bot, "r:" + bot.job.id))
    prompt = next(iter(bot.service.current(bot.tenant).pending.values()))
    update = reply(bot, prompt, "Use warmer colors")
    bot.service.handle(update)
    bot.service.handle(update)
    jobs = bot.repo.jobs(bot.tenant)
    new = next(j for j in jobs if j.id != bot.job.id)
    assert new.input["regenerate_from"] == bot.job.id
    assert new.input["started_via"] == "telegram"
    assert any(new.id in call[1].get("text", "") for call in bot.calls if call[0] == "sendMessage")
    assert new.input["owner_feedback"] == "Use warmer colors"
    assert new.input["selected_campaign"] == bot.job.checkpoint["campaign"]["output"]
    assert new.input["snapshot"] == bot.job.input["snapshot"]
    assert new.input["include_story"] is True and new.input["creative_type"] == "product"
    assert new.request_key == "telegram:11" and len(jobs) == 2
    assert bot.repo.tenant(bot.tenant).campaign_grants == before - 1
    assert "Uses 1 campaign credit" in bot.calls[-1][1]["text"]


def test_regeneration_exhausted_allowance_replies_without_job(bot):
    with bot.repo.sessions.begin() as session:
        session.get(Tenant, bot.tenant).campaign_grants = 0
    bot.service.handle(callback(bot, "r:" + bot.job.id))
    prompt = next(iter(bot.service.current(bot.tenant).pending.values()))
    bot.service.handle(reply(bot, prompt, "Make it warmer"))
    assert "allowance exhausted" in bot.calls[-1][1]["text"]
    assert len(bot.repo.jobs(bot.tenant)) == 1


@pytest.mark.parametrize("changed", ["profile", "expired", "foreign", "active"])
def test_regeneration_rejects_invalid_source_before_spending(bot, changed):
    tenant = bot.tenant
    if changed == "profile":
        row = bot.repo.list(tenant, "business")[0]
        bot.repo.put(tenant, "business", {**row.data, "name": "Changed"}, row.id, row.version)
    elif changed == "expired":
        with bot.repo.sessions.begin() as session:
            row = session.get(Job, bot.job.id)
            checkpoint = copy.deepcopy(row.checkpoint)
            checkpoint["campaign"]["output"]["selected"]["expires_at"] = "2000-01-01T00:00:00Z"
            row.checkpoint = checkpoint
    elif changed == "foreign":
        tenant = bot.other
    else:
        start_campaign(
            bot.repo,
            bot.assets,
            tenant,
            WorkflowStart(mode="live", creative_type="product"),
            "already-active",
        )
    before = bot.repo.tenant(tenant).campaign_grants
    with pytest.raises((Conflict, AccessError)):
        start_campaign(
            bot.repo,
            bot.assets,
            tenant,
            WorkflowStart(mode="live", regenerate_from=bot.job.id, owner_feedback="Change it"),
            "invalid",
        )
    assert bot.repo.tenant(tenant).campaign_grants == before


def test_replay_disabled_and_duplicate_sends_are_suppressed(bot):
    before = len(bot.calls)
    replay = SimpleNamespace(**{**bot.job.__dict__, "mode": "replay"})
    bot.service.notify_job(replay)
    bot.service.toggle(bot.tenant, False)
    bot.service.notify_job(bot.job)
    assert len(bot.calls) == before
    bot.service.toggle(bot.tenant, True)
    bot.service.notify_job(bot.job)
    bot.service.notify_job(bot.job)
    assert len([c for c in bot.calls if c[0] == "sendPhoto"]) == 1


def test_poller_offset_and_receipts_survive_restart(bot):
    update = callback(bot, f"d:{bot.creative['id']}:1:approved", update_id=123)
    bot.updates[:] = [update]
    poller = TelegramPoller(bot.service)
    poller.tick()
    assert bot.repo.controls().telegram_offset == 124
    count = len([c for c in bot.calls if c[0] == "editMessageCaption"])
    TelegramPoller(bot.service).tick()
    assert len([c for c in bot.calls if c[0] == "editMessageCaption"]) == count
    assert bot.calls[-1][1]["offset"] == 124
    with bot.repo.sessions.begin() as session:
        from goldcoast.studio.database import Controls

        session.get(Controls, 1).telegram_offset = 0
    TelegramPoller(bot.service).tick()
    assert bot.repo.get(bot.tenant, "creative", bot.creative["id"]).version == 2


def test_telegram_outage_does_not_fail_job(bot, monkeypatch):
    def failed(*args):
        raise RuntimeError("test-secret")

    bot.service.client.send_photo = failed
    bot.service.notify_job(bot.job)
    events = bot.repo.events(bot.tenant, bot.job.id)
    assert events[-1].type == "notification_failed" and "test-secret" not in str(events[-1].payload)
    assert bot.repo.job(bot.tenant, bot.job.id).state == "completed"
    monkeypatch.setattr(StudioSettings, "from_env", classmethod(lambda cls: bot.settings))
    monkeypatch.setattr(TelegramClient, "send_message", failed)
    job = start_campaign(
        bot.repo,
        bot.assets,
        bot.tenant,
        WorkflowStart(mode="live", creative_type="product"),
        "failed-notification",
    )

    def provider_failure(*args):
        raise ValueError("Safe campaign failure")

    process_job(
        bot.repo,
        bot.assets,
        bot.repo.claim("worker"),
        "worker",
        provider_failure,
        creative_producer=None,
    )
    assert bot.repo.job(bot.tenant, job.id).state == "failed"
    assert any(e.type == "notification_failed" for e in bot.repo.events(bot.tenant, job.id))


def test_regeneration_execution_reuses_selected_campaign_for_product(bot):
    new = start_campaign(
        bot.repo,
        bot.assets,
        bot.tenant,
        WorkflowStart(mode="live", regenerate_from=bot.job.id, owner_feedback="Use softer colors"),
        "regenerate-execute",
    )
    process_job(
        bot.repo, bot.assets, bot.repo.claim("worker"), "worker", factory, creative_producer=None
    )
    finished = bot.repo.job(bot.tenant, new.id)
    assert finished.state == "completed"
    assert finished.checkpoint["campaign"]["output"] == new.input["selected_campaign"]
    assert finished.counters == {}


def test_notifications_api_is_authenticated_and_hides_internal_state(bot):
    from fastapi.testclient import TestClient

    from goldcoast.api.studio_app import create_app
    from goldcoast.api.studio_auth import authenticated

    app = create_app(settings=bot.settings, sessions=bot.repo.sessions)
    with TestClient(app) as client:
        assert client.get("/api/v2/notifications").status_code == 401
        app.dependency_overrides[authenticated] = lambda: SimpleNamespace(tenant_id=bot.tenant)
        assert client.get("/api/v2/notifications/config").json() == {"configured": True}
        view = client.get("/api/v2/notifications").json()
        assert view["chat_id"] == 42 and "pending" not in view and "test-secret" not in str(view)
        assert (
            client.put("/api/v2/notifications", json={"enabled": False}).json()["enabled"] is False
        )
        assert (
            client.put("/api/v2/notifications", json={"enabled": True, "chat_id": 55}).status_code
            == 422
        )
        assert len(client.post("/api/v2/notifications/telegram/link").json()["code"]) == 8
        assert client.delete("/api/v2/notifications/telegram").status_code == 200
        assert client.get("/api/v2/notifications").json() is None


def test_unconfigured_bot_never_calls_transport(bot):
    bot.settings.telegram_token = ""
    count = len(bot.calls)
    bot.service.notify_job(bot.job)
    bot.service.handle(callback(bot, "r:" + bot.job.id))
    TelegramPoller(bot.service).tick()
    assert len(bot.calls) == count
    with pytest.raises(Conflict, match="not configured"):
        bot.service.link(bot.tenant)


def test_overlong_feedback_keeps_prompt_and_no_allowance_is_consumed(bot):
    before = bot.repo.tenant(bot.tenant).campaign_grants
    bot.service.handle(callback(bot, "r:" + bot.job.id))
    prompt = next(iter(bot.service.current(bot.tenant).pending.values()))
    bot.service.handle(reply(bot, prompt, "x" * 501))
    assert bot.service.current(bot.tenant).pending
    assert bot.repo.tenant(bot.tenant).campaign_grants == before
    assert "500 characters" in bot.calls[-1][1]["text"]


def test_replay_resets_telegram_decision_provenance(bot):
    bot.service.handle(callback(bot, f"d:{bot.creative['id']}:1:approved"))
    job = start_campaign(
        bot.repo, bot.assets, bot.tenant, WorkflowStart(replay_source=bot.job.id), "replay-telegram"
    )
    process_job(
        bot.repo,
        bot.assets,
        bot.repo.claim("replayer"),
        "replayer",
        lambda *_: pytest.fail("Provider constructed"),
    )
    rows = CreativeService(bot.repo, bot.assets).list(bot.tenant, job.id)
    assert len(rows) == 1 and rows[0]["data"]["decided_via"] == "studio"
    assert rows[0]["data"]["decision"] == "pending"
    assert bot.repo.job(bot.tenant, job.id).counters == {}


def test_completed_job_stays_completed_when_photo_delivery_fails(bot, monkeypatch):
    monkeypatch.setattr(StudioSettings, "from_env", classmethod(lambda cls: bot.settings))

    def fail(*args, **kwargs):
        raise TelegramError("offline")

    monkeypatch.setattr(TelegramClient, "send_photo", fail)

    async def producer(
        repo, assets, job, snapshot, result, runtime, client, settings, stages, root
    ):
        artifact = bot.artifact.model_copy(update={"job_id": job.id})
        creative = CreativeService(repo, assets).save(bot.tenant, artifact, png((1080, 1440)))
        await stages.run("creative_result", lambda: {"passing_creative_ids": [creative["id"]]})

    job = start_campaign(
        bot.repo,
        bot.assets,
        bot.tenant,
        WorkflowStart(mode="live", creative_type="product"),
        "complete-outage",
    )
    process_job(
        bot.repo,
        bot.assets,
        bot.repo.claim("worker"),
        "worker",
        factory,
        creative_producer=producer,
    )
    assert bot.repo.job(bot.tenant, job.id).state == "completed"
    events = bot.repo.events(bot.tenant, job.id)
    assert events[-1].type == "notification_failed"
    assert any(e.type == "run_completed" for e in events)


def test_delivery_caps_previews_and_includes_summary(bot):
    ids = [bot.creative["id"]]
    raw = bot.assets.get(bot.tenant, ids[0])
    for _ in range(6):
        row = CreativeService(bot.repo, bot.assets).save(
            bot.tenant, bot.artifact.model_copy(deep=True), raw
        )
        ids.append(row["id"])
    with bot.repo.sessions.begin() as session:
        job = session.get(Job, bot.job.id)
        checkpoint = copy.deepcopy(job.checkpoint)
        checkpoint["creative_result"]["output"]["passing_creative_ids"] = ids
        job.checkpoint = checkpoint
    bot.service.notify_job(bot.repo.job(bot.tenant, bot.job.id))
    assert len([c for c in bot.calls if c[0] == "sendPhoto"]) == 6
    assert "7 passing creatives" in bot.calls[-1][1]["text"]


def test_rejecting_an_expired_creative_alerts_without_prompt(bot):
    row = bot.repo.get(bot.tenant, "creative", bot.creative["id"])
    value = {**row.data, "expires_at": "2000-01-01T00:00:00Z"}
    row = bot.repo.put(bot.tenant, "creative", value, row.id, row.version)
    before = len([c for c in bot.calls if c[0] == "sendMessage"])
    bot.service.handle(callback(bot, f"d:{row.id}:{row.version}:rejected"))
    assert not bot.service.current(bot.tenant).pending
    assert len([c for c in bot.calls if c[0] == "sendMessage"]) == before
    assert any(c[0] == "answerCallbackQuery" and c[1]["show_alert"] for c in bot.calls)


@pytest.mark.parametrize("social", [True, False])
def test_directors_and_refinement_receive_owner_feedback(bot, monkeypatch, social):
    from goldcoast.studio.compositor import SIZES
    from goldcoast.studio.creative import produce_creatives
    from goldcoast.studio.workflow import CampaignResult, Stages, VideoEvidence

    payload = {**bot.job.input, "owner_feedback": "Use warmer lighting"}
    if not social:
        payload.pop("creative_type")
    job = bot.repo.create_job(bot.tenant, "campaign", "live", "feedback", payload)
    job = bot.repo.claim("producer")
    snapshot = Snapshot.model_validate(job.input["snapshot"])
    result = CampaignResult.model_validate(bot.job.checkpoint["campaign"]["output"])
    stages = Stages(bot.repo, job, "producer")
    frame = bot.repo.put(
        bot.tenant,
        "campaign_frame",
        {"job_id": job.id, "source_asset_id": "source-video", "mime": "image/png"},
    )
    bot.assets.put(bot.tenant, frame.id, png())
    video = VideoEvidence(
        asset_id="source-video",
        title="Boba launch",
        description="A finished boba tea on the counter.",
        subject="Boba tea",
        observations="The complete drink is centered.",
        search_queries=["Los Angeles boba today"],
        uncertainty="Flavor is not visible.",
        best_frame_s=1.5,
        frame_reason="The full cup is clear.",
        frame_asset_id=frame.id,
    ).model_dump(mode="json")
    stages.data["video_evidence"] = {"state": "completed", "output": video}
    images = []

    class Runtime:
        async def run(self, name, instructions, context, output):
            assert name == ("social_director" if social else "creative_director")
            assert context["owner_feedback"] == "Use warmer lighting"
            assert "preserving verified facts" in instructions
            assert "local_signals" in context and context["local_signals"]["available"] is False
            assert context["campaign_video"] == video
            assert "weather_influence" in output.model_json_schema()["required"]
            assert "stronger selected idea" in instructions
            return bot.artifact.brief

    class Client:
        judges = 0

        def generate_image(self, stage, model, parts, config, output_path, input_refs):
            assert frame.id in input_refs
            assert any(isinstance(part, str) and "CAMPAIGN VIDEO FRAME" in part for part in parts)
            images.append((stage, parts[0]))
            output_path.parent.mkdir(exist_ok=True, parents=True)
            output_path.write_bytes(png())
            return SimpleNamespace(image_path=output_path)

        def generate(self, *args, **kwargs):
            self.judges += 1
            from goldcoast.studio.creative import JUDGE_RUBRIC

            assert args[2][0].startswith(JUDGE_RUBRIC)
            context = json.loads(args[2][0].split("Context: ", 1)[1])
            assert context["brand"] == snapshot.brand.model_dump(mode="json")
            assert context["selected"] == result.selected.model_dump(mode="json")
            assert context["campaign_video"] == video
            assert args[2][1].inline_data.mime_type == "image/png"
            assert "score_reasons" in args[3].response_json_schema["required"]
            verdict = bot.artifact.verdict.model_copy(
                update={"visual_quality": 5 if self.judges == 1 else 8}
            )
            return SimpleNamespace(response_text=judged_json(verdict))

    async def render(profile, kit, brief, background, placement, logo, font):
        return png(SIZES[placement])

    monkeypatch.setattr(
        "goldcoast.studio.social.render_social",
        lambda profile, kit, brief, pictures, placement, logo, font: png(SIZES[placement]),
    )
    ids = asyncio.run(
        produce_creatives(
            bot.repo,
            bot.assets,
            job,
            snapshot,
            result,
            Runtime(),
            Client(),
            SimpleNamespace(image_model="fixture", judge_model="fixture"),
            stages,
            bot.root,
            renderer=render,
        )
    )
    assert len(ids) == 2
    refinement = next(
        prompt
        for stage, prompt in images
        if stage == ("social_refinement" if social else "studio_image_landscape")
    )
    assert refinement.startswith("Owner feedback (preserve verified facts): Use warmer lighting")
    checkpoint = bot.repo.job(bot.tenant, job.id).checkpoint
    assert checkpoint["notification_ready"]["output"]["creative_ids"] == ids
