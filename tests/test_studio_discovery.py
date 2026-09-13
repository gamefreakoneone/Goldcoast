import json
from datetime import UTC, datetime, timedelta

import pytest

from goldcoast.llm.recordings import ReplayMissError
from goldcoast.studio.discovery import Discovery, ProviderCassette
from goldcoast.studio.graph import EvidenceSource, GraphClaim, build_graph, canonical_url


def fixture_transport(provider, operation, payload):
    assert provider == "tavily"
    if operation == "search":
        assert payload["search_depth"] == "basic"
        return {
            "results": [
                {
                    "title": "Evening market",
                    "url": "https://events.example/market?utm_source=test",
                    "content": "The neighborhood market opens at 5 pm on Saturday.",
                }
            ]
        }
    return {
        "results": [
            {
                "url": payload["urls"][0],
                "raw_content": (
                    "The neighborhood market opens at 5 pm on Saturday. Admission is free."
                ),
            }
        ]
    }


def test_search_extract_and_exact_offline_replay(tmp_path):
    used = []
    live = Discovery(ProviderCassette(tmp_path / "live", used.append), transport=fixture_transport)
    sources = live.search("Los Angeles neighborhood market September 2026")
    source = live.extract(sources[0]["url"])[0]
    assert "Admission is free" in source["text"]
    assert len(live.sources) == 1
    assert used == ["search", "extract"]
    live.search("Los Angeles neighborhood market September 2026")
    assert used == ["search", "extract"]

    def forbidden(*args):
        raise AssertionError("Replay reached a live provider boundary")

    replay = Discovery(
        ProviderCassette(tmp_path / "replayed", forbidden, tmp_path / "live"), transport=forbidden
    )
    assert replay.search("Los Angeles neighborhood market September 2026") == sources
    assert replay.extract(sources[0]["url"])[0] == source
    with pytest.raises(ReplayMissError):
        replay.search("a different request")


def test_incomplete_provider_record_is_never_reissued(tmp_path):
    cassette = ProviderCassette(tmp_path, lambda _: None)

    def failure():
        raise TimeoutError("not logged")

    with pytest.raises(RuntimeError):
        cassette.call("tavily", "search", {"query": "x"}, failure)
    record = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert record["status"] == "failed"
    with pytest.raises(ReplayMissError):
        cassette.call("tavily", "search", {"query": "x"}, lambda: pytest.fail("retried"))


def test_extraction_is_confined_to_known_public_sources(tmp_path):
    discovery = Discovery(ProviderCassette(tmp_path, lambda _: pytest.fail("reserved")))
    for url in [
        "http://127.0.0.1/a",
        "http://localhost/a",
        "file:///secret",
        "https://a.internal/x",
        "https://user:password@public.example/a",
        "https://public.example:9000/a",
        "https://not-discovered.example/a",
    ]:
        with pytest.raises(ValueError):
            discovery.extract(url)
    assert (
        canonical_url("https://example.com/a?utm_source=x&b=2#top") == "https://example.com/a?b=2"
    )
    assert (
        discovery.local_events("LA", "2026-09-13T00:00:00Z", "2026-09-14T00:00:00Z")["available"]
        is False
    )


def test_supported_deduplicated_conflicting_and_stale_graph():
    now = datetime.now(UTC)
    sources = [
        EvidenceSource(
            id=str(i),
            url=f"https://source{i}.example/event",
            title="Event",
            text=text,
            provider="tavily",
            retrieved_at=now,
            expires_at=now + timedelta(hours=1),
            content_hash="hash",
        )
        for i, text in enumerate(["The market opens at 5 pm.", "The market opens at 6 pm."])
    ]
    first = GraphClaim(
        subject="Market",
        predicate="opening time",
        value="5 pm",
        source_id="0",
        quote=sources[0].text,
    )
    second = GraphClaim(
        subject="market",
        predicate="opening time",
        value="6 pm",
        source_id="1",
        quote=sources[1].text,
    )
    assert len(build_graph(sources, [first, first], now).edges) == 1
    graph = build_graph(sources, [first, second], now)
    assert {edge.state for edge in graph.edges} == {"disputed"}
    assert {
        edge.state for edge in build_graph(sources, [first], now + timedelta(hours=2)).edges
    } == {"stale"}
    with pytest.raises(ValueError, match="verbatim"):
        build_graph(sources, [first.model_copy(update={"quote": "an invented source quote"})], now)
    with pytest.raises(ValueError, match="verbatim"):
        build_graph(sources, [first.model_copy(update={"source_id": "invented"})], now)
