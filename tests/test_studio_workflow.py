import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from test_studio_foundation import foundation as foundation

from goldcoast.studio.assets import LocalAssetStore
from goldcoast.studio.brand import BrandKit, BrandService, BusinessProfile, Product
from goldcoast.studio.discovery import Discovery, ProviderCassette
from goldcoast.studio.graph import EvidenceSource, GraphClaim, build_graph
from goldcoast.studio.repository import Conflict
from goldcoast.studio.worker import process_job
from goldcoast.studio.workflow import (
    Candidate,
    ChiefDecision,
    ScoutReport,
    SearchPlan,
    Stages,
    WorkflowStart,
    start_campaign,
    validate_candidates,
)


@pytest.fixture
def campaign(foundation):
    settings, _, repo, first, second = foundation
    assets = LocalAssetStore(settings.asset_root)
    service = BrandService(repo, assets)
    service.save(
        first.id,
        "business",
        BusinessProfile(
            name="Juniper",
            city="Los Angeles",
            confirmed=True,
            products=[Product(name="Iced latte")],
        ),
        0,
    )
    service.save(first.id, "brand", BrandKit(confirmed=True), 0)
    repo.controls(enabled=True)
    repo.grant(first.id, 3, 1)
    return repo, assets, first.id, second.id, settings.asset_root.parent


def factory(repo, assets, job, worker):
    now = datetime.now(UTC)
    discovery = Discovery(ProviderCassette(assets.root / "provider-test", lambda _: None))
    source = EvidenceSource(
        id="source",
        url="https://example.com/market",
        title="Local market",
        text="The neighborhood market opens this afternoon.",
        provider="tavily",
        retrieved_at=now,
        expires_at=now + timedelta(hours=1),
        content_hash="hash",
    )
    candidate = Candidate(
        id="local-market",
        category="local",
        title="A market-day coffee stop",
        angle="Invite neighbors to enjoy an iced latte before the market.",
        product_name="Iced latte",
        source_ids=["source"],
        expires_at=now + timedelta(hours=1),
        fit=9,
        timeliness=9,
    )

    class Runtime:
        async def run(self, name, instructions, payload, output, tools=None):
            repo.reserve_call(job.tenant_id, job.id, "model", worker)
            if name == "chief_planner":
                return SearchPlan(
                    local_queries=["market"],
                    cultural_queries=["coffee"],
                    strategy="Local relevance",
                )
            if name == "local_scout":
                assert [t.tool_spec["name"] for t in tools] == ["search_web", "extract_page"]
                discovery.sources[source.id] = source
                return ScoutReport(
                    summary="Local market found",
                    candidates=[candidate],
                    claims=[
                        GraphClaim(
                            subject="Neighborhood market",
                            predicate="time",
                            value="this afternoon",
                            source_id=source.id,
                            quote=source.text,
                        )
                    ],
                )
            if name == "culture_scout":
                return ScoutReport(summary="No reliable cultural angle")
            return ChiefDecision(
                candidate_id="local-market", rationale="Strong local fit and current evidence"
            )

    return Runtime(), discovery, None, SimpleNamespace(), lambda _: None, assets.root


def test_complete_workflow_and_provider_free_replay(campaign):
    repo, assets, tenant, _, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "start")
    assert start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "start").id == job.id
    claimed = repo.claim("worker")
    process_job(repo, assets, claimed, "worker", factory, creative_producer=None)
    finished = repo.job(tenant, job.id)
    assert finished.state == "completed"
    assert finished.counters == {"model": 4}
    assert finished.checkpoint["campaign"]["output"]["selected"]["id"] == "local-market"
    replay = start_campaign(repo, assets, tenant, WorkflowStart(replay_source=job.id), "replay")

    def forbidden(*args):
        pytest.fail("Replay constructed live providers")

    process_job(repo, assets, repo.claim("replayer"), "replayer", forbidden, creative_producer=None)
    assert repo.job(tenant, replay.id).state == "completed"
    assert repo.job(tenant, replay.id).counters == {}
    assert repo.tenant(tenant).campaign_grants == 2


def test_interrupted_stage_is_not_reissued(campaign):
    repo, assets, tenant, _, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "interrupted")
    job = repo.claim("worker")
    repo.checkpoint(tenant, job.id, "worker", {"chief_plan": {"state": "pending"}})
    process_job(repo, assets, repo.job(tenant, job.id), "worker", factory, creative_producer=None)
    assert repo.job(tenant, job.id).state == "failed"
    assert repo.job(tenant, job.id).counters == {}


def test_cancelled_stage_never_executes(campaign):
    repo, assets, tenant, _, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "cancel")
    job = repo.claim("worker")
    stages = Stages(repo, job, "worker")
    repo.finish(tenant, job.id, "cancelled")
    with pytest.raises(Conflict):
        asyncio.run(stages.run("should-not-run", lambda: pytest.fail("ran")))


def test_completed_stage_resumes_without_provider_call(campaign):
    repo, assets, tenant, _, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "resume")
    job = repo.claim("worker")
    stage = Stages(repo, job, "worker")
    assert asyncio.run(stage.run("one", lambda: {"answer": 3})) == {"answer": 3}
    resumed = Stages(repo, repo.job(tenant, job.id), "worker")
    assert asyncio.run(resumed.run("one", lambda: pytest.fail("repeated"))) == {"answer": 3}


def test_candidates_cannot_invent_products_or_sources():
    now = datetime.now(UTC)
    profile = BusinessProfile(name="Cafe", city="LA", products=[Product(name="Latte")])
    base = Candidate(
        id="idea",
        category="local",
        title="Coffee",
        angle="Coffee stop",
        product_name="Latte",
        source_ids=["invented"],
        expires_at=now + timedelta(hours=1),
        fit=8,
        timeliness=8,
    )
    valid, rejected = validate_candidates([base], build_graph([], []), profile, now)
    assert not valid and "Evidence" in rejected[0]["reason"]
    valid, rejected = validate_candidates(
        [base.model_copy(update={"product_name": "Pizza"})], build_graph([], []), profile, now
    )
    assert not valid and "Product" in rejected[0]["reason"]


def test_foreign_replay_is_inaccessible(campaign):
    from goldcoast.studio.repository import AccessError

    repo, assets, tenant, other, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "private")
    with pytest.raises(AccessError):
        start_campaign(repo, assets, other, WorkflowStart(replay_source=job.id), "foreign")


def test_unmatched_quote_is_excluded_without_stopping_campaign(campaign):
    repo, assets, tenant, _, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "bad-quote")

    def invalid_factory(*args):
        runtime, discovery, client, settings, reserve, root = factory(*args)
        original = runtime.run

        async def run(name, instructions, payload, output, tools=None):
            result = await original(name, instructions, payload, output, tools)
            if name == "local_scout":
                result.claims[0].quote = "A fabricated quote absent from the recorded page."
            if name == "chief_marketer":
                result.candidate_id = "evergreen-product"
            return result

        runtime.run = run
        return runtime, discovery, client, settings, reserve, root

    process_job(
        repo, assets, repo.claim("worker"), "worker", invalid_factory, creative_producer=None
    )
    finished = repo.job(tenant, job.id)
    assert finished.state == "completed"
    result = finished.checkpoint["campaign"]["output"]
    assert result["selected"]["category"] == "evergreen"
    assert not result["graph"]["edges"]
    assert any("quote did not match" in item["reason"] for item in result["rejected"])
