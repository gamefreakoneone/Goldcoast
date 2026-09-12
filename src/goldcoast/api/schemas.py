from datetime import datetime

from pydantic import Field

from goldcoast.models.manifest import ClipEntry
from goldcoast.models.pipeline import (
    AdFormat,
    ApprovalDecision,
    ApprovalDecisionValue,
    ContractModel,
    GeneratedAd,
    HypeMoment,
    QualityVerdict,
)


class RunCreate(ContractModel):
    clip_path: str = Field(min_length=1)
    replay: bool | None = None
    replay_from: str | None = Field(default=None, min_length=1)


class ClipInfo(ClipEntry):
    clip_path: str
    clip_url: str
    available: bool


class MomentView(HypeMoment):
    best_frame_url: str | None
    clip_url: str


class AdView(GeneratedAd):
    image_url: str


class AdAttempt(ContractModel):
    ad: AdView
    verdict: QualityVerdict | None
    is_final: bool


class AdWithVerdict(AdView):
    verdict: QualityVerdict
    decision: ApprovalDecision | None
    attempts: list[AdAttempt]
    errors: list[str] = Field(default_factory=list)


class DecisionCreate(ContractModel):
    ad_id: str | None = None
    decision: ApprovalDecisionValue
    reviewer: str = Field(min_length=1)
    note: str | None = None


class ExportAd(ContractModel):
    ad_id: str
    brief_id: str
    business_id: str
    format: AdFormat
    path: str
    image_url: str
    decision: ApprovalDecision


class ExportManifest(ContractModel):
    run_id: str
    exported_at: datetime
    ads: list[ExportAd]
