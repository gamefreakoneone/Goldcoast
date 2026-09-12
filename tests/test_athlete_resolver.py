from dataclasses import replace

import pytest

from goldcoast.matching.athlete_resolver import AthleteUnresolvedError, resolve_athlete
from goldcoast.models.pipeline import AthleteHints


def test_confident_alias_and_country_normalization(seed):
    result = resolve_athlete(AthleteHints(name="S. Biles", country="USA"), seed, sport="gymnastics")
    assert result.athlete_id == "simone-biles"
    assert result.confidence >= 0.8


def test_ambiguous_athletes_fail_with_candidate_scores(seed):
    duplicate = seed.athletes["simone-biles"].model_copy(update={"id": "other-athlete"})
    ambiguous = replace(seed, athletes={**seed.athletes, duplicate.id: duplicate})
    with pytest.raises(AthleteUnresolvedError, match="other-athlete"):
        resolve_athlete(AthleteHints(name="Simone"), ambiguous)


@pytest.mark.parametrize("hints", [AthleteHints(), AthleteHints(name="Unknown", country="USA")])
def test_unknown_or_insufficient_hints_fail(seed, hints):
    with pytest.raises(AthleteUnresolvedError):
        resolve_athlete(hints, seed, sport="gymnastics")
