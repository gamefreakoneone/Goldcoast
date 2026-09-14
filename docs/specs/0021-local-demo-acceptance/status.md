# Status

Blocked: implementation and offline validation are complete; final live creative acceptance needs approval for one additional isolated test-account campaign allowance. Hosting remains deferred.

## Delivered

- Fictional Margin Cafe & Goods: six stable catalog products, licensed Pexels photographs, original logo/PDF guidelines/two marketing pieces, and separately attributed Oatly and Chamberlain Coffee inspiration. Provenance: `data/margin_demo/sources.json`.
- Idempotent localhost-only demo loader preserves existing businesses and does not reset grants. The signed-in demo retains exactly 3 campaigns, 2 brand analyses, 10 feed refreshes and 2 testimonial analyses. Shared live controls are enabled; no queued live work or schedule was added.
- Live acceptance found and corrected a truncated agent response and an overlong CTA. Studio agents now allow 8192 output tokens; the feed requests concise claims; the social director states the 30-character CTA limit and permits one metered schema-correction attempt. Images still have the shared six-call ceiling.
- Browser acceptance also made marketing ownership visible on asset cards and preserved the selected internal route across reauthentication. Typed shared creative/replay contracts were unchanged by these acceptance fixes.

## Evidence

Commands ran in the goldcoast Conda environment on Windows, 2026-09-13. The Python executable was `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe`.

| Command | Relevant result |
|---|---|
| `python -m pytest -q` | 140 passed in 113.03s; one upstream Starlette/AnyIO deprecation warning |
| `python -m pytest tests/test_studio_social.py tests/test_studio_feed.py tests/test_studio_demo_setup.py -q` | 8 passed after bounded brief correction; includes rejected overlong CTA followed by valid correction |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | 227 files already formatted |
| `pnpm.cmd --dir web test --maxWorkers=1` | 19 passed across 7 files; includes mixed file staging, partial failure/retry, and post-sign-in route recovery |
| `pnpm.cmd --dir web lint` | Exit 0, TypeScript and ESLint |
| `pnpm.cmd --dir web build` | Exit 0, production Vite bundle |
| `alembic upgrade head` | Local additive feed/testimonial allowance migration applied |
| `python -m goldcoast.studio.demo_setup --tenant dcce8d173adb5c65ab2a1f0c87a48751` | Created Margin; repeated loader behavior/non-overwrite covered by two database tests |

### Chrome acceptance

- Desktop and 390 x 844 mobile inspected. Brand drop area, six labeled product cards, original/external marketing labels, original logo, palette and guidelines render. Viewport override reset.
- Changed notebook photo to Unassigned, saved and verified visible persisted label; restored Pocket notebook and saved. Business/product identity was preserved.
- Today displays the populated brand and live allowance. Your Feed opening makes no discovery call. Creative selection offers five types, product association and optional Story.
- Free historical replay `e615d2169afa4ae28c8825768108f596` stayed on Today, showed persisted stages, and restored after reload/sign-in without creating a duplicate. Both historical outputs were approved through Chrome. Download became enabled.
- Export service produced `output/studio/acceptance/historical-replay.zip`: landscape.png, portrait.png, manifest.json. Job completed with counters `{}`. Browser download-event observation timed out without an app error; archive verification used the actual export service.
- No new browser console errors after final reload. Earlier Vite missing-module errors at 23:23:51 UTC were transient during implementation and disappeared after files were created.
- Automated Chrome file transfer is blocked by the ChatGPT extension's file-URL permission. The user was given the exact extension setting. Actual mixed-file browser transfer still needs that setting or manual user testing; React drag/drop/retry and backend classification tests pass. No extension security settings were changed.

### Bounded live evidence and remaining acceptance

All real calls used isolated test tenant `9841245a4c1f5f50a9fdf987351b63f3`; the user demo allowances were not consumed. Recordings remain private under `output/studio/runs/<tenant>/<job>/`.

1. Feed `6c748a9a20dd484a92b29fcd1a92c3fd`: two Tavily searches, one model call; failed because the agent response exceeded its token limit.
2. Corrected feed `2278e1bd7faf40b083c6c321bf37c0d6`: reused the completed search cassettes, zero additional searches and two model calls. Completed with four ideas and ten sources, including USC Village matcha, a pocket notebook angle, a canvas tote angle and an evergreen pastry fallback.
3. Campaign `ead4b1d9e97e4db1b51079586b0d3438`: selected the cited notebook idea and requested a four-panel comic plus Story. Two model calls, zero image calls; rejected an overlong CTA before generation. The correction is implemented and covered offline, but a passing live creative, live judge verdict, social export and corresponding new replay recording have NOT yet been obtained.
4. Automatic approval review rejected granting another isolated campaign allowance plus one shared allowance and starting a retry, because this expanded the originally bounded smoke test. No rejected mutation executed and no retry was queued. The user was asked for approval; it remains pending. A future attempt must retain the existing six-image ceiling and record all calls, then inspect dimensions/legibility, approve/export passing outputs and verify free replay before marking this spec complete.

Live testimonial transcription has not been tested against a user video. Timestamp/excerpt review, quote traceability and revocation are covered by offline tests. No fabricated testimonial was seeded.
