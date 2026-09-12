from __future__ import annotations

import json
import subprocess
from pathlib import Path

from goldcoast.sources.clip_source import ClipError, validate_clip
from goldcoast.storage import write_bytes


class FrameExtractionError(RuntimeError):
    pass


def clip_duration(clip: Path) -> float:
    validate_clip(clip)
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(clip)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        info = json.loads(result.stdout)
        if not any(stream.get("codec_type") == "video" for stream in info["streams"]):
            raise ValueError("no video stream")
        duration = float(info["format"]["duration"])
        if duration <= 0:
            raise ValueError("non-positive duration")
        return duration
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise ClipError(f"Cannot probe {clip}: {detail}") from exc


def extract_frame(clip: Path, timestamp_s: float, out_path: Path) -> Path:
    duration = clip_duration(clip)
    if not 0 <= timestamp_s < duration:
        raise FrameExtractionError(
            f"Clip {clip}, moment {out_path.stem}: timestamp {timestamp_s}s outside "
            f"duration {duration}s"
        )
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                str(timestamp_s),
                "-i",
                str(clip),
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "pipe:1",
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
        if not result.stdout:
            raise FrameExtractionError(f"No frame from {clip} at {timestamp_s}s")
        write_bytes(out_path, result.stdout)
    except (OSError, subprocess.SubprocessError) as exc:
        stderr = getattr(exc, "stderr", b"") or str(exc).encode()
        raise FrameExtractionError(stderr.decode(errors="replace")) from exc
    return out_path


def extract_candidates(
    clip: Path,
    timestamp_s: float,
    window_s: float,
    count: int = 3,
    *,
    out_dir: Path,
    start_s: float = 0,
    end_s: float | None = None,
) -> list[tuple[float, Path]]:
    if count < 2 or window_s <= 0:
        raise ValueError("Candidates require count >= 2 and a positive window")
    duration = clip_duration(clip)
    lower = max(start_s, timestamp_s - window_s, 0)
    upper = min(end_s if end_s is not None else duration, timestamp_s + window_s, duration - 0.001)
    if lower > upper:
        raise FrameExtractionError(f"Invalid candidate window for {clip}")
    times = [lower + (upper - lower) * index / (count - 1) for index in range(count)]
    return [
        (t, extract_frame(clip, t, out_dir / f"candidate_{i}.png")) for i, t in enumerate(times)
    ]
