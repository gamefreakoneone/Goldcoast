from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from goldcoast.agents.prompts.judge_rubric import RUBRIC, CriterionScores, JudgeResponse
from goldcoast.agents.structured import AgentParseError, ModelSafetyError, structured_call
from goldcoast.data import SeedData
from goldcoast.llm.client import LLMCallError
from goldcoast.media.images import AssetMissingError, load_image_part
from goldcoast.models.pipeline import (
    AD_FORMAT_SIZES,
    AdBrief,
    GeneratedAd,
    HypeMoment,
    QualityVerdict,
    VerdictScores,
)
from goldcoast.settings import Settings
from goldcoast.storage import write_json


def score_verdict(scores: CriterionScores, settings: Settings) -> tuple[VerdictScores, bool]:
    values = scores.model_dump()
    overall = min(scores.business_accuracy, round(sum(values.values()) / 5))
    passed = (
        overall >= settings.judge_pass_threshold
        and min(values.values()) >= settings.judge_min_criterion
    )
    return VerdictScores(**values, overall=overall), passed


class JudgeAgent:
    def __init__(self, client: Any, seed: SeedData, settings: Settings, output_dir: Path):
        self.client, self.seed, self.settings, self.output_dir = client, seed, settings, output_dir

    def judge(self, ad: GeneratedAd, brief: AdBrief, moment: HypeMoment) -> QualityVerdict:
        if (
            ad.brief_id != brief.id
            or ad.business_id != brief.business_id
            or brief.moment_id != moment.id
        ):
            raise ValueError("Ad, brief, and moment references do not match")
        if len({ad.run_id, brief.run_id, moment.run_id}) != 1:
            raise ValueError("Ad, brief, and moment run IDs do not match")
        athlete = self.seed.athletes[brief.athlete_id]
        business = self.seed.businesses[brief.business_id]
        style = self.seed.ad_styles[brief.ad_style_id]
        assets = self.settings.data_dir / "assets"
        refs = {
            "Candidate ad to judge": ad.image_path,
            "Reference hero frame": moment.best_frame_path,
            "Reference athlete portrait": assets / athlete.headshot if athlete.headshot else None,
            "Reference business logo": assets / business.logo,
        }
        parts: list[Any] = []
        for label, path in refs.items():
            if path is None or not path.is_file():
                raise AssetMissingError(f"{athlete.id}/{business.id}: missing {label}: {path}")
            parts.extend([label, load_image_part(path)])
        with Image.open(ad.image_path) as image:
            observed_size = image.size
        parts.append(
            RUBRIC
            + json.dumps(
                {
                    "brief": brief.model_dump(mode="json"),
                    "business": business.model_dump(mode="json"),
                    "style": style.model_dump(mode="json"),
                    "athlete": athlete.model_dump(mode="json"),
                    "target_size": AD_FORMAT_SIZES[ad.format],
                    "observed_size": observed_size,
                    "metadata": ad.metadata.model_dump(),
                    "placement": "billboard" if ad.format == "landscape" else "reel",
                }
            )
        )
        try:
            result = structured_call(
                self.client,
                "judge_score",
                self.settings.judge_model,
                parts,
                JudgeResponse,
                input_refs=[str(path) for path in refs.values()],
            )
        except (AgentParseError, ModelSafetyError, LLMCallError) as exc:
            result = JudgeResponse(
                scores=CriterionScores(**dict.fromkeys(CriterionScores.model_fields, 0)),
                issues=[f"Judge failed: {exc}"],
                regeneration_hints=[
                    "Produce a clear, accurate discovery ad using only supplied facts."
                ],
            )
        if observed_size != AD_FORMAT_SIZES[ad.format] or ad.metadata.format_mismatch:
            result.scores.format_compliance = min(result.scores.format_compliance, 4)
            result.issues.append(
                f"format_compliance: observed dimensions {observed_size} do not meet target"
            )
            result.regeneration_hints.append(
                f"Use exact target dimensions {AD_FORMAT_SIZES[ad.format]}."
            )
        scores, passed = score_verdict(result.scores, self.settings)
        if not passed and not result.regeneration_hints:
            result.regeneration_hints.append(
                "Correct the lowest-scored criterion against the supplied rubric."
            )
        verdict = QualityVerdict(
            id=f"{ad.id}-verdict",
            run_id=ad.run_id,
            ad_id=ad.id,
            attempt=ad.attempt,
            scores=scores,
            passed=passed,
            issues=result.issues,
            regeneration_hints=result.regeneration_hints,
            model_id=self.settings.judge_model,
            created_at=datetime.now(UTC),
        )
        write_json(self.output_dir / "verdicts" / f"{ad.id}_attempt_{ad.attempt}.json", verdict)
        return verdict
