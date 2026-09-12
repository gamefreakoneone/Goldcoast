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
Make the headline direction creative and athlete-led rather than generic restaurant
advertising: connect the observed moment to a documented taste, then invite the
visitor's curiosity. Include the athlete's name and the overlapping interest.
Propose a punchy headline of at most five words plus a short discovery line.
Example: 'Big cheers. Fresh discoveries. Simone loves sushi. Ready to explore your
next favorite nearby?' For pizza, connect her documented pepperoni-pizza interest
to exploring a local slice. Her interest is not a recommendation of the business.
Never infer a gold medal, victory, record, or competition result from celebration
alone. Only describe the supplied moment. Any supplied 'Demo offer' is fictional
demo copy; preserve that qualifier, amount, and ticket condition verbatim.
"""
