# Tasks: 0002 Video Hype Detection

## Task List

- [ ] Implement `ClipSource` and `LocalClipSource` in `src/goldcoast/sources/clip_source.py`.
- [ ] Implement `extract_frame` and `extract_candidates` in `src/goldcoast/media/frames.py`.
- [ ] Write the detection prompt and response schema in `src/goldcoast/agents/prompts/video_detect.py`.
- [ ] Implement `VideoAgent.detect` with upload or inline handling, parsing, threshold filtering, and overlap merging.
- [ ] Implement the uncertain-frame candidate pick.
- [ ] Add `ClipEntry.to_hype_moments` and `ClipEntry.from_analysis`, and wire the manifest lookup, frame extraction from recorded timestamps, and manifest write-back into `VideoAgent.detect`.
- [ ] Add `hype_threshold`, `frame_candidate_window_s`, and `clip_manifest` to settings and `.env.example`.
- [ ] Wire the `detect` CLI command with `--force-analysis`, and the `clips` command.
- [ ] Write a test that calls `detect` on an analyzed clip and asserts zero model calls, and a test that edits `best_frame_s` in a temporary manifest and asserts the frame is extracted at the new timestamp.
- [ ] Record real model calls for the MVP hype clip into `tests/fixtures/model_calls/video/`, and add a hand-written empty-response fixture for the no-hype case.
- [ ] Write `tests/test_video_agent.py` running in replay mode against the fixtures.
- [ ] Update `README.md` run commands.

## Validation Steps

```powershell
conda activate goldcoast
python -m goldcoast detect sample_clips/<hype-clip>.mp4 --out output/manual/0002
python -m goldcoast clips
python -m goldcoast detect sample_clips/<hype-clip>.mp4 --out output/manual/0002-again
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_video_agent.py
ruff check .
```

Then open `sample_clips/manifest.json`, change `best_frame_s` for the hype clip by a few seconds, and run the second `detect` command again.

Expected: the first `detect` yields at least one moment, a PNG exists at the reported `best_frame_path`, and the manifest now has an entry for the clip with `analyzed: true`; `clips` lists it; the second `detect` finishes in a few seconds, writes no new file under `model_calls/`, and returns the same moments; after the hand edit the extracted frame visibly changes and no model call is made; the no-hype fixture test yields an empty list and an analyzed entry with no moments; tests pass in replay mode without network access.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including the detected moment JSON and a reference to the extracted frame.
- `docs/FEATURE_STATUS.md` shows 0002 as Completed with a link to the evidence.
- The spec is committed on its own.
