# Requirements: 0005 Ad Quality Judge

## Goal

Score every generated ad against its brief and style with a fixed rubric, and drive a bounded regeneration loop so that only ads meeting the quality bar, or the best available attempt clearly flagged, reach the human reviewer. After this spec, `python -m goldcoast judge <ad.json>` prints a `QualityVerdict`, and a `judge_loop` helper regenerates failing ads with the judge's hints.

## Functional Requirements

- `JudgeAgent.judge(ad, brief, moment) -> QualityVerdict` using a Gemini vision-capable model that receives the ad image, the hype frame, the athlete portrait, the business logo, the brief, the ad style, and the rubric.
- Rubric with five criteria scored 0 to 10:
  - `image_quality`: sharpness, composition, absence of artifacts and garbled text, and the athlete matching the hero frame and portrait without distortion or replacement.
  - `style_adherence`: mood, palette, typography, and layout notes of the `AdStyle`.
  - `business_accuracy`: business name, offer text, and call to action are present and spelled correctly, the logo is present and undistorted, and nothing contradicts the business record.
  - `format_compliance`: correct aspect ratio and size, required elements present, layout suits the placement (billboard or reel), no critical content in unsafe edges.
  - `brand_safety`: no offensive, misleading, or off-brand content, no unintended real-person likeness issues beyond the athlete images supplied, no competitor references, and no copy that states or implies the athlete endorses, recommends, or visits the business.
- `overall` is the minimum of `business_accuracy` and the rounded mean of all five, so a single accuracy failure cannot be averaged away.
- `passed` is true when `overall` is at or above `judge_pass_threshold` (default 7) and no criterion is below `judge_min_criterion` (default 5).
- `issues` lists concrete problems and `regeneration_hints` lists concrete, prompt-ready instructions to fix them.
- `judge_loop(brief, moment, fmt) -> JudgedAd` that generates, judges, and regenerates with hints up to `judge_max_retries` (default 2), returning the passing attempt or the highest-scoring attempt flagged `passed: false`.
- Verdicts are written to `verdicts/<ad_id>_attempt_<n>.json`. The judge never modifies image files.
- The judge is a separate model call from generation and is recorded and replayable.
- CLI `judge` command and tests in replay mode covering a pass, a fail then pass on retry, and exhaustion of retries.

## Inputs and Outputs

- Inputs: `GeneratedAd`, `AdBrief`, `HypeMoment`, seed data, settings.
- Outputs: `QualityVerdict` records, regenerated ads through spec 0004, model call records.

## Out of Scope

- Human approval. Verdicts are advisory and never auto-approve.
- Editing or inpainting images.
- Learned or calibrated scoring across runs.

## Dependencies

- 0001 for models and the client.
- 0004 for `AdAgent.generate` with hints and attempts.
- Project owner input: ad styles with `required_elements` per `docs/DATA_REQUIREMENTS.md`, and a chosen judge model id.
