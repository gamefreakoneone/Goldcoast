# Status: 0005 Ad Quality Judge

## Status

Completed

## Evidence

Started after 0004 commit 43fea79. Read requirements, design, tasks, and shared
contracts. Paused for the owner's upstream creative refinement, then resumed
after 855f342. Validation now uses the creative 0003 briefs and 0004 ads with the
brief-scoped layout. The rubric explicitly checks correct athlete spelling and
the complete, visibly labeled fictional ticket-holder offer.

### Validation — 2026-09-12

```powershell
(& conda shell.powershell hook) | Out-String | Invoke-Expression
conda activate goldcoast
$env:GOLDCOAST_REPLAY = "0"
python -m goldcoast judge output/manual/0004-creative/ads/yama-sushi-marketplace-koreatown/brief_783f5055d830/landscape/attempt_1.json --brief output/manual/0003-creative/briefs/0002-moment-1-brief-yama-sushi-marketplace-koreatown.json --moment output/manual/0002/moments/0002-moment-1.json --out output/manual/0005
python -m goldcoast judge output/manual/0004-creative/ads/yama-sushi-marketplace-koreatown/brief_783f5055d830/portrait/attempt_1.json --brief output/manual/0003-creative/briefs/0002-moment-1-brief-yama-sushi-marketplace-koreatown.json --moment output/manual/0002/moments/0002-moment-1.json --out output/manual/0005
python -m goldcoast judge-loop --brief output/manual/0003-creative/briefs/0002-moment-1-brief-yama-sushi-marketplace-koreatown.json --moment output/manual/0002/moments/0002-moment-1.json --format portrait --out output/manual/0005-loop
$env:GOLDCOAST_REPLAY = "1"; pytest tests/test_judge_agent.py tests/test_judge_loop.py -p no:cacheprovider --basetemp output/pytest-tmp
pytest -p no:cacheprovider --basetemp output/pytest-tmp
ruff check .
ruff format --check .
```

All exited 0. Targeted: `12 passed in 5.59s`; regression: `63 passed in 12.91s`;
lint passes; `105 files already formatted`. Original calls, images, and HTTP
journals copied unchanged into `tests/fixtures/model_calls/judge/{direct,loop}/`.
Eight live generation requests total: two direct scores, three images, three
loop scores. No video requests, repair requests, or hidden SDK retries.

The landscape passed with all five criteria 7, overall 7. The real creative
portrait was rejected with this full verdict:

```json
{
  "id": "0002-moment-1-brief-yama-sushi-marketplace-koreatown-portrait-attempt-1-verdict",
  "run_id": "0002",
  "ad_id": "0002-moment-1-brief-yama-sushi-marketplace-koreatown-portrait-attempt-1",
  "attempt": 1,
  "scores": {"image_quality": 6, "style_adherence": 6, "business_accuracy": 4, "format_compliance": 7, "brand_safety": 7, "overall": 4},
  "passed": false,
  "issues": [
    "Athlete name misspelled as 'Simone Billes' instead of 'Simone Biles'.",
    "Redundant cutout of the athlete's head layered directly over the background hero shot where her face is already clearly visible.",
    "Logo colors altered to dark reddish-orange on black, reducing contrast and fidelity."
  ],
  "regeneration_hints": [
    "Fix spelling of athlete's name to 'Simone Biles'.",
    "Remove redundant sticker headshot cutout since the hero background already features the athlete's face clearly.",
    "Use proper high-contrast brand colors for the logo at the bottom."
  ],
  "model_id": "gemini-3.8-flash",
  "created_at": "2026-09-12T22:54:53.679586Z"
}
```

The separate live portrait loop finished with exactly three attempts on disk:
overall 6 (duplicate cutout/style), 5 (invented logo), then 7 (passed, with advisory
cutout-outline and logo-color issues). Final image:
`output/manual/0005-loop/ads/yama-sushi-marketplace-koreatown/brief_783f5055d830/portrait/attempt_3.png`.
Each image has a sidecar and a verdict. The judge never edits the image, verified
by byte comparison in tests. Real recorded loop tests cover first-pass success,
third-attempt success, and a one-retry cap selecting attempt 1 over worse attempt
2. Invalid JSON, safety blocks, thresholds, and retry generation failure are
covered with explicit negative test inputs and no network calls.

Shared contracts deliberately document judge_min_criterion, deterministic scoring,
dimension enforcement, and the type/payload event hook matching EventBus.

## Blockers

None.

## Change Log

- 2026-09-12: Spec created.
- 2026-09-12: Completed rubric, judge, bounded loop, CLI, real pass/fail and loop recordings, all validation evidence, and 63 passing tests after the creative refinement.
