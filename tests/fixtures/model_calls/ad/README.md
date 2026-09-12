# Image generation recordings

Real gemini-3.1-flash-image outputs from the first 0004 live validation on
2026-09-12. `ad_generate_1.json` is an unchanged copy of the original
`output/manual/0004/model_calls/ad_generate_2.json` (landscape); `ad_generate_2.json`
is original `ad_generate_4.json` (portrait). Original sequence numbers, prompts,
response metadata, image references, and image bytes are retained. Fixture
filenames express replay ordering, not original HTTP request numbers.

The first validation made four calls: one generation and one strict-ratio retry
per format. All returned native 1376x768 or 768x1376 canvases. The documented 1%
native-canvas tolerance subsequently enabled deterministic resizing, with no new
model call. These final selected outputs replay one call per format. The original
four calls and HTTP journals remain under ignored output/manual/0004.

`inputs/` holds the unchanged real brief, moment, and extracted hero frame. Tests
rebase the frame path to this fixture; they need neither output/ nor an MP4.
Negative dimension/refusal cases deliberately transform or wrap these recordings
and are not represented as additional real provider responses.
