from __future__ import annotations

from pydantic import Field

from goldcoast.data import SeedData
from goldcoast.models.pipeline import AthleteHints, ContractModel


class AthleteUnresolvedError(ValueError):
    pass


class SeedLookupError(ValueError):
    pass


class ResolvedAthlete(ContractModel):
    athlete_id: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]


def normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().replace(".", "").split())


def country(value: str | None) -> str:
    result = normalize(value)
    return "united states" if result in {"usa", "us", "united states of america"} else result


def resolve_athlete(
    hints: AthleteHints,
    seed: SeedData,
    *,
    sport: str | None = None,
    threshold: float = 0.6,
) -> ResolvedAthlete:
    scored = []
    for athlete in seed.athletes.values():
        evidence = []
        score = 0.0
        if hints.name and normalize(hints.name) in {
            normalize(name) for name in [athlete.name, *athlete.aliases]
        }:
            score += 0.65
            evidence.append("exact name or alias")
        if hints.country and country(hints.country) == country(athlete.country):
            score += 0.1
            evidence.append("country")
        if sport and normalize(sport) == normalize(athlete.sport):
            score += 0.1
            evidence.append("sport")
        if set(map(normalize, hints.kit_colors)) & set(
            map(normalize, athlete.identification.kit_colors)
        ):
            score += 0.075
            evidence.append("kit colors")
        if hints.bib_number and hints.bib_number == athlete.identification.bib_number:
            score += 0.075
            evidence.append("bib number")
        scored.append(
            ResolvedAthlete(
                athlete_id=athlete.id, confidence=min(1, round(score, 3)), evidence=evidence
            )
        )
    scored.sort(key=lambda result: (-result.confidence, result.athlete_id))
    if (
        not scored
        or scored[0].confidence < threshold
        or (len(scored) > 1 and scored[0].confidence - scored[1].confidence < 0.1)
    ):
        details = ", ".join(f"{r.athlete_id}={r.confidence:.3f}" for r in scored[:3])
        raise AthleteUnresolvedError(f"Athlete unresolved or ambiguous; candidates: {details}")
    return scored[0]
