from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AdFormat(StrEnum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


AD_FORMAT_SIZES: dict[AdFormat, tuple[int, int]] = {
    AdFormat.LANDSCAPE: (1920, 1080),
    AdFormat.PORTRAIT: (1080, 1920),
}


class AthleteHints(ContractModel):
    name: str | None = None
    country: str | None = None
    kit_colors: list[str] = Field(default_factory=list)
    bib_number: str | None = None
    crowd_reaction: str | None = None
    source: Literal["gemini", "manual"] = "gemini"


class HypeMoment(ContractModel):
    id: str
    run_id: str
    clip_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    best_frame_s: float = Field(ge=0)
    best_frame_path: Path | None = None
    hype_score: float = Field(ge=0, le=10)
    description: str
    sport: str
    event_context: str
    athlete_id: str | None = None
    athlete_hints: AthleteHints | None = None
    source: Literal["gemini", "manual"] = "gemini"

    @model_validator(mode="after")
    def validate_timestamps(self) -> HypeMoment:
        if self.end_s < self.start_s:
            raise ValueError("end_s must be greater than or equal to start_s")
        if not self.start_s <= self.best_frame_s <= self.end_s:
            raise ValueError("best_frame_s must fall between start_s and end_s")
        return self


class AdBrief(ContractModel):
    id: str
    run_id: str
    moment_id: str
    athlete_id: str
    business_id: str
    ad_style_id: str
    match_reason: str
    match_score: float = Field(ge=0, le=1)
    headline_direction: str
    offer_text: str
    cta: str
    formats: list[AdFormat] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_formats(self) -> AdBrief:
        if len(self.formats) != len(set(self.formats)):
            raise ValueError("formats must not contain duplicates")
        return self


class AdMetadata(ContractModel):
    format_mismatch: bool = False
    resized_from: tuple[int, int] | None = None
    portrait_omitted: bool = False
    composited: bool = False


class GeneratedAd(ContractModel):
    id: str
    run_id: str
    brief_id: str
    business_id: str
    format: AdFormat
    attempt: int = Field(ge=1)
    image_path: Path
    prompt_used: str
    model_id: str
    created_at: datetime
    metadata: AdMetadata = Field(default_factory=AdMetadata)


class VerdictScores(ContractModel):
    image_quality: int = Field(ge=0, le=10)
    style_adherence: int = Field(ge=0, le=10)
    business_accuracy: int = Field(ge=0, le=10)
    format_compliance: int = Field(ge=0, le=10)
    brand_safety: int = Field(ge=0, le=10)
    overall: int = Field(ge=0, le=10)


class QualityVerdict(ContractModel):
    id: str
    run_id: str
    ad_id: str
    attempt: int = Field(ge=1)
    scores: VerdictScores
    passed: bool
    issues: list[str] = Field(default_factory=list)
    regeneration_hints: list[str] = Field(default_factory=list)
    model_id: str
    created_at: datetime


class ApprovalDecisionValue(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalDecision(ContractModel):
    ad_id: str
    decision: ApprovalDecisionValue
    reviewer: str
    note: str | None = None
    decided_at: datetime


class PipelineEventType(StrEnum):
    RUN_STARTED = "run_started"
    CLIP_LOADED = "clip_loaded"
    CLIP_MANIFEST_HIT = "clip_manifest_hit"
    MOMENT_DETECTED = "moment_detected"
    MOMENT_SKIPPED = "moment_skipped"
    FRAME_EXTRACTED = "frame_extracted"
    ATHLETE_RESOLVED = "athlete_resolved"
    BUSINESS_MATCHED = "business_matched"
    BRIEF_CREATED = "brief_created"
    AD_GENERATING = "ad_generating"
    AD_GENERATED = "ad_generated"
    AD_JUDGED = "ad_judged"
    AD_REGENERATING = "ad_regenerating"
    AD_FINAL = "ad_final"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    AD_DECIDED = "ad_decided"


class PipelineEvent(ContractModel):
    id: str
    run_id: str
    type: PipelineEventType
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunFailure(ContractModel):
    stage: str
    message: str
    moment_id: str | None = None
    brief_id: str | None = None
    format: AdFormat | None = None


class Run(ContractModel):
    id: str
    clip_path: Path
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    replay: bool = False
    moment_ids: list[str] = Field(default_factory=list)
    brief_ids: list[str] = Field(default_factory=list)
    ad_ids: list[str] = Field(default_factory=list)
    failures: list[RunFailure] = Field(default_factory=list)
    replay_from: str | None = None
