from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from goldcoast.agents.prompts.match_rerank import RERANK_PROMPT, RankedBusiness, Ranking
from goldcoast.agents.prompts.match_style import STYLE_PROMPT, StyleChoice
from goldcoast.agents.structured import AgentParseError, structured_call
from goldcoast.data import SeedData
from goldcoast.matching.athlete_resolver import ResolvedAthlete, SeedLookupError, resolve_athlete
from goldcoast.matching.business_candidates import (
    NoBusinessMatchError,
    athlete_tags,
    candidate_businesses,
)
from goldcoast.matching.style_selector import eligible_styles
from goldcoast.models.manifest import ClipEntry, ClipManifest
from goldcoast.models.pipeline import AdBrief, AdFormat, AthleteHints, HypeMoment
from goldcoast.settings import Settings
from goldcoast.storage import write_json

ENDORSEMENT = re.compile(
    r"\b(endorse\w*|recommend\w*|loves eating at|visits?|eats at|trained here|"
    r"official partner|favorite LA)\b",
    re.IGNORECASE,
)


class MatchingAgent:
    def __init__(self, client: Any, seed: SeedData, settings: Settings, output_dir: Path):
        self.client, self.seed, self.settings, self.output_dir = client, seed, settings, output_dir
        self.resolved: ResolvedAthlete | None = None

    def match(self, moment: HypeMoment) -> list[AdBrief]:
        if moment.athlete_id:
            if moment.athlete_id not in self.seed.athletes:
                raise SeedLookupError(
                    f"Manifest entry {moment.clip_path.name}: unknown athlete {moment.athlete_id}"
                )
            self.resolved = ResolvedAthlete(
                athlete_id=moment.athlete_id, confidence=1, evidence=["curated manifest athlete_id"]
            )
        else:
            self.resolved = resolve_athlete(
                moment.athlete_hints or AthleteHints(),
                self.seed,
                sport=moment.sport,
                threshold=self.settings.athlete_confidence_threshold,
            )
            manifest = ClipManifest.load(self.settings.clip_manifest)
            entry = manifest.get(moment.clip_path.name) or ClipEntry(
                file=moment.clip_path.name, sport=moment.sport
            )
            entry.athlete_id = self.resolved.athlete_id
            manifest.upsert(entry)
            manifest.save(self.settings.clip_manifest)
        athlete = self.seed.athletes[self.resolved.athlete_id]
        candidates = candidate_businesses(athlete, self.seed)
        if not candidates:
            raise NoBusinessMatchError(
                f"No businesses overlap {athlete.id}: {', '.join(sorted(athlete_tags(athlete)))}"
            )
        eligible = eligible_styles(moment, self.seed)
        if not eligible:
            raise SeedLookupError(f"No eligible ad style for {moment.sport}: {moment.description}")
        prompt = RERANK_PROMPT + json.dumps(
            {
                "moment": moment.model_dump(mode="json"),
                "athlete": athlete.model_dump(mode="json"),
                "candidates": [
                    {
                        **c.model_dump(),
                        "business": self.seed.businesses[c.business_id].model_dump(mode="json"),
                    }
                    for c in candidates
                ],
            }
        )
        fallback = {
            c.business_id: RankedBusiness(
                business_id=c.business_id,
                match_reason="Shared tags: " + ", ".join(c.overlap_tags),
                score=c.base_score,
                headline_direction=(
                    f"Inspired by {athlete.name}'s interest in "
                    f"{c.overlap_tags[0].replace('_', ' ')}, "
                    f"explore {self.seed.businesses[c.business_id].name} nearby."
                ),
            )
            for c in candidates
        }
        try:
            ranking = structured_call(
                self.client, "match_rerank", self.settings.video_model, prompt, Ranking
            ).businesses
        except AgentParseError:
            ranking = list(fallback.values())
        selected = {}
        for ranked in ranking:
            if ranked.business_id in fallback and ranked.business_id not in selected:
                selected[ranked.business_id] = ranked
        for business_id, ranked in fallback.items():
            selected.setdefault(business_id, ranked)
        style_id = eligible[0].id
        try:
            choice = structured_call(
                self.client,
                "match_style",
                self.settings.video_model,
                STYLE_PROMPT
                + json.dumps(
                    {
                        "moment": moment.description,
                        "styles": [s.model_dump(mode="json") for s in eligible],
                    }
                ),
                StyleChoice,
            )
            if choice.ad_style_id in {s.id for s in eligible}:
                style_id = choice.ad_style_id
        except AgentParseError:
            pass
        briefs = []
        for ranked in list(selected.values())[: self.settings.max_businesses]:
            business = self.seed.businesses[ranked.business_id]
            headline = ranked.headline_direction
            if not headline or ENDORSEMENT.search(headline):
                headline = fallback[business.id].headline_direction
            brief = AdBrief(
                id=f"{moment.id}-brief-{business.id}",
                run_id=moment.run_id,
                moment_id=moment.id,
                athlete_id=athlete.id,
                business_id=business.id,
                ad_style_id=style_id,
                match_reason=ranked.match_reason,
                match_score=ranked.score,
                headline_direction=headline,
                offer_text=business.offer_text or business.tagline,
                cta=business.cta,
                formats=[AdFormat.LANDSCAPE, AdFormat.PORTRAIT],
            )
            write_json(self.output_dir / "briefs" / f"{brief.id}.json", brief)
            briefs.append(brief)
        return briefs
