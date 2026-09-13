# Status: 0015 marketing workspace

Completed

## Delivered

Responsive authenticated marketing workspace: PKCE login, private image uploads, typed profile and brand confirmation, daily chief workflow, durable activity, evidence/candidate inspection, judged creative review, versioned approval/rejection, ZIP export, history and owner usage controls. Legacy UI remains opt-in. Three generated concept references and two fictional Morrow Coffee demonstration images are committed under docs/design/marketing and data/studio_demo/assets.

## Evidence

- `pnpm.cmd --dir web test`: 6 files, 16 tests passed (14.29 s).
- `pnpm.cmd --dir web lint`: TypeScript and ESLint passed.
- `pnpm.cmd --dir web build`: production build passed; lazy marketing JS 47.66 kB (14.37 gzip), CSS 24.05 kB.
- `python -m pytest -q`: 122 passed (96.16 s); one upstream Starlette deprecation warning. Subsequent added regressions: `python -m pytest tests/test_strands_runtime.py tests/test_studio_workflow.py -q`: 18 passed (6.33 s), including schema metadata, recording preservation and rejected-quote fallback.
- `python -m ruff check .`: All checks passed. `python -m ruff format --check .`: 189 files already formatted.
- `python scripts/check_studio_browser.py --phase onboard`: real Keycloak authorization-code login, confirmed Morrow Coffee profile, two actual private PNG uploads. Local imported users now have verified example emails to avoid a first-login missing-profile block.
- `--phase brand` / `--phase confirm`: actual Gemini analysis of both uploaded images, editable image-derived kit, owner review and save. Same brand job 6ab585213fdd458aae6b855d6b905a94 completed; 3 reserved model attempts (sandbox connection denial, rejected old schema wire format, successful analysis).
- `--phase campaign`: campaign 182dda74dc204d95affff2932da436c1 completed with real Strands/Gemini/Tavily calls. 19 recorded sources, 3 supported graph edges, 4 excluded evidence/opportunities. Selected Post-Reservoir Loop Afternoon Latte. Landscape and portrait passed on first image attempt, all four judge criteria 10/10; these are actual model verdicts, not independent guarantees.
- `--phase review`: real history navigation, evidence/activity, reject then approve, two approvals and authenticated ZIP download to output/studio-browser/approved-campaign.zip.
- `--phase pause`: global live generation disabled after validation. Exactly one campaign and one brand allowance consumed; all failed/recovery requests remain included in durable job counters. No automatic retry was added.
- `--phase capture`: desktop and 390px mobile screenshots, no horizontal overflow. Browser runs reported no page errors. Chrome computer-use connector exposed no browsers; installed Chrome via the project Playwright Python library was used as the allowed fallback.

## Live integration fixes

Use response_json_schema for strict model schemas, reduce provider schema constraints while retaining full local Pydantic validation, and supply structured extraction with a plain recorded evidence transcript. Provider-rejected requests were manually resumed within the same original reservation. Completed scout evidence was reused for the final extraction recovery. Source quote mismatches now exclude their evidence with a reason instead of aborting the entire campaign. Live runtime recordings now choose unused sequence filenames on restart. Earlier overwritten failed agent records in this validation run are a known development-only limitation; durable counters/events retain the attempts. Brand/Gemini image records were preserved.

Shared contract changes: provider wire schemas are a subset; local typed contracts remain strict. Invalid citations are explicitly excluded before graph construction. These corrections affect specs 0009/0013 and are recorded here as discovered by integrated validation.

## Visual fidelity ledger

Compared rendered Today, Brand and Review screenshots with their generated concepts using view_image. Matched ivory canvas, 252px navigation, forest active states, serif title hierarchy, split panels, photo library, two-format review, scores and footer. Fixed a selector that accidentally applied keyboard focus outlines to every control. Real kit voice and judge feedback are longer than concept placeholders, increasing panel height; actual ad copy/images and controlled composition replace illustrative mock ads. Mobile stacks panels with horizontally scrollable navigation and full-width actions. Screenshots are in output/studio-browser; concepts and asset prompts/provenance are in docs/design/marketing/design-system.md. No functional controls were replaced by static mock data.
