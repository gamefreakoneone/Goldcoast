# Requirements: 0003 Context Matching

## Goal

Turn a `HypeMoment` into one `AdBrief` per relevant local business by resolving the athlete, matching businesses to the athlete's preferences, and choosing an ad style. After this spec, `python -m goldcoast match <moment.json>` prints valid `AdBrief` JSON for each matched business.

## Functional Requirements

- Athlete lookup: if the `HypeMoment` carries an `athlete_id` from the clip manifest, use that athlete directly with confidence 1.0 and skip resolution. This is the normal path for curated demo clips.
- Athlete resolution: otherwise match `athlete_hints` against seed athletes using name and aliases, country, sport, kit colors, and bib number. Produce a confidence score and fail explicitly below a threshold rather than guessing. On success, write the resolved `athlete_id` back into the clip's manifest entry so the owner can confirm or correct it and so the next run skips resolution.
- Candidate businesses: every business with at least one tag overlapping the athlete's cuisines, dishes, or interests. Businesses with no overlap are never candidates.
- Ranking: a deterministic score from tag overlap count and category priority, followed by a model re-rank that receives the moment description, athlete profile, and candidate list and returns an ordered list with a one-sentence `match_reason` per business. The model may reorder candidates but cannot add businesses.
- Selection: the top `max_businesses` (default 2) candidates become briefs.
- Ad style selection: filter styles whose `use_when` matches the sport or moment type, then a model choice among them with a reason. Fall back to the first matching style if the model output is invalid.
- Each `AdBrief` carries `headline_direction`, `offer_text` and `cta` from the business, `match_reason`, `match_score`, and both formats.
- `headline_direction` follows the discovery framing: it invites the visitor to explore something the athlete is known to like, using only facts from the athlete's seed profile, and never states or implies that the athlete endorses, recommends, or visits the business. The re-rank prompt includes this rule and an example of acceptable and unacceptable phrasing, and the agent rejects a headline direction containing endorsement verbs (`endorses`, `recommends`, `loves eating at`, `visits`) and falls back to a template built from the overlap tag.
- Every model call is recorded and replayable.
- CLI `match` command and tests in replay mode covering a confident match, an ambiguous athlete, and an athlete with no matching businesses.

## Inputs and Outputs

- Inputs: `HypeMoment` JSON, seed data, settings.
- Outputs: `list[AdBrief]`, model call records, brief JSON files.

## Out of Scope

- Image generation.
- Sport-venue matching by the athlete's sport rather than interests (a bar raiser). The tag rule already allows it if the owner adds venues with the sport as a tag.
- Geographic distance scoring beyond the `nearest_venue` field.

## Dependencies

- 0001 for models, seed loaders, and the Gemini client.
- 0002 for `HypeMoment` inputs and recorded fixtures.
- Project owner input: athlete profiles and businesses with overlapping tags per `docs/DATA_REQUIREMENTS.md`.
