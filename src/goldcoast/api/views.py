from pathlib import Path

from fastapi import HTTPException

from goldcoast.agents.ad_agent import brief_key
from goldcoast.api.paths import clip_url, media_url, safe_path
from goldcoast.api.schemas import AdAttempt, AdView, AdWithVerdict, MomentView
from goldcoast.models.pipeline import GeneratedAd, HypeMoment, PipelineEvent, QualityVerdict, Run
from goldcoast.pipeline.events import EventBus
from goldcoast.pipeline.run_store import RunStore


def ad_view(store: RunStore, ad: GeneratedAd) -> AdView:
    root = store.run_dir(ad.run_id)
    try:
        relative = ad.image_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise HTTPException(409, "Ad image is outside its run") from exc
    safe_path(root, relative)
    return AdView(**ad.model_dump(), image_url=media_url(ad.run_id, relative))


def moment_view(moment: HypeMoment) -> MomentView:
    return MomentView(
        **moment.model_dump(),
        best_frame_url=(
            media_url(moment.run_id, f"frames/{moment.id}.png") if moment.best_frame_path else None
        ),
        clip_url=clip_url(moment.clip_path.name),
    )


def matching_verdict(ad: GeneratedAd, verdicts: list[QualityVerdict]) -> QualityVerdict | None:
    return next(
        (
            v
            for v in verdicts
            if v.ad_id == ad.id and v.run_id == ad.run_id and v.attempt == ad.attempt
        ),
        None,
    )


def final_ads(store: RunStore, run: Run) -> list[AdWithVerdict]:
    ads = store.ads(run.id)
    by_id = {ad.id: ad for ad in ads}
    verdicts = store.verdicts(run.id)
    decisions = {decision.ad_id: decision for decision in store.decisions(run.id)}
    errors = {
        event.payload["final_ad"]["id"]: event.payload.get("errors", [])
        for event in EventBus(store.run_dir(run.id)).backlog()
        if event.type == "ad_final"
    }
    result = []
    for identifier in run.ad_ids:
        ad = by_id.get(identifier)
        if ad is None or ad.run_id != run.id:
            raise HTTPException(409, "Final ad artifact missing or inconsistent")
        verdict = matching_verdict(ad, verdicts)
        if verdict is None:
            raise HTTPException(409, "Final ad has no matching verdict")
        attempts = [
            AdAttempt(
                ad=ad_view(store, attempt),
                verdict=matching_verdict(attempt, verdicts),
                is_final=attempt.id == identifier,
            )
            for attempt in sorted(ads, key=lambda item: item.attempt)
            if attempt.brief_id == ad.brief_id and attempt.format == ad.format
        ]
        result.append(
            AdWithVerdict(
                **ad_view(store, ad).model_dump(),
                verdict=verdict,
                decision=decisions.get(identifier),
                attempts=attempts,
                errors=errors.get(identifier, []),
            )
        )
    return result


def event_view(event: PipelineEvent) -> PipelineEvent:
    def enrich(value):
        if isinstance(value, list):
            return [enrich(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: enrich(item) for key, item in value.items()}
        if "image_path" in value and "brief_id" in value:
            relative = (
                f"ads/{value['business_id']}/brief_{brief_key(value['brief_id'])}/"
                f"{value['format']}/attempt_{value['attempt']}.png"
            )
            result["image_url"] = media_url(event.run_id, relative)
        if "best_frame_path" in value and "best_frame_s" in value:
            result["best_frame_url"] = (
                media_url(event.run_id, f"frames/{value['id']}.png")
                if value["best_frame_path"]
                else None
            )
            result["clip_url"] = clip_url(Path(value["clip_path"].replace("\\", "/")).name)
        return result

    return event.model_copy(update={"payload": enrich(event.payload)})
