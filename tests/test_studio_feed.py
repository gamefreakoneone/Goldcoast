from datetime import UTC, datetime, timedelta

import pytest
from test_studio_foundation import foundation as foundation
from test_studio_workflow import campaign as campaign

from goldcoast.studio.feed import FeedRequest, FeedResult, current_feed, selected_idea, start_feed
from goldcoast.studio.graph import build_graph
from goldcoast.studio.repository import AccessError, Conflict
from goldcoast.studio.workflow import Candidate, snapshot_business, validate_candidates


def test_feed_budget_cache_and_tenant_isolation(campaign):
    repo, assets, tenant, other, _ = campaign
    repo.grant(tenant, 0, 0, feed=1)
    repo.controls(feed=1)
    job = start_feed(repo, assets, tenant, FeedRequest(), "feed-one")
    repo.claim("worker")
    for _ in range(2):
        repo.reserve_call(tenant, job.id, "search", "worker")
    with pytest.raises(Conflict, match="allowance"):
        repo.reserve_call(tenant, job.id, "search", "worker")
    with pytest.raises(Conflict):
        repo.reserve_call(tenant, job.id, "image", "worker")
    snapshot = snapshot_business(repo, assets, tenant)
    now = datetime.now(UTC)
    idea = Candidate(
        id="latte",
        category="evergreen",
        title="Latte",
        angle="Enjoy a latte",
        product_name="Iced latte",
        source_ids=[],
        expires_at=now + timedelta(hours=6),
        fit=8,
        timeliness=0,
    )
    result = FeedResult(
        ideas=[idea],
        graph=build_graph([], []),
        retrieved_at=now,
        expires_at=now + timedelta(hours=6),
        rejected=[],
    )
    repo.checkpoint(
        tenant,
        job.id,
        "worker",
        {"feed": {"state": "completed", "output": result.model_dump(mode="json")}},
    )
    repo.finish(tenant, job.id, "completed", "worker")
    assert start_feed(repo, assets, tenant, FeedRequest(), "feed-two").id == job.id
    assert current_feed(repo, tenant, snapshot, "new topic") is None
    assert selected_idea(repo, tenant, snapshot, job.id, "latte").selected.id == "latte"
    with pytest.raises(AccessError):
        selected_idea(repo, other, snapshot, job.id, "latte")
    snapshot.business_version += 1
    assert current_feed(repo, tenant, snapshot, "") is None
    with pytest.raises(Conflict, match="changed"):
        selected_idea(repo, tenant, snapshot, job.id, "latte")


def test_past_event_is_not_recent_just_because_source_is_new(campaign):
    repo, assets, tenant, _, _ = campaign
    snapshot = snapshot_business(repo, assets, tenant)
    now = datetime.now(UTC)
    idea = Candidate(
        id="old-event",
        category="local",
        title="Old concert",
        angle="Coffee before concert",
        product_name="Iced latte",
        source_ids=[],
        event_date=(now - timedelta(days=2)).date(),
        expires_at=now + timedelta(hours=6),
        fit=8,
        timeliness=9,
    )
    valid, rejected = validate_candidates([idea], build_graph([], []), snapshot.profile, now)
    assert not valid
    assert rejected[0]["reason"] == "Event date has passed"


def test_failed_feed_remains_visible_after_reload_without_refresh(campaign):
    from goldcoast.studio.feed import latest_feed

    repo, assets, tenant, _, _ = campaign
    repo.grant(tenant, 0, 0, feed=1)
    repo.controls(feed=1)
    job = start_feed(repo, assets, tenant, FeedRequest(), "failed-feed")
    repo.claim("worker")
    repo.finish(tenant, job.id, "failed", "worker")
    snapshot = snapshot_business(repo, assets, tenant)
    assert latest_feed(repo, tenant, snapshot, "").id == job.id
    assert current_feed(repo, tenant, snapshot, "") is None
    assert latest_feed(repo, tenant, snapshot, "different topic") is None
    assert repo.tenant(tenant).feed_grants == 0
    assert repo.job(tenant, job.id).counters == {}


@pytest.mark.parametrize("code,phrase", [(400, "rejected"), (403, "denied access"), (429, "quota")])
def test_provider_failure_messages_explain_cause_without_raw_payload(code, phrase):
    from google.genai.errors import ClientError

    from goldcoast.studio.worker import failure_message

    error = ClientError(code, {"error": {"message": "private provider payload"}})
    message = failure_message(error)
    assert phrase in message
    assert "private provider payload" not in message
