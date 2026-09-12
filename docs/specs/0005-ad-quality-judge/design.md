# Design: 0005 Ad Quality Judge

## Overview

The judge closes the generation loop. It compares each ad image against the ground truth it was built from (frame, logo, brief, style) and returns structured scores plus actionable hints. A small loop helper uses those hints to regenerate, bounded by a retry cap, so the pipeline always produces a final ad per format, either passing or explicitly flagged.

## Components

- `src/goldcoast/agents/judge_agent.py`: `JudgeAgent(client, seed, settings, output_dir)` with `judge(ad, brief, moment) -> QualityVerdict`.
- `src/goldcoast/agents/prompts/judge_rubric.py`: rubric text, criterion definitions, scoring anchors (what a 3, 6, and 9 look like per criterion), and the response schema for `VerdictScores`, `issues`, and `regeneration_hints`.
- `src/goldcoast/pipeline/judge_loop.py`: `judge_loop(ad_agent, judge_agent, brief, moment, fmt) -> JudgedAd` where `JudgedAd` holds `final_ad`, `final_verdict`, and `attempts: list[tuple[GeneratedAd, QualityVerdict]]`.
- `src/goldcoast/cli.py`: `judge` command and `judge-loop` command for manual testing.
- `tests/test_judge_agent.py`, `tests/test_judge_loop.py`, `tests/fixtures/model_calls/judge/`.

## Data Flow

1. `judge` loads the business, style, and athlete for the brief, and the images for the ad, the hype frame, the athlete portrait, and the logo.
2. The prompt presents the ad image first, then the reference images labeled as references, then the brief facts that must appear verbatim (business name, offer text, call to action), then the style attributes and `required_elements`, then the format's target size and placement, then the rubric with anchors. The model is asked to score each criterion, list issues tied to a criterion, and write hints phrased as instructions to an image generator.
3. The response is parsed into `QualityVerdict`. `overall` and `passed` are computed in code, never taken from the model, so the threshold rules are deterministic.
4. The verdict is written to `verdicts/<ad_id>_attempt_<n>.json`. In pipeline use, the caller emits `ad_judged`.
5. `judge_loop` calls `ad_agent.generate_one` for attempt 1, judges it, and if it fails and attempts remain, emits `ad_regenerating`, calls `generate_one` with `attempt + 1` and the verdict's hints, and judges again. When an attempt passes or retries are exhausted, it selects the final ad (passing attempt, else highest `overall`), emits `ad_final`, and returns.

## Interfaces

- `JudgeAgent.judge(ad: GeneratedAd, brief: AdBrief, moment: HypeMoment) -> QualityVerdict`.
- `judge_loop(ad_agent: AdAgent, judge_agent: JudgeAgent, brief: AdBrief, moment: HypeMoment, fmt: AdFormat, emit: Callable[[PipelineEvent], None] | None = None) -> JudgedAd`.
- CLI: `goldcoast judge <ad.json> --brief <brief.json> --moment <moment.json> [--out DIR]` and `goldcoast judge-loop --brief <brief.json> --moment <moment.json> --format landscape|portrait [--out DIR]`.
- Settings additions: `judge_min_criterion: int = 5`. Existing: `judge_model`, `judge_max_retries`, `judge_pass_threshold`.
- Model call stage: `judge_score`.
- `QualityVerdict` is exactly as defined in `TECHNICAL_DESIGN.md`; this spec adds no fields.

## Error Handling

- Invalid judge output: one repair call, then the verdict is recorded with all scores 0, `passed: false`, and an issue stating the judge failed, so the loop still terminates.
- Generation failure during a retry: the loop stops and returns the best attempt so far.
- Judge model safety block on the ad image: treated as `brand_safety: 0` with the block reason as an issue.
- Replay mode reads recorded verdicts in sequence; the loop's control flow is exercised fully from records.

## Open Questions

- Whether a second judge call with a different model should break ties near the threshold. Default: no, a single judge call per attempt.
- Whether hints from earlier attempts should accumulate. Default: pass only the most recent verdict's hints plus a one-line summary of prior failures.
