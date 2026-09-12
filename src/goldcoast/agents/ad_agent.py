from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from goldcoast.agents.prompts.ad_generate import build_ad_prompt
from goldcoast.data import SeedData
from goldcoast.llm.client import LLMCallError
from goldcoast.media.images import (
    AssetMissingError,
    check_dimensions,
    load_image_part,
    resize_to_format,
    save_png,
)
from goldcoast.models.pipeline import AdBrief, AdFormat, AdMetadata, GeneratedAd, HypeMoment
from goldcoast.settings import Settings
from goldcoast.storage import write_json


class AdGenerationError(RuntimeError):
    pass


def brief_key(brief_id: str) -> str:
    return hashlib.sha256(brief_id.encode()).hexdigest()[:12]


class AdAgent:
    def __init__(self, client: Any, seed: SeedData, settings: Settings, output_dir: Path):
        self.client, self.seed, self.settings, self.output_dir = client, seed, settings, output_dir
        self.errors: list[str] = []

    def generate(
        self,
        brief: AdBrief,
        moment: HypeMoment,
        attempt: int = 1,
        hints: list[str] | None = None,
    ) -> list[GeneratedAd]:
        self.errors = []
        results = []
        for fmt in brief.formats:
            try:
                results.append(self.generate_one(brief, moment, fmt, attempt, hints))
            except AdGenerationError as exc:
                self.errors.append(f"{brief.id}/{fmt}: {exc}")
        if not results:
            raise AdGenerationError("; ".join(self.errors))
        return results

    def generate_one(
        self,
        brief: AdBrief,
        moment: HypeMoment,
        fmt: AdFormat,
        attempt: int = 1,
        hints: list[str] | None = None,
    ) -> GeneratedAd:
        if brief.moment_id != moment.id or brief.run_id != moment.run_id:
            raise ValueError("Brief and moment must belong to the same run and moment")
        if fmt not in brief.formats or attempt < 1:
            raise ValueError("Invalid brief format or attempt")
        athlete = self.seed.athletes[brief.athlete_id]
        business = self.seed.businesses[brief.business_id]
        style = self.seed.ad_styles[brief.ad_style_id]
        assets = self.settings.data_dir / "assets"
        refs = {
            "Hero frame, photographic background": moment.best_frame_path,
            "Athlete portrait, identity reference": assets / athlete.headshot
            if athlete.headshot
            else None,
            "Business logo": assets / business.logo,
        }
        if business.reference_photos:
            refs["Business product reference"] = assets / business.reference_photos[0]
        for label, path in refs.items():
            if path is None or not path.is_file():
                raise AssetMissingError(f"{athlete.id}/{business.id}: missing {label}: {path}")
        image_parts = {label: load_image_part(path) for label, path in refs.items()}
        path = (
            self.output_dir
            / "ads"
            / business.id
            / f"brief_{brief_key(brief.id)}"
            / fmt.value
            / f"attempt_{attempt}.png"
        )
        metadata = AdMetadata()
        no_image_retry = False
        ratio_retry = False
        extra_hints = list(hints or [])
        while True:
            prompt = build_ad_prompt(
                brief,
                moment,
                athlete,
                business,
                style,
                fmt,
                extra_hints,
                without_portrait=metadata.portrait_omitted,
            )
            parts: list[Any] = [prompt]
            input_refs = []
            for label, part in image_parts.items():
                if metadata.portrait_omitted and label.startswith("Athlete portrait"):
                    continue
                parts.extend([label, part])
                input_refs.append(str(refs[label]))
            try:
                call = self.client.generate_image(
                    "ad_generate",
                    self.settings.image_model,
                    parts,
                    {
                        "response_modalities": ["IMAGE"],
                        "image_config": {
                            "aspect_ratio": "16:9" if fmt == AdFormat.LANDSCAPE else "9:16",
                        },
                        "automatic_function_calling": {"disable": True},
                    },
                    output_path=path,
                    input_refs=input_refs,
                )
            except LLMCallError as exc:
                raise AdGenerationError(str(exc)) from exc
            if call.image_path is None:
                if no_image_retry:
                    raise AdGenerationError(call.refusal)
                no_image_retry = True
                if re.search(
                    r"person|people|likeness|celebrity|athlete|recogniz", call.refusal, re.I
                ):
                    metadata.portrait_omitted = True
                extra_hints.append("Return the finished image, not a textual explanation.")
                continue
            dimensions = check_dimensions(path, fmt)
            if not dimensions.correct_ratio and not ratio_retry:
                ratio_retry = True
                extra_hints.append(
                    "CRITICAL: previous output had the wrong ratio. Fill the exact canvas."
                )
                continue
            metadata.format_mismatch = not dimensions.correct_ratio
            if dimensions.correct_ratio and not dimensions.exact:
                metadata.resized_from = dimensions.size
                resize_to_format(path, fmt)
            else:
                with Image.open(path) as image:
                    save_png(image.convert("RGB"), path)
            ad = GeneratedAd(
                id=f"{brief.id}-{fmt.value}-attempt-{attempt}",
                run_id=brief.run_id,
                brief_id=brief.id,
                business_id=brief.business_id,
                format=fmt,
                attempt=attempt,
                image_path=path,
                prompt_used=prompt,
                model_id=call.record.model_id,
                created_at=datetime.now(UTC),
                metadata=metadata,
            )
            write_json(path.with_suffix(".json"), ad)
            return ad
