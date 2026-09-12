from fastapi import APIRouter

from goldcoast.api.deps import SeedDep
from goldcoast.models.seed import AdStyle, Athlete, Business

router = APIRouter()


@router.get("/seed/athletes", response_model=list[Athlete])
def athletes(seed: SeedDep):
    return list(seed.athletes.values())


@router.get("/seed/businesses", response_model=list[Business])
def businesses(seed: SeedDep):
    return list(seed.businesses.values())


@router.get("/seed/ad-styles", response_model=list[AdStyle])
def ad_styles(seed: SeedDep):
    return list(seed.ad_styles.values())
