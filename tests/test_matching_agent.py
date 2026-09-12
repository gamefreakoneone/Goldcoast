import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from goldcoast.agents.matching_agent import ENDORSEMENT, MatchingAgent
from goldcoast.llm.recordings import RecordedResponseClient
from goldcoast.matching.athlete_resolver import SeedLookupError
from goldcoast.matching.business_candidates import NoBusinessMatchError, candidate_businesses
from goldcoast.models.manifest import ClipEntry, ClipManifest
from goldcoast.models.pipeline import AdFormat, AthleteHints

FIXTURES = Path(__file__).parent / "fixtures/model_calls/match"


def test_real_match_and_curated_shortcut(seed, agent_settings, moment, tmp_path):
    moment.athlete_hints = AthleteHints(name="Unknown person")
    agent = MatchingAgent(
        RecordedResponseClient(FIXTURES, tmp_path / "calls"), seed, agent_settings, tmp_path
    )
    briefs = agent.match(moment)
    assert agent.resolved.confidence == 1
    assert len(briefs) == 2
    eligible = {c.business_id for c in candidate_businesses(seed.athletes["simone-biles"], seed)}
    for brief in briefs:
        assert brief.business_id in eligible
        assert brief.formats == [AdFormat.LANDSCAPE, AdFormat.PORTRAIT]
        assert brief.offer_text == seed.businesses[brief.business_id].tagline
        assert not ENDORSEMENT.search(brief.headline_direction)
        assert (tmp_path / "briefs" / f"{brief.id}.json").is_file()


def test_resolution_writes_manifest(seed, agent_settings, moment, tmp_path):
    moment.athlete_id = None
    ClipManifest(entries=[ClipEntry(file=moment.clip_path.name, notes="keep this")]).save(
        agent_settings.clip_manifest
    )
    MatchingAgent(
        RecordedResponseClient(FIXTURES, tmp_path / "calls"), seed, agent_settings, tmp_path
    ).match(moment)
    entry = ClipManifest.load(agent_settings.clip_manifest).get(moment.clip_path.name)
    assert entry.athlete_id == "simone-biles"
    assert entry.notes == "keep this"


def test_unknown_manifest_id_is_explicit(seed, agent_settings, moment, tmp_path):
    moment.athlete_id = "invented"
    with pytest.raises(SeedLookupError, match="gymnastics_simone.mp4"):
        MatchingAgent(None, seed, agent_settings, tmp_path).match(moment)


def test_no_candidates_never_calls_model(seed, agent_settings, moment, tmp_path):
    with pytest.raises(NoBusinessMatchError, match="ice_skating"):
        MatchingAgent(None, replace(seed, businesses={}), agent_settings, tmp_path).match(moment)


def test_invalid_ranking_and_style_fall_back(seed, agent_settings, moment, tmp_path):
    calls = []

    class InvalidClient:
        def generate(self, stage, *args, **kwargs):
            calls.append(stage)
            return SimpleNamespace(response_text="not JSON")

    briefs = MatchingAgent(InvalidClient(), seed, agent_settings, tmp_path).match(moment)
    expected = candidate_businesses(seed.athletes["simone-biles"], seed)[:2]
    assert [b.business_id for b in briefs] == [c.business_id for c in expected]
    assert all(b.match_reason.startswith("Shared tags:") for b in briefs)
    assert all(b.ad_style_id == "electric-finish" for b in briefs)
    assert calls == ["match_rerank", "match_rerank", "match_style", "match_style"]


def test_hallucinations_and_endorsement_are_rejected(seed, agent_settings, moment, tmp_path):
    class InvalidClient:
        def generate(self, stage, *args, **kwargs):
            response = {"ad_style_id": "invented", "reason": "test"}
            if stage == "match_rerank":
                response = {
                    "businesses": [
                        {
                            "business_id": "invented",
                            "match_reason": "invented",
                            "score": 1,
                            "headline_direction": "invented",
                        },
                        {
                            "business_id": "prime-pizza-little-tokyo",
                            "match_reason": "pizza",
                            "score": 0.9,
                            "headline_direction": "Simone recommends Prime Pizza",
                        },
                    ]
                }
            return SimpleNamespace(response_text=json.dumps(response))

    briefs = MatchingAgent(InvalidClient(), seed, agent_settings, tmp_path).match(moment)
    assert briefs[0].business_id == "prime-pizza-little-tokyo"
    assert all(b.business_id in seed.businesses for b in briefs)
    assert all(not ENDORSEMENT.search(b.headline_direction) for b in briefs)
    assert all(b.ad_style_id == "electric-finish" for b in briefs)
