# Requirements: 0004 Ad Generation

## Goal

Turn each `AdBrief` into a landscape ad and a portrait ad using the Gemini image model, with the hype frame as the hero image and the business's brand and offer integrated. After this spec, `python -m goldcoast generate <brief.json>` writes two PNGs and prints `GeneratedAd` JSON for each.

## Functional Requirements

- `AdAgent.generate(brief, moment, attempt=1, hints=None) -> list[GeneratedAd]` producing one ad per format in the brief.
- The prompt includes the hype frame image as the hero image, the athlete portrait from the athlete's `headshot` as an identity reference, the business logo image, the business name, tagline, offer text and call to action, brand colors, the ad style's mood, palette, typography guidance, layout notes for the format, required elements, and the exact target size and aspect ratio.
- The prompt instructs the model to build the ad around the real hero frame as the background, keeping the athlete's appearance as captured. If the athlete's face is clearly visible in the hero frame, the portrait is a consistency reference only. If it is not, the model places the portrait as a foreground cutout overlay, with the business's product or offering visual beside it (a slice, a bowl, a gym floor) so the composition reads as athlete plus place. It must not ask the model to invent or redraw the athlete's face.
- The prompt states the discovery framing: the ad invites visitors to explore the athlete's interests nearby and must not claim the athlete endorses, recommends, or visits the business. Headline and copy come from the brief's `headline_direction`, `offer_text`, and `cta` and are not to be rewritten into endorsement language by the model. When the business has no `offer_text`, the brief carries the business tagline in its place and the prompt asks for no offer language at all.
- The prompt includes the first `reference_photos` entry of the business, when present, as the product visual to place beside the athlete.
- If the model declines to produce an image because it contains a recognizable real person, the agent records the refusal, retries once with the portrait removed and the hero frame described as the ad's photographic base, and if still refused raises `AdGenerationError` with the refusal reason so the owner can switch to the compositing fallback described in `design.md`.
- Output images are saved to `ads/<business_id>/<format>/attempt_<n>.png` with a sidecar JSON holding the `GeneratedAd` record and the full prompt.
- Dimension check: if the returned image has the correct aspect ratio but a different size, resize to the target; if the aspect ratio is wrong, retry once with a stronger instruction, then record the ad with `format_mismatch: true` in its metadata for the judge.
- `hints` from a judge verdict are appended to the prompt on regeneration attempts, and `attempt` is incremented.
- Every model call is recorded and replayable, including the image bytes reference.
- CLI `generate` command and tests in replay mode that verify file layout, metadata, and dimension handling using recorded responses.

## Inputs and Outputs

- Inputs: `AdBrief`, `HypeMoment` (for the frame path), seed data, optional regeneration hints.
- Outputs: PNG files, `GeneratedAd` records, model call records.

## Out of Scope

- Judging ads (0005).
- Text overlay with Pillow. Text is rendered by the image model, per the intentional design decision in `TECHNICAL_DESIGN.md`.
- Additional formats.

## Dependencies

- 0001 for models and the client.
- 0002 for the hype frame.
- 0003 for briefs.
- Project owner input: the athlete portrait, business logos, and ad styles per `docs/DATA_REQUIREMENTS.md`, and a chosen image model id.
