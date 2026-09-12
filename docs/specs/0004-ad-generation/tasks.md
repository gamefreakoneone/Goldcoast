# Tasks: 0004 Ad Generation

## Task List

- [ ] Extend `GeminiClient` with `generate_image` and image call recording.
- [ ] Implement `check_dimensions`, `resize_to_format`, and `load_image_part` in `src/goldcoast/media/images.py`.
- [ ] Write `build_ad_prompt` in `src/goldcoast/agents/prompts/ad_generate.py`, including the athlete portrait as a reference part and the instruction not to redraw the athlete.
- [ ] Implement the real-person refusal retry without the portrait part.
- [ ] Implement `AdAgent.generate` and `generate_one` with file layout, dimension handling, and hints.
- [ ] Add `format_mismatch` and `resized_from` handling to `GeneratedAd.metadata`.
- [ ] Wire the `generate` CLI command.
- [ ] Record real model calls for one brief in both formats into `tests/fixtures/model_calls/ad/`.
- [ ] Write `tests/test_ad_agent.py` in replay mode covering both formats, a resize case, and a format mismatch case.

## Validation Steps

```powershell
conda activate goldcoast
python -m goldcoast generate output/manual/0003/briefs/<brief>.json --moment output/manual/0002/moments/<moment>.json --out output/manual/0004
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_ad_agent.py
ruff check .
```

Expected: two PNGs exist at `ads/<business_id>/landscape/attempt_1.png` (1920x1080) and `ads/<business_id>/portrait/attempt_1.png` (1080x1920) with sidecar JSON, the business name and offer are visible in each image on manual inspection, the athlete in each ad is recognizably the one in the hero frame, and tests pass in replay mode. If the model refuses on real-person grounds even after the retry, record that in `status.md` as a blocker and raise the compositing fallback decision with the owner before continuing.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including paths to the generated images and a note on the manual inspection.
- `docs/FEATURE_STATUS.md` shows 0004 as Completed with a link to the evidence.
- The spec is committed on its own.
