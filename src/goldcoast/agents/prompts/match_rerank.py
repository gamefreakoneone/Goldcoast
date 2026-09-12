from pydantic import Field

from goldcoast.models.pipeline import ContractModel


class RankedBusiness(ContractModel):
    business_id: str
    match_reason: str
    score: float = Field(ge=0, le=1)
    headline_direction: str


class Ranking(ContractModel):
    businesses: list[RankedBusiness]


RERANK_PROMPT = """Rank only the supplied eligible local businesses for this hype
moment and athlete. Return each supplied business once, in best-first order, with
a one-sentence match reason grounded in the overlap tags, score from 0 to 1, and
a concise headline direction. You cannot add businesses. Use only facts in the
athlete's supplied profile. This is interest-based local discovery, not endorsement.
Never imply the athlete endorses, recommends, loves eating at, visits, or has a
relationship with a business. Acceptable: 'Inspired by a love of sushi, discover
fresh flavors nearby.' Unacceptable: 'Simone recommends Yama' or 'She visits Prime
Pizza after every meet'. Do not invent offers, promotions, visits, or favorites.
"""
