# Feature Status

Project ledger for Goldcoast. Check this file before starting work. Specs are executed in numeric order.

## Status Table

| Spec | Feature | Status | Evidence | Notes |
|---|---|---|---|---|
| 0001 | Project scaffold and seed data | Completed | [Validation evidence](specs/0001-project-scaffold-and-seed-data/status.md#evidence) | Conda env, pyproject, Pydantic models, seed JSON loaders, CLI entry point |
| 0002 | Video hype detection | Not started | | Gemini video analysis to HypeMoment, best-frame extraction with ffmpeg |
| 0003 | Context matching | Not started | | Athlete resolution, business matching by tags, ad style selection to AdBrief |
| 0004 | Ad generation | Not started | | Gemini image model produces landscape and portrait ads per brief |
| 0005 | Ad quality judge | Not started | | Rubric scoring to QualityVerdict, bounded regeneration loop |
| 0006 | Pipeline orchestration and run store | Not started | | Stage chaining, event bus, run directory, replay mode |
| 0007 | API and live events | Not started | | FastAPI runs, SSE events, media, decisions, export |
| 0008 | Web UI and approval | Not started | | React/Vite player, timeline, gallery with scores, approve/reject |

`docs/specs/demo-spec/` is a format reference and is not tracked here. Its `requirements.md` holds the project-level requirements and delivery order.

## Status Definitions

- Completed: all tasks in the spec's `tasks.md` are checked, validation steps pass, and evidence is recorded in the spec's `status.md`.
- In progress: work has started and at least one task is checked or code exists on a branch.
- Blocked: work cannot continue until a named dependency, decision, or external input is resolved. The blocker is recorded in the spec's `status.md`.
- Not started: no work has begun.

## Update Rule

When a feature's status changes, update this table and the spec's `status.md` and `tasks.md` checkboxes in the same change. The Evidence column links to the validation section of the spec's `status.md` or names the commit that completed the spec.
