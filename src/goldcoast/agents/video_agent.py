from __future__ import annotations

from pathlib import Path
from typing import Any

from google.genai import types

from goldcoast.agents.prompts.video_detect import (
    VIDEO_PROMPT,
    DetectedMoment,
    FramePick,
    VideoAnalysis,
)
from goldcoast.agents.structured import structured_call
from goldcoast.media.frames import (
    FrameExtractionError,
    clip_duration,
    extract_candidates,
    extract_frame,
)
from goldcoast.models.manifest import ClipEntry, ClipManifest, ManifestMoment
from goldcoast.models.pipeline import HypeMoment
from goldcoast.settings import Settings
from goldcoast.storage import write_json


def merge_moments(moments: list[DetectedMoment], threshold: int) -> list[DetectedMoment]:
    merged: list[DetectedMoment] = []
    for moment in sorted(
        (m for m in moments if m.hype_score >= threshold), key=lambda m: m.start_s
    ):
        if merged and moment.start_s <= merged[-1].end_s:
            previous = merged.pop()
            best = max((previous, moment), key=lambda m: m.hype_score)
            merged.append(
                best.model_copy(
                    update={
                        "start_s": min(previous.start_s, moment.start_s),
                        "end_s": max(previous.end_s, moment.end_s),
                    }
                )
            )
        else:
            merged.append(moment)
    return sorted(merged, key=lambda m: m.hype_score, reverse=True)[:3]


class VideoAgent:
    def __init__(self, client: Any, settings: Settings, output_dir: Path) -> None:
        self.client = client
        self.settings = settings
        self.output_dir = output_dir
        self.run_id = output_dir.name
        self.manifest_hit: ClipEntry | None = None
        self.frame_errors: list[str] = []

    def detect(self, clip_path: Path, force: bool = False) -> list[HypeMoment]:
        manifest = ClipManifest.load(self.settings.clip_manifest)
        duration = clip_duration(clip_path)
        existing = manifest.get(clip_path.name)
        self.manifest_hit = None
        self.frame_errors = []
        if existing and existing.analyzed and not force:
            entry = existing
            self.manifest_hit = entry
        else:
            parts: list[Any] = [VIDEO_PROMPT + f"\nClip duration: {duration:.3f} seconds."]
            if not self.client.replay:
                parts.append(self.client.video_part(clip_path))
            analysis = structured_call(
                self.client,
                "video_detect",
                self.settings.video_model,
                parts,
                VideoAnalysis,
                input_refs=[str(clip_path)],
            )
            candidates = merge_moments(analysis.moments, self.settings.hype_threshold)
            for index, moment in enumerate(candidates):
                if not 0 <= moment.best_frame_s < duration or moment.end_s > duration:
                    raise FrameExtractionError(
                        f"Analysis timestamp beyond {clip_path} duration {duration}"
                    )
                if moment.frame_uncertain:
                    choices = extract_candidates(
                        clip_path,
                        moment.best_frame_s,
                        self.settings.frame_candidate_window_s,
                        out_dir=self.output_dir / "frames" / f"candidates_{index}",
                        start_s=moment.start_s,
                        end_s=moment.end_s,
                    )
                    pick_parts: list[Any] = [
                        "Pick the sharpest, most dramatic frame. Return its zero-based index."
                    ]
                    for i, (timestamp, path) in enumerate(choices):
                        pick_parts.extend(
                            [
                                f"Index {i}, timestamp {timestamp}s",
                                types.Part.from_bytes(
                                    data=path.read_bytes(),
                                    mime_type="image/png",
                                ),
                            ]
                        )
                    pick = structured_call(
                        self.client,
                        "video_pick_frame",
                        self.settings.video_model,
                        pick_parts,
                        FramePick,
                        input_refs=[str(p) for _, p in choices],
                    )
                    moment.best_frame_s = choices[pick.index][0]
            entry = ClipEntry.from_analysis(
                existing,
                clip_path.name,
                analysis.sport,
                [
                    ManifestMoment.model_validate(m.model_dump(exclude={"frame_uncertain"}))
                    for m in candidates
                ],
            )
            manifest.upsert(entry)
            manifest.save(self.settings.clip_manifest)
        moments = entry.to_hype_moments(self.run_id, clip_path)
        for moment in moments:
            frame = self.output_dir / "frames" / f"{moment.id}.png"
            if not 0 <= moment.best_frame_s < duration:
                raise FrameExtractionError(
                    f"Clip {clip_path}, moment {moment.id}: timestamp {moment.best_frame_s}s "
                    f"outside duration {duration}s"
                )
            try:
                moment.best_frame_path = extract_frame(clip_path, moment.best_frame_s, frame)
            except FrameExtractionError as exc:
                self.frame_errors.append(str(exc))
            write_json(self.output_dir / "moments" / f"{moment.id}.json", moment)
        return moments
