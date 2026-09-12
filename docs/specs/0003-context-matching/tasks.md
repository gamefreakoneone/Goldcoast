# Tasks: 0003 Context Matching

## Task List

- [x] Apply the owner's creative discovery and clearly labeled ticket-holder demo-offer refinement, record fresh matching outputs, and revalidate.

- [x] Implement `resolve_athlete` in `src/goldcoast/matching/athlete_resolver.py`, plus the direct lookup path when `moment.athlete_id` is set and the manifest write-back on resolution.
- [x] Implement `candidate_businesses` in `src/goldcoast/matching/business_candidates.py` with tag normalization.
- [x] Implement `eligible_styles` in `src/goldcoast/matching/style_selector.py`.
- [x] Write the re-rank and style prompts and schemas under `src/goldcoast/agents/prompts/`.
- [x] Implement `MatchingAgent.match` combining the layers and writing brief files.
- [x] Add `athlete_confidence_threshold` and `max_businesses` to settings and `.env.example`.
- [x] Wire the `match` CLI command.
- [x] Record real model calls for a confident match into `tests/fixtures/model_calls/match/`.
- [x] Write `tests/test_athlete_resolver.py` covering confident, ambiguous, and unknown athletes, the manifest `athlete_id` shortcut, and the write-back.
- [x] Write `tests/test_matching_agent.py` in replay mode covering a normal match, an invalid re-rank response, and no candidates.

## Validation Steps

```powershell
conda activate goldcoast
python -m goldcoast match output/manual/0002/moments/<moment>.json --out output/manual/0003
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_athlete_resolver.py tests/test_matching_agent.py
ruff check .
```

Expected: the `match` command prints one `AdBrief` per matched business, each `business_id` shares at least one tag with the resolved athlete, and each brief has both formats; tests pass in replay mode.

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`, including the printed briefs.
- `docs/FEATURE_STATUS.md` shows 0003 as Completed with a link to the evidence.
- The spec is committed on its own.
