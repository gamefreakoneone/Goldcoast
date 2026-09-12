# Design: 0002 Video Hype Detection

## Overview

The video agent is the entry point of the pipeline. It first consults the clip manifest by file name. For a clip that has already been analyzed, or hand-annotated, it builds the moments from the manifest and only runs ffmpeg. For a new clip it sends the video to a Gemini video-capable model with a structured prompt, receives candidate moments as JSON, filters them by hype threshold, extracts a PNG for the best frame of each moment, and records everything in the manifest so the owner can review and edit it.

## Components

- `src/goldcoast/sources/clip_source.py`: `ClipSource` protocol with `list_clips() -> list[Path]` and `open(name) -> Path`, and `LocalClipSource(root)`.
- `src/goldcoast/agents/video_agent.py`: `VideoAgent(client, settings, output_dir)` with `detect(clip_path) -> list[HypeMoment]`.
- `src/goldcoast/agents/prompts/video_detect.py`: prompt template and the JSON schema passed to the model as a response schema.
- `src/goldcoast/media/frames.py`: `extract_frame(clip, timestamp_s, out_path)` and `extract_candidates(clip, timestamp_s, window_s, count)` using `ffmpeg` via `subprocess`.
- `src/goldcoast/models/manifest.py` (from spec 0001): `ClipManifest`, `ClipEntry`, `ManifestMoment`. This spec adds `ClipEntry.to_hype_moments(run_id, clip_path)` and `ClipEntry.from_analysis(...)` helpers.
- `src/goldcoast/cli.py`: `detect` command.
- `tests/test_video_agent.py`, `tests/fixtures/model_calls/video/`.

## Data Flow

0. `detect` receives a clip path and loads the manifest. If `force` is false and the entry for the file name is `analyzed: true` with at least one moment carrying `best_frame_s`, the agent converts each manifest moment to a `HypeMoment` with a fresh id, the current `run_id`, the entry's `athlete_id`, and `source` set from `analyzed_by`. It extracts `frames/<moment_id>.png` at each `best_frame_s` with ffmpeg and returns. In pipeline use, the caller emits `clip_manifest_hit` with the clip name, `analyzed_by`, and `analyzed_at`. No model call happens. An analyzed entry with zero moments returns an empty list, which is the control-clip case.
1. Otherwise, if the file exceeds the inline size limit, the agent uploads it with the Gemini Files API and waits until it is active; otherwise it inlines the bytes.
2. The agent sends the prompt with a response schema describing an array of moments. It asks the model to return timestamps in seconds, a hype score with a one-sentence justification, the sport, the event context, and athlete hints drawn only from what is visible or audible.
3. The response is parsed into `list[HypeMoment]`. Moments below `hype_threshold` are dropped. Overlapping moments are merged, keeping the higher score.
4. For each surviving moment, `extract_frame` writes `frames/<moment_id>.png`. If the model flagged the frame as uncertain, `extract_candidates` writes a few neighbors and the agent asks the model to pick the sharpest and most dramatic one in a second, cheaper call.
5. The agent upserts the manifest entry with the moments and hints, `analyzed: true`, `analyzed_by: gemini`, `analyzed_at` now, and `sport` from the analysis if the entry did not already have one, preserving any existing `athlete_id` and `notes`. It saves the manifest atomically and returns the moments with `best_frame_path` set. In pipeline use, the caller emits `moment_detected` and `frame_extracted` events.

## Interfaces

- `VideoAgent.detect(clip_path: Path, force: bool = False) -> list[HypeMoment]`.
- `extract_frame(clip: Path, timestamp_s: float, out_path: Path) -> Path`.
- `ClipEntry.to_hype_moments(run_id: str, clip_path: Path) -> list[HypeMoment]` and `ClipEntry.from_analysis(existing: ClipEntry | None, file: str, sport: str, moments: list[ManifestMoment]) -> ClipEntry`.
- CLI: `goldcoast detect <clip> [--out DIR] [--threshold N] [--force-analysis] [--json]` and `goldcoast clips` to print the manifest as a table.
- Settings additions: `hype_threshold: int = 6`, `frame_candidate_window_s: float = 1.0`, `clip_manifest: Path = Path("sample_clips/manifest.json")`.
- Model call stages: `video_detect`, `video_pick_frame`.

## Error Handling

- Unreadable or non-MP4 file: `ClipError` before any model call.
- Model returns invalid JSON: one repair call with the parse error, then `AgentParseError`.
- Files API upload times out: `LLMCallError` after a bounded wait.
- ffmpeg failure: `FrameExtractionError` with the ffmpeg stderr; the moment is kept with `best_frame_path` unset and the pipeline caller decides whether to continue.
- Replay mode: records are read from `model_calls/` by stage and sequence; a missing record raises `ReplayMissError`.
- Manifest entry marked analyzed but a `best_frame_s` beyond the clip's duration (for example after a hand edit): `FrameExtractionError` naming the clip, the moment, and the duration, so the owner fixes the timestamp rather than the agent silently re-analyzing.
- Unparseable manifest: `ManifestError` before any work, since it is a hand-edited file and silent recovery would lose edits.

## Open Questions

- Inline versus Files API threshold. Default: inline under 20 MB, upload above.
- Whether to ask for multiple moments per clip or only the top one. Default: up to three, sorted by score, written to the manifest so the owner can delete the ones they do not want.
