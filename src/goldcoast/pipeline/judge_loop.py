from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field

from goldcoast.agents.ad_agent import AdAgent, AdGenerationError
from goldcoast.agents.judge_agent import JudgeAgent
from goldcoast.media.images import AssetMissingError
from goldcoast.models.pipeline import (
    AdBrief,
    AdFormat,
    ContractModel,
    GeneratedAd,
    HypeMoment,
    PipelineEventType,
    QualityVerdict,
)


class JudgedAd(ContractModel):
    final_ad: GeneratedAd
    final_verdict: QualityVerdict
    attempts: list[tuple[GeneratedAd, QualityVerdict]]
    errors: list[str] = Field(default_factory=list)


def judge_loop(
    ad_agent: AdAgent,
    judge_agent: JudgeAgent,
    brief: AdBrief,
    moment: HypeMoment,
    fmt: AdFormat,
    emit: Callable[[PipelineEventType, dict], Any] | None = None,
) -> JudgedAd:
    def publish(event: PipelineEventType, payload: dict) -> None:
        if emit:
            emit(event, payload)

    attempts = []
    hints: list[str] = []
    errors = []
    for attempt in range(1, judge_agent.settings.judge_max_retries + 2):
        publish(
            PipelineEventType.AD_GENERATING,
            {"brief_id": brief.id, "format": fmt, "attempt": attempt},
        )
        try:
            ad = ad_agent.generate_one(brief, moment, fmt, attempt, hints)
        except (AdGenerationError, AssetMissingError) as exc:
            if not attempts:
                raise
            errors.append(str(exc))
            break
        publish(PipelineEventType.AD_GENERATED, ad.model_dump(mode="json"))
        verdict = judge_agent.judge(ad, brief, moment)
        attempts.append((ad, verdict))
        publish(PipelineEventType.AD_JUDGED, verdict.model_dump(mode="json"))
        if verdict.passed:
            break
        hints = [
            *verdict.regeneration_hints,
            "Prior failures: "
            + "; ".join(f"attempt {v.attempt}: overall {v.scores.overall}" for _, v in attempts),
        ]
        if attempt <= judge_agent.settings.judge_max_retries:
            publish(
                PipelineEventType.AD_REGENERATING,
                {
                    "ad_id": ad.id,
                    "brief_id": brief.id,
                    "format": fmt,
                    "attempt": attempt + 1,
                    "hints": hints,
                },
            )
    ad, verdict = max(attempts, key=lambda pair: (pair[1].passed, pair[1].scores.overall))
    result = JudgedAd(final_ad=ad, final_verdict=verdict, attempts=attempts, errors=errors)
    publish(PipelineEventType.AD_FINAL, result.model_dump(mode="json"))
    return result
