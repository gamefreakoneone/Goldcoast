# Design: 0003 Context Matching

## Overview

The matching agent is deliberately two-layered. A deterministic layer decides who the athlete is and which businesses are eligible, so every match is explainable from seed data. A model layer then ranks eligible candidates and writes the reasons, adding judgment without the ability to invent.

## Components

- `src/goldcoast/agents/matching_agent.py`: `MatchingAgent(client, seed, settings, output_dir)` with `match(moment) -> list[AdBrief]`.
- `src/goldcoast/matching/athlete_resolver.py`: `resolve_athlete(hints, seed) -> ResolvedAthlete` with `athlete_id`, `confidence`, `evidence`.
- `src/goldcoast/matching/business_candidates.py`: `candidate_businesses(athlete, seed) -> list[Candidate]` with overlap tags and a base score.
- `src/goldcoast/matching/style_selector.py`: `eligible_styles(moment, seed) -> list[AdStyle]`.
- `src/goldcoast/agents/prompts/match_rerank.py` and `match_style.py`: prompt templates and response schemas.
- `src/goldcoast/cli.py`: `match` command.
- `tests/test_matching_agent.py`, `tests/test_athlete_resolver.py`, `tests/fixtures/model_calls/match/`.

## Data Flow

1. If `moment.athlete_id` is set, the agent loads that athlete from seed data and skips resolution; an unknown id raises `SeedLookupError` naming the manifest entry. Otherwise `resolve_athlete` scores each seed athlete: exact or alias name match on the hint contributes most, then country, sport, kit colors, bib number. The best score is normalized to a confidence. Below `athlete_confidence_threshold` (default 0.6) the agent raises `AthleteUnresolvedError`. On success the agent writes `athlete_id` into the clip's manifest entry through `ClipManifest.upsert` and saves atomically.
2. `candidate_businesses` computes the set of athlete tags (cuisines, dish names normalized to tags, interests) and returns businesses with non-empty intersection, each with `overlap_tags` and `base_score`.
3. The re-rank prompt receives the moment description, the athlete profile, and the candidates with their overlap tags. The response schema is an ordered array of `{business_id, match_reason, score}`. Any `business_id` not in the candidate list is discarded.
4. `eligible_styles` filters by `use_when` against the sport and a coarse moment type derived from the description (`victory`, `precision`, `comeback`, `record`). The style prompt picks one and returns a reason.
5. For each of the top `max_businesses`, an `AdBrief` is built with `headline_direction` from the re-rank response, business promo fields, the chosen `ad_style_id`, and `formats = [landscape, portrait]`. Briefs are written to `briefs/<brief_id>.json`.

## Interfaces

- `MatchingAgent.match(moment: HypeMoment) -> list[AdBrief]`.
- `resolve_athlete(hints: AthleteHints, seed: SeedData) -> ResolvedAthlete`.
- CLI: `goldcoast match <moment.json> [--out DIR] [--max-businesses N]`.
- Settings additions: `athlete_confidence_threshold: float = 0.6`, `max_businesses: int = 2`.
- Model call stages: `match_rerank`, `match_style`.
- Events emitted by the pipeline caller: `athlete_resolved`, `business_matched` (one per brief), `brief_created`.

## Error Handling

- No confident athlete: `AthleteUnresolvedError` with the top three candidates and their scores, surfaced as a `run_failed` event with a readable reason.
- No candidate businesses: `NoBusinessMatchError` listing the athlete's tags so the owner can fix seed data.
- Invalid re-rank output: fall back to the deterministic order and set `match_reason` to the overlap tags.
- Invalid style output: first eligible style.
- Replay mode reads recorded calls; deterministic layers need no records.

## Open Questions

- Whether dish names should be normalized to tags automatically or the owner must add dish tags to businesses. Default: normalize by lowercasing and replacing spaces with underscores, and also match cuisine alone.
- Whether `max_businesses` should be per category. Default: a single global cap.
