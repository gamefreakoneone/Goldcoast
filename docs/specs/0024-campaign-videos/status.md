# Status: 0024 Campaign videos

Completed. The current workspace replaces testimonial-facing creation with named campaign videos while preserving historical testimonial records and backend contracts. A video can be associated with a confirmed product, selected on Today, or resolved from an exact title or “the video I just uploaded” in Telegram. The video agent returns typed observations, discovery queries, a bounded timestamp and frame rationale; the worker extracts and privately stores the frame. Planning, both creative producers and the shared judge receive the evidence and frame. Review shows the source context and selected moment.

Regeneration restores the original video checkpoint and frame without another analysis or extraction. Replay copies the same checkpoint with zero provider calls. Historical videos without a preserved typed frame remain viewable and fail regeneration before grant reservation instead of silently analyzing a different frame. The testimonial UI, quote picker and testimonial allowance controls are absent; old records remain valid.

## Evidence

### Automated validation

- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m pytest -q`: 206 passed, one existing Starlette/AnyIO deprecation warning, 116.73s.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff check .`: All checks passed.
- `C:/Users/amogh/anaconda3/envs/goldcoast/python.exe -m ruff format --check .`: 247 files already formatted.
- `pnpm.cmd --dir web test --maxWorkers=1`: 38 tests in 13 files passed, 55.78s.
- `pnpm.cmd --dir web lint`: TypeScript and ESLint passed.
- `pnpm.cmd --dir web build`: passed; 56 modules transformed, 3.01s.
- `C:/Users/amogh/anaconda3/envs/goldcoast/Scripts/alembic.exe upgrade head`: exit 0; `alembic current` returned `0023_telegram_offset (head)`. This feature uses JSON Resources and needs no migration.
- `git -c safe.directory=C:/Users/amogh/Desktop/Goldcoast diff --check`: exit 0; only Windows line-ending notices.

The six focused Python campaign-video tests cover required labels, confirmed-product binding, model schema and provider accounting, out-of-range timestamps, private frame ownership, planning/scout propagation, regeneration and replay reuse, tenant-scoped Telegram selection and duplicate command idempotency. Both producer variants additionally assert the video in director, image-reference and judge contexts. Frontend tests cover staged video metadata, multipart fields, Today selection/product binding, Review evidence and removal of testimonial-facing controls. All tests deny network access.

### Rendered verification

Browser plugin was not available, so installed Python Playwright and headless Chrome exercised the running app at `http://localhost:5173`. Target flow: sign in -> Brand library campaign-video area -> Today live video selector -> fixture-backed Review evidence. The first two pages used the actual authenticated demo API; Review intercepted only the fake run endpoints so no campaign or grant was created.

- Page identity: `Goldcoast — Local discovery studio`; expected Brand, Today and Review routes rendered.
- Meaningful content: Campaign videos, upload constraints, optional campaign-video selector, Via phone label, selected-frame card and rationale were visible.
- Removed surface: no Customer voices, Testimonials, Testimonial quote or testimonial allowance control.
- Interaction: switched Today from Replay to Live and exercised the campaign-video select state without submitting.
- Desktop and mobile: 1440 x 1050 and 390 x 844; no horizontal overflow.
- Runtime health: no page errors, console errors or framework overlay.
- Screenshots inspected at `C:/Users/amogh/AppData/Local/Temp/goldcoast-0024-qa/`: `brand-campaign-videos-desktop.png`, `today-video-select-desktop.png`, `review-video-evidence-desktop.png`, and `review-video-evidence-mobile.png`.

The local API and worker were restarted only after confirming zero queued/running jobs. New PIDs were API 62952 and worker 55340; OpenAPI exposes `/api/v2/runs/{job_id}/video-frame`. Validation did not call `/workflows` against the real API and did not create a job. At the end, the demo and shared campaign allowances were both 2, with zero active jobs.
