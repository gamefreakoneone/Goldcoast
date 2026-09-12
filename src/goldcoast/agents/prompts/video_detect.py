from pydantic import Field

from goldcoast.models.manifest import ManifestMoment
from goldcoast.models.pipeline import ContractModel


class DetectedMoment(ManifestMoment):
    frame_uncertain: bool = False


class VideoAnalysis(ContractModel):
    sport: str
    moments: list[DetectedMoment] = Field(default_factory=list, max_length=3)


class FramePick(ContractModel):
    index: int = Field(ge=0, le=2)


VIDEO_PROMPT = """Watch this complete sports clip once. Identify up to three distinct,
non-overlapping crowd-pleasing hype moments, sorted by hype score (0 to 10).
Use seconds relative to the start of this clip, never broadcast clock times.
Choose start_s <= best_frame_s <= end_s strictly within the clip duration.
Describe the decisive action and justify the hype score in the description;
include sport, event context, and athlete hints based only on visible or audible
evidence: name, country, kit colors, bib number, crowd reaction. Use null for
unknown hints. Do not guess an athlete from fame alone. Pick a sharp, dramatic,
picturesque frame for an advertisement; flag frame_uncertain only if neighboring
frames need inspection. Return no moments if the clip contains no hype.
"""
