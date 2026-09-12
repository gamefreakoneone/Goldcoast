# Requirements: 0002 Video Hype Detection

## Goal

Given a clip, produce a list of `HypeMoment` records that identify when the crowd-pleasing action happens, why it is a hype moment, who the athlete appears to be, and the single best frame for use in an ad. After this spec, `python -m goldcoast detect <clip>` prints valid `HypeMoment` JSON and writes the best frame PNG.

## Functional Requirements

- A `ClipSource` protocol with a `LocalClipSource` implementation that lists and opens MP4 files under `sample_clips/`.
- A `VideoAgent.detect(clip_path) -> list[HypeMoment]` that uploads or inlines the clip to a Gemini video-capable model, prompts for hype moments, and parses the response into models.
- Each moment includes `start_s`, `end_s`, `best_frame_s`, `hype_score` from 0 to 10, `description`, `sport`, `event_context`, and `athlete_hints` with `name`, `country`, `kit_colors`, `bib_number`, and `crowd_reaction`.
- Moments below a configurable `hype_threshold` (default 6) are dropped. A control clip with no hype produces an empty list, not an error.
- Best-frame extraction with ffmpeg at `best_frame_s`, saved as PNG under `frames/<moment_id>.png` in the provided output directory, with a candidate window of a few frames around the timestamp when the model reports uncertainty.
- Manifest lookup by clip name: before calling Gemini, the agent looks up the clip's file name in `sample_clips/manifest.json`. If the entry is `analyzed: true` and has at least one moment with `best_frame_s`, the agent builds `HypeMoment` records from the entry, including its `athlete_id` if set, extracts the frames with ffmpeg at the recorded timestamps, and returns without any model call. Otherwise it analyzes the clip with Gemini and writes the moments, hints, `analyzed: true`, `analyzed_by: gemini`, and `analyzed_at` into the entry, creating the entry if the clip was not listed.
- The manifest is the owner's editing surface. After a Gemini analysis the owner can open the manifest, change `best_frame_s` or the window to a more picturesque moment, set or correct `athlete_id`, delete moments they do not want, and set `analyzed_by: manual`. The next run uses the edited values without re-analysis.
- A `force` flag re-runs Gemini for a clip and replaces its moments and hints, but never overwrites a non-null `athlete_id`.
- Every model call is recorded through the client from spec 0001, and the agent works in replay mode from those records.
- CLI `detect` command that writes the frames and prints the moments as JSON, with `--force-analysis` to re-run Gemini, and a `clips` command that lists manifest entries with their analyzed state, athlete id, and best-frame timestamps.
- Tests in replay mode using recorded responses for the MVP hype clip, checking the parsed models, the frame extraction, and that the manifest entry is written correctly. The no-hype case is covered with a recorded or hand-written empty response fixture rather than a second real clip, and results in an entry with `analyzed: true` and an empty `moments` list.
- A test that runs `detect` on an already-analyzed clip and asserts zero model calls, and a test that edits `best_frame_s` in the manifest and asserts the next `detect` extracts the frame at the new timestamp.

## Inputs and Outputs

- Inputs: clip path, the clip manifest, settings, output directory.
- Outputs: `list[HypeMoment]`, PNG frames, an updated manifest entry, model call records.

## Out of Scope

- Athlete resolution against seed data. The agent reports hints and passes through a manifest `athlete_id` when present; resolution and write-back of `athlete_id` happen in spec 0003.
- Live stream ingestion.
- Any UI.

## Dependencies

- 0001 for models, settings, and the recording Gemini client.
- Project owner input: the MVP gymnastics clip with its manifest entry naming `athlete_id`. A control clip is optional.
