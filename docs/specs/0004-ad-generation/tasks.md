# Tasks: 0004 Ad Generation

## Task List

- [x] Extend `GeminiClient` with `generate_image` and image call recording.
- [x] Implement `check_dimensions`, `resize_to_format`, and `load_image_part` in `src/goldcoast/media/images.py`.
- [x] Write `build_ad_prompt` in `src/goldcoast/agents/prompts/ad_generate.py`, including the athlete portrait as a reference part and the instruction not to redraw the athlete.
- [x] Implement the real-person refusal retry without the portrait part.
- [x] Implement `AdAgent.generate` and `generate_one` with file layout, dimension handling, and hints.
- [x] Add `format_mismatch` and `resized_from` handling to `GeneratedAd.metadata`.
- [x] Wire the `generate` CLI command.
- [x] Record real model calls for one brief in both formats into `tests/fixtures/model_calls/ad/`.
- [x] Write `tests/test_ad_agent.py` in replay mode covering both formats, a resize case, and a format mismatch case.

## Validation Steps

```powershell
conda activate goldcoast
python -m goldcoast generate output/manual/0003/briefs/<brief>.json --moment output/manual/0002/moments/<moment>.json --out output/manual/0004
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_ad_agent.py
ruff check .
```

Expected: two PNGs exist at `ads/<business_id>/brief_<key>/landscape/attempt_1.png` (1920x1080) and `ads/<business_id>/brief_<key>/portrait/attempt_1.png` (1080x1920) with sidecar JSON, the business name and offer are visible in each image on manual inspection, the athlete in each ad is recognizably the one in the hero frame, and tests pass in replay mode. If the model refuses on real-person grounds even after the retry, record the exact refusal and apply the compositing fallback authorized by the kickoff/resume instructions, documenting the design change.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including paths to the generated images and a note on the manual inspection.
- `docs/FEATURE_STATUS.md` shows 0004 as Completed with a link to the evidence.
- The spec is committed on its own.
