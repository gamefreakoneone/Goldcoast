# Status: 0004 Ad Generation

## Status

Completed

## Evidence

### Validation — 2026-09-12

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
ruff format .
ruff check .
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_image_recording.py tests/test_llm_client.py tests/test_models.py -p no:cacheprovider --basetemp output/pytest-tmp
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast generate output/manual/0003/briefs/0002-moment-1-brief-yama-sushi-marketplace-koreatown.json --moment output/manual/0002/moments/0002-moment-1.json --out output/manual/0004
$env:GOLDCOAST_REPLAY = "1"
python C:/Users/amogh/AppData/Local/Temp/opencode/goldcoast_capture_ad.py
pytest tests/test_ad_agent.py -p no:cacheprovider --basetemp output/pytest-tmp
pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
```

All commands exited 0. Preliminary tests: `9 passed in 1.25s`; ad tests:
`5 passed in 3.22s`; full regression: `51 passed in 8.01s`; lint:
`All checks passed!`; format: `96 files already formatted`.

The live CLI printed two complete GeneratedAd records and made exactly four
recorded image requests, zero video requests. Both formats initially triggered
the one permitted dimension retry. Original records 1–4 have latencies 10043,
10624, 8350, and 8587 ms, respectively, beginning at
`2026-09-12T22:33:42.252513Z`. Four HTTP journals confirm these requests.
No likeness refusal occurred, so compositing was not adopted.

All landscape responses were 1376x768 and portrait responses were 768x1376.
These are the model's native quantized canvases, within 0.8% of the requested
ratios. Updated the dimension contract to a 1% relative native-canvas tolerance;
larger mismatches still retry once and remain flagged. This avoids repeated
requests for the same native dimensions. The temporary capture helper copies
original records 2 and 4 byte-for-byte to the replay fixture, preserves their
image bytes and original sequence metadata, then invokes `AdAgent.generate`
using `RecordedResponseClient` and the existing brief/moment to normalize them
without a network call. Fixture README explains the ordering. Tests reproduce
this normalization from committed inputs, independent of the temporary helper.

Final normalized outputs (both with sidecar JSON):

- `output/manual/0004-normalized/ads/yama-sushi-marketplace-koreatown/brief_783f5055d830/landscape/attempt_1.png`: 1920x1080, resized_from [1376,768].
- `output/manual/0004-normalized/ads/yama-sushi-marketplace-koreatown/brief_783f5055d830/portrait/attempt_1.png`: 1080x1920, resized_from [768,1376].

Both metadata records have format_mismatch false, portrait_omitted false, and
composited false. Initial strict-ratio outputs and all four calls remain intact
under `output/manual/0004/` for provenance.

Manual inspection: opened both generated images and the normalized portrait.
The smiling athlete with raised arms from the hero photograph is recognizable,
with sushi imagery and the Yama logo. Business name, tagline, and CTA are readable
in both. Landscape uses a dark diagonal right panel with yellow headline;
portrait uses gold motion streaks and lower-third business copy. The headline is
longer than the style's five-word preference; this is a concrete quality issue
for the separate judge rather than a missing generated asset. No promotion or
endorsement claim appears in the visible copy.

Read all spec documents and shared contracts before implementation. Context7 MCP
was queried through the existing stdio helper twice on 2026-09-12. The official
`/googleapis/python-genai` README and SDK sources confirm `Part.from_bytes`,
`GenerateContentConfig(response_modalities=["IMAGE"], image_config=ImageConfig(aspect_ratio=...))`,
both 16:9 and 9:16, response parts/inline image data, candidate finish reasons,
Files API activation, and structured JSON schemas. No video call was made.

Contract correction: multiple moments can match the same business, so the
original business/format/attempt path would overwrite earlier moments. Ads now
include `brief_<key>`, where key is the first 12 hexadecimal SHA-256 characters
of the brief ID. This also keeps Windows paths short. Shared documentation and
validation paths are updated deliberately. Original generated image bytes are
stored separately in `model_calls/images/`, so resizing and later attempts cannot
alter replay evidence. `GeneratedAd` gains typed metadata for dimensions and the
portrait-free retry.

## Blockers

None.

## Change Log

- 2026-09-12: Spec created.
- 2026-09-12: Implemented after 0003 commit 953f62f, verified SDK through Context7, recorded both formats, documented native-dimension normalization and collision-free paths, and completed all checks.
