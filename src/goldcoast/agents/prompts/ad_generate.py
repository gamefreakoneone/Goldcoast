import json

from goldcoast.models.pipeline import AD_FORMAT_SIZES, AdBrief, AdFormat, HypeMoment
from goldcoast.models.seed import AdStyle, Athlete, Business


def build_ad_prompt(
    brief: AdBrief,
    moment: HypeMoment,
    athlete: Athlete,
    business: Business,
    style: AdStyle,
    fmt: AdFormat,
    hints: list[str] | None = None,
    *,
    without_portrait: bool = False,
) -> str:
    width, height = AD_FORMAT_SIZES[fmt]
    ratio = "16:9" if fmt == AdFormat.LANDSCAPE else "9:16"
    instruction = (
        f"Compose a finished {fmt.value} local-discovery ad for Olympic visitors in LA. "
        f"Output exactly {width}x{height} pixels, aspect ratio {ratio}. "
        "Use the real hero frame as the photographic background. Keep the athlete as captured; "
        "never redraw, invent, distort, or replace the athlete's face. "
        "When the face is clear in the hero frame, use the portrait only for identity consistency. "
        "Otherwise place the supplied portrait as a foreground cutout, with the business product "
        "visual beside it. Use the supplied product reference when present. "
        "This is interest-based discovery: never state or imply the athlete endorses, recommends, "
        "or visits the business. Use only supplied profile facts. Follow headline_direction; "
        "do not turn it into an endorsement. Keep the business name, tagline/offer, and CTA "
        "verbatim and legible, and preserve the supplied logo. Render all text in the image. "
        "Leave safe margins for critical text and keep the athlete and product visible. "
    )
    if without_portrait:
        instruction += (
            "No separate portrait is supplied. The hero frame is the ad's photographic base; "
            "compose around this existing photograph without creating a new likeness. "
        )
    if business.offer_text is None:
        instruction += (
            "There is no promotion: the supplied offer_text is a tagline. No offer language. "
        )
    return (
        instruction
        + "\n"
        + json.dumps(
            {
                "moment": moment.description,
                "athlete": athlete.model_dump(mode="json"),
                "business": business.model_dump(mode="json"),
                "headline_direction": brief.headline_direction,
                "verbatim_text": [business.name, brief.offer_text, brief.cta],
                "style": style.model_dump(mode="json"),
                "layout": style.layout_notes[fmt],
                "regeneration_hints": hints or [],
            }
        )
    )
