import json
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from test_studio_foundation import foundation as foundation
from test_studio_workflow import campaign as campaign
from test_studio_workflow import factory

from goldcoast.studio.brand import BusinessProfile, Product
from goldcoast.studio.discovery import Discovery, ProviderCassette, SignalsResult, weather_url
from goldcoast.studio.graph import build_graph, canonical_url
from goldcoast.studio.repository import Conflict
from goldcoast.studio.worker import process_job
from goldcoast.studio.workflow import Candidate, WorkflowStart, start_campaign, validate_candidates


def transport(day):
    def request(provider, operation, payload):
        assert provider == "weather"
        if operation == "geocode":
            assert payload == {"name": "Los Angeles", "count": 1}
            return {
                "results": [
                    {"latitude": 34.05, "longitude": -118.24, "timezone": "America/Los_Angeles"}
                ]
            }
        assert payload["date"] == str(day)
        assert payload["timezone"] == "America/Los_Angeles"
        return {
            "daily": {
                "time": [str(day)],
                "temperature_2m_max": [34],
                "temperature_2m_min": [21],
                "precipitation_probability_max": [5],
                "weather_code": [0],
                "uv_index_max": [9],
            }
        }

    return request


def test_weather_evidence_budget_cache_and_replay(tmp_path):
    day = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    used = []
    discovery = Discovery(
        ProviderCassette(tmp_path / "live", used.append), transport=transport(day)
    )
    output = discovery.local_signals("Los Angeles", "America/Los_Angeles", day)
    result = SignalsResult.model_validate(output)
    assert result.available and len(result.sources) == 1 and len(result.claims) == 4
    assert result.sources[0].provider == "weather"
    assert result.sources[0].url == canonical_url(result.sources[0].url)
    assert all(c.quote in result.sources[0].text for c in result.claims)
    assert "high 34°C" in result.summary[0]
    assert used == ["tool", "tool"]
    assert discovery.local_signals("Los Angeles", "America/Los_Angeles", day) == output
    assert used == ["tool", "tool"]
    records = [json.loads(p.read_text()) for p in (tmp_path / "live").glob("*.json")]
    assert {r["request"]["operation"] for r in records} == {"geocode", "forecast"}
    forecast = next(r for r in records if r["request"]["operation"] == "forecast")
    assert result.sources[0].url == weather_url("forecast", forecast["request"]["payload"])
    assert "date=" not in result.sources[0].url
    graph = build_graph(result.sources, result.claims)
    candidate = Candidate(
        id="heat",
        category="local",
        title="Cool down",
        angle="An iced latte on a hot day",
        product_name="Latte",
        source_ids=[result.sources[0].id],
        expires_at=datetime.now(UTC) + timedelta(days=1),
        fit=9,
        timeliness=9,
    )
    valid, rejected = validate_candidates(
        [candidate],
        graph,
        BusinessProfile(name="Cafe", city="Los Angeles", products=[Product(name="Latte")]),
        datetime.now(UTC),
    )
    assert len(valid) == 1 and not rejected
    assert valid[0].expires_at == result.sources[0].expires_at

    def forbidden(*args):
        pytest.fail("Replay reached provider or reservation")

    replay = Discovery(
        ProviderCassette(tmp_path / "replay", forbidden, tmp_path / "live"), transport=forbidden
    )
    assert replay.local_signals("Los Angeles", "America/Los_Angeles", day) == output


@pytest.mark.parametrize("day,offset", [(date(2026, 3, 8), -7), (date(2026, 11, 1), -8)])
def test_business_day_expiry_handles_dst(tmp_path, day, offset):
    discovery = Discovery(ProviderCassette(tmp_path, lambda _: None), transport=transport(day))
    result = SignalsResult.model_validate(
        discovery.local_signals("Los Angeles", "America/Los_Angeles", day)
    )
    deadline = result.sources[0].expires_at
    assert deadline.date() == day and deadline.hour == 23
    assert deadline.utcoffset() == timedelta(hours=offset)
    assert all(c.valid_until == deadline for c in result.claims)


@pytest.mark.parametrize("failure", ["empty", "timeout", "date", "null", "code"])
def test_unavailable_weather_is_safe_and_not_retried(tmp_path, failure):
    calls = []
    day = date(2026, 9, 13)

    def request(provider, operation, payload):
        calls.append(operation)
        if failure == "timeout":
            raise TimeoutError("secret provider details")
        if failure == "empty":
            return {"results": []}
        value = transport(day)(provider, operation, payload)
        if operation == "forecast":
            if failure == "date":
                value["daily"]["time"] = ["2000-01-01"]
            else:
                value["daily"]["weather_code" if failure == "code" else "temperature_2m_max"] = [
                    999 if failure == "code" else None
                ]
        return value

    discovery = Discovery(ProviderCassette(tmp_path, lambda _: None), transport=request)
    result = discovery.local_signals("Los Angeles", "America/Los_Angeles", day)
    assert not result["available"] and not result["claims"] and not result["sources"]
    before = len(calls)
    discovery.local_signals("Los Angeles", "America/Los_Angeles", day)
    assert len(calls) == before
    assert "secret" not in str(result)


