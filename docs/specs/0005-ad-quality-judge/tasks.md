# Tasks: 0005 Ad Quality Judge

## Task List

- [x] Write the rubric, scoring anchors, and response schema in `src/goldcoast/agents/prompts/judge_rubric.py`.
- [x] Implement `JudgeAgent.judge` with reference image loading, parsing, and deterministic `overall` and `passed` computation.
- [x] Add `judge_min_criterion` to settings and `.env.example`.
- [x] Implement `judge_loop` in `src/goldcoast/pipeline/judge_loop.py` with event emission hooks.
- [x] Wire the `judge` and `judge-loop` CLI commands.
- [x] Record real judge calls for a passing ad and a failing ad into `tests/fixtures/model_calls/judge/`.
- [x] Write `tests/test_judge_agent.py` covering pass, fail, invalid output, and threshold edge cases.
- [x] Write `tests/test_judge_loop.py` in replay mode covering pass on first attempt, pass on retry, and retry exhaustion with best-attempt selection.

## Validation Steps

```powershell
conda activate goldcoast
python -m goldcoast judge output/manual/0004-creative/ads/<business_id>/brief_<key>/landscape/attempt_1.json --brief output/manual/0003-creative/briefs/<brief>.json --moment output/manual/0002/moments/<moment>.json --out output/manual/0005
python -m goldcoast judge-loop --brief output/manual/0003-creative/briefs/<brief>.json --moment output/manual/0002/moments/<moment>.json --format portrait --out output/manual/0005
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_judge_agent.py tests/test_judge_loop.py
ruff check .
```

Expected: the `judge` command prints a verdict with five criterion scores, an `overall`, `passed`, and at least one hint when it fails; `judge-loop` ends with a final ad and at most `judge_max_retries + 1` attempts on disk; tests pass in replay mode.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including one full verdict JSON and the attempt count from the loop.
- `docs/FEATURE_STATUS.md` shows 0005 as Completed with a link to the evidence.
- The spec is committed on its own.
