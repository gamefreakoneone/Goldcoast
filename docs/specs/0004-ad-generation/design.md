# Design: 0004 Ad Generation

## Overview

The ad agent builds a multimodal prompt per brief and format, sends it to the Gemini image model, and persists the result with enough metadata for the judge and the UI. It is stateless across calls so regeneration is just another call with a higher attempt number and extra hints.

## Components

- `src/goldcoast/agents/ad_agent.py`: `AdAgent(client, seed, settings, output_dir)` with `generate(brief, moment, attempt, hints) -> list[GeneratedAd]` and `generate_one(brief, moment, fmt, attempt, hints) -> GeneratedAd`.
- `src/goldcoast/agents/prompts/ad_generate.py`: `build_ad_prompt(brief, athlete, business, style, fmt, hints) -> PromptParts` combining text and image parts.
- `src/goldcoast/media/images.py`: `check_dimensions(path, fmt) -> DimensionResult`, `resize_to_format(path, fmt)`, and `load_image_part(path)`.
- `src/goldcoast/llm/client.py`: extended with `generate_image(stage, model_id, parts, config) -> RecordedImageCall` that saves the returned image bytes to a path chosen by the caller and records the call with a reference to that path.
- `src/goldcoast/cli.py`: `generate` command.
- `tests/test_ad_agent.py`, `tests/fixtures/model_calls/ad/`.

## Data Flow

1. `generate` loads the athlete, business, and style for the brief from seed data and the hype frame from the moment.
2. For each format, `build_ad_prompt` assembles: system-style instruction on the ad's purpose, audience (Olympic visitors near the venue), and discovery framing; the hero frame labeled as the photographic background with a description of the moment; the athlete portrait labeled as an identity reference that becomes a foreground cutout overlay only if the athlete's face is not clearly visible in the hero frame; the business's product or offering to depict beside the athlete, drawn from `offerings` and, if present, `reference_photos`; the logo image; brand and offer text that must appear verbatim; style guidance; layout notes for the format; required elements; the exact pixel size; and any regeneration hints. The instruction states that the athlete must appear as in the supplied images and must not be redrawn or replaced, and that copy must not imply endorsement.
3. `generate_image` calls the model, saves the PNG to `ads/<business_id>/<format>/attempt_<n>.png`, and records the call.
4. `check_dimensions` validates the file. Same aspect ratio but wrong size is resized in place. Wrong aspect ratio triggers one immediate retry with a stronger size instruction; if still wrong, the ad is kept and `metadata.format_mismatch` is set.
5. A `GeneratedAd` is written next to the PNG as `attempt_<n>.json` and returned. The pipeline caller emits `ad_generating` before and `ad_generated` after each format.

## Interfaces

- `AdAgent.generate(brief: AdBrief, moment: HypeMoment, attempt: int = 1, hints: list[str] | None = None) -> list[GeneratedAd]`.
- `build_ad_prompt(...) -> PromptParts` where `PromptParts` is an ordered list of text and image parts.
- CLI: `goldcoast generate <brief.json> --moment <moment.json> [--out DIR] [--format landscape|portrait] [--attempt N] [--hint TEXT ...]`.
- Model call stage: `ad_generate`.
- `GeneratedAd.metadata` gains optional keys `format_mismatch: bool`, `resized_from: [w, h]`.

## Error Handling

- Missing logo, frame, or athlete portrait file: `AssetMissingError` before any model call, naming the athlete or business id and the expected path.
- Model returns no image: one retry, then `AdGenerationError` for that format; the other format still proceeds.
- Safety block from the model: recorded, surfaced as `AdGenerationError` with the block reason so the pipeline can mark the brief as failed for that format.
- Real-person refusal: if the block reason indicates a recognizable person, retry once without the portrait part and with the hero frame described as the ad's photographic base. If refused again, raise `AdGenerationError` with the reason. Compositing fallback, to be adopted only if this happens with the chosen model: the model generates the styled background, typography, and logo placement from text and the logo alone at the target size, leaving a described empty region, and `media/images.py` pastes the cropped hero frame into that region with Pillow. This changes the intentional design decision about full-ad generation and must be recorded in `TECHNICAL_DESIGN.md` if adopted.
- Replay mode returns the recorded image path and copies it into the current run's ads directory.

## Open Questions

- Whether to pass the logo as an image part or describe it in text. Default: image part, since the judge checks logo presence.
- Whether face visibility in the hero frame should be decided by code (a face-detection pass) or left to the image model's judgment from the prompt. Default: the model decides from the prompt for the MVP; add a `face_visible` flag on `HypeMoment` from the video agent later if the model's choices are inconsistent.
- Whether landscape and portrait should be generated in one call with two outputs. Default: one call per format for simpler retries.