def test_cancellation_is_not_swallowed(tmp_path):
    def reserve(_):
        raise Conflict("Cancelled")

    discovery = Discovery(
        ProviderCassette(tmp_path, reserve), transport=lambda *_: pytest.fail("Called")
    )
    with pytest.raises(Conflict, match="Cancelled"):
        discovery.local_signals("Los Angeles", "America/Los_Angeles", date.today())


def test_workflow_retains_signals_and_replays_without_providers(campaign):
    repo, assets, tenant, _, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "weather")

    def providers(*args):
        runtime, discovery, client, settings, reserve, root = factory(*args)
        discovery.transport = transport(date.fromisoformat(job.input["snapshot"]["local_date"]))
        discovery.cassette.reserve = lambda kind: repo.reserve_call(
            tenant, job.id, kind, "weather-worker"
        )
        original = runtime.run

        async def run(name, instructions, payload, output, tools=None):
            assert payload["signals"] and "high 34°C" in payload["signals"][0]
            return await original(name, instructions, payload, output, tools)

        runtime.run = run
        return runtime, discovery, client, settings, reserve, root

    process_job(
        repo,
        assets,
        repo.claim("weather-worker"),
        "weather-worker",
        providers,
        creative_producer=None,
    )
    finished = repo.job(tenant, job.id)
    assert finished.state == "completed"
    assert finished.counters == {"tool": 2, "model": 4}
    assert len(finished.checkpoint["campaign"]["output"]["graph"]["edges"]) == 5
    replay = start_campaign(
        repo, assets, tenant, WorkflowStart(replay_source=job.id), "weather-replay"
    )
    process_job(
        repo,
        assets,
        repo.claim("replayer"),
        "replayer",
        lambda *_: pytest.fail("Provider constructed"),
        creative_producer=None,
    )
    copied = repo.job(tenant, replay.id)
    assert copied.state == "completed" and copied.counters == {}
    assert copied.checkpoint["local_signals"] == finished.checkpoint["local_signals"]
    regenerated = start_campaign(
        repo,
        assets,
        tenant,
        WorkflowStart(mode="live", regenerate_from=job.id, owner_feedback="Cooler imagery"),
        "weather-regeneration",
    )

    def saved_providers(*args):
        values = factory(*args)
        values[1].local_signals = lambda *_: pytest.fail("Regeneration fetched fresh weather")
        return values

    process_job(
        repo,
        assets,
        repo.claim("revision"),
        "revision",
        saved_providers,
        creative_producer=None,
    )
    revised = repo.job(tenant, regenerated.id)
    assert revised.state == "completed"
    assert revised.checkpoint["local_signals"] == finished.checkpoint["local_signals"]
    assert revised.counters == {}


def test_weather_brief_contract_and_historical_compatibility():
    from types import SimpleNamespace

    from pydantic import ValidationError

    from goldcoast.studio.creative import CreativeBrief, GeneratedCreativeBrief, creative_signals

    old = dict(
        headline="Pause",
        subheading="A cool latte",
        cta="Visit today",
        product_name="Latte",
        image_prompt="A latte",
    )
    assert CreativeBrief.model_validate(old).weather_influence is None
    with pytest.raises(ValidationError):
        GeneratedCreativeBrief.model_validate(old)
    current = GeneratedCreativeBrief.model_validate(
        {**old, "weather_influence": {"influenced": True, "rationale": "Cold drink for a warm day"}}
    )
    assert current.weather_influence.influenced
    signals = SignalsResult(available=True, summary=["High 34 C"])
    stages = SimpleNamespace(data={"local_signals": {"output": signals.model_dump()}})
    assert creative_signals(stages) == signals.model_dump(mode="json")


def test_signals_api_is_additive_and_graph_route_stays_compatible(campaign):
    from types import SimpleNamespace

    from goldcoast.api.workflow_routes import graph, result

    repo, assets, tenant, _, _ = campaign
    job = start_campaign(repo, assets, tenant, WorkflowStart(mode="live"), "api-signals")
    process_job(repo, assets, repo.claim("worker"), "worker", factory, creative_producer=None)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(repo=repo)))
    identity = SimpleNamespace(tenant_id=tenant)
    output = result(job.id, request, identity)
    assert output["selected"]["id"] == "local-market"
    assert output["local_signals"]["available"] is False
    assert graph(job.id, request, identity) == output["graph"]


def test_product_campaign_skips_weather(campaign):
    repo, assets, tenant, _, _ = campaign
    job = start_campaign(
        repo, assets, tenant, WorkflowStart(mode="live", creative_type="product"), "no-weather"
    )

    def providers(*args):
        values = factory(*args)
        values[1].local_signals = lambda *_: pytest.fail("Product checked weather")
        return values

    process_job(repo, assets, repo.claim("worker"), "worker", providers, creative_producer=None)
    finished = repo.job(tenant, job.id)
    assert finished.state == "completed" and "local_signals" not in finished.checkpoint
