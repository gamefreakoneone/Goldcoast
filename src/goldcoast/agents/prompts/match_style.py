from goldcoast.models.pipeline import ContractModel


class StyleChoice(ContractModel):
    ad_style_id: str
    reason: str


STYLE_PROMPT = "Choose one supplied eligible ad style for this moment. Explain why."
