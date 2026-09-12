from goldcoast.data import SeedData
from goldcoast.models.pipeline import ContractModel
from goldcoast.models.seed import Athlete


class NoBusinessMatchError(ValueError):
    pass


class Candidate(ContractModel):
    business_id: str
    overlap_tags: list[str]
    base_score: float


def tag(value: str) -> str:
    return "_".join(value.casefold().split())


def athlete_tags(athlete: Athlete) -> set[str]:
    return {
        tag(value)
        for value in [
            *athlete.interests,
            *(food.cuisine for food in athlete.favorite_foods),
            *(dish for food in athlete.favorite_foods for dish in food.dishes),
        ]
    }


def candidate_businesses(athlete: Athlete, seed: SeedData) -> list[Candidate]:
    tags = athlete_tags(athlete)
    priorities = {
        "restaurant": 6,
        "cafe": 5,
        "bar": 4,
        "sports_venue": 3,
        "experience": 2,
        "retail": 1,
    }
    candidates = []
    for business in seed.businesses.values():
        overlap = sorted(tags & {tag(t) for t in business.tags})
        if overlap:
            candidates.append(
                Candidate(
                    business_id=business.id,
                    overlap_tags=overlap,
                    base_score=min(1, 0.1 * len(overlap) + 0.001 * priorities[business.category]),
                )
            )
    return sorted(candidates, key=lambda c: (-c.base_score, c.business_id))
