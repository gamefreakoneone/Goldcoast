# Feature Status

Project ledger for Goldcoast. Check this file before starting work. Specs are executed in numeric order.

## Status Table

| Spec | Feature | Status | Evidence | Notes |
|---|---|---|---|---|
| 0001 | Project scaffold and seed data | Completed | [Validation evidence](specs/0001-project-scaffold-and-seed-data/status.md#evidence) | Conda env, pyproject, Pydantic models, seed JSON loaders, CLI entry point |
| 0002 | Video hype detection | Completed | [Evidence](specs/0002-video-hype-detection/status.md#evidence) | Three real moments and PNGs, analyzed manifest, offline replay fixture, cache/edit checks; 35 tests pass |
| 0003 | Context matching | Completed | [Evidence](specs/0003-context-matching/status.md#evidence) | Creative athlete-led discovery and labeled 15% restaurant demo offers; fresh real fixtures |
| 0004 | Ad generation | Completed | [Evidence](specs/0004-ad-generation/status.md#evidence) | Creative discovery ads and visible 15% demo offer in both formats; fresh real fixtures |
| 0005 | Ad quality judge | Completed | [Evidence](specs/0005-ad-quality-judge/status.md#evidence) | Real typo rejection and 6→5→7 regeneration; all 63 Python tests pass |
| 0006 | Pipeline orchestration and run store | Completed | [Evidence](specs/0006-pipeline-orchestration-and-run-store/status.md#evidence) | Real run 20260912-230559-0d2470: 12 passing final ads; independent replay; 73 tests pass |
| 0007 | API and live events | Completed | [Evidence](specs/0007-api-and-live-events/status.md#evidence) | API replay 20260912-235123-6424eb: 12 passing finals, SSE, approvals/export; 87 tests pass |
| 0008 | Web UI and approval | Completed | [Evidence](specs/0008-web-ui-and-approval/status.md#evidence) | Replay UI run 20260913-002142-60027e; 12 finals, 17 attempts; Playwright MCP screenshots, decisions/export, native SSE resume; 12 frontend tests pass |

`docs/specs/demo-spec/` is a format reference and is not tracked here. Its `requirements.md` holds the project-level requirements and delivery order.

## Pivot delivery

| Spec | Feature | Status | Evidence | Notes |
|---|---|---|---|---|
| 0009 | Strands runtime | Completed | [Evidence](specs/0009-strands-runtime/status.md) | Strands 1.55.1; 8 runtime tests, 95 total tests pass; recorded tool execution and offline replay |

| 0010 | Accounts and persistence | Completed | [Evidence](specs/0010-accounts-and-persistence/status.md) | OIDC, PostgreSQL, durable usage limits and jobs |

| 0011 | Business and brand onboarding | Completed | [Evidence](specs/0011-business-and-brand-onboarding/status.md) | Private assets and editable visual brand kit |

| 0012 | Discovery and knowledge graph | Completed | [Evidence](specs/0012-discovery-and-knowledge-graph/status.md) | Tavily and cited graph |

| 0013 | Chief marketing workflow | Completed | [Evidence](specs/0013-chief-marketing-workflow/status.md) | Daily agent orchestration |

| 0014 | Branded creative production | Completed | [Evidence](specs/0014-branded-creative-production/status.md) | Reference imagery, composition and judge |

| 0015 | Marketing workspace | Completed | [Evidence](specs/0015-marketing-workspace/status.md) | New business-facing UI |

| 0016 | Adaptation and replay | Completed | [Evidence](specs/0016-adaptation-and-replay/status.md) | Free historical demo and opt-in scheduling |

| 0017 | Hosted deployment | Blocked | [Evidence](specs/0017-hosted-deployment/status.md) | Deferred by user until local acceptance testing |

Local acceptance testing is active. 0017 hosting is explicitly deferred by the user; 0024 submission package remains not started.

## Status Definitions

- Completed: all tasks in the spec's `tasks.md` are checked, validation steps pass, and evidence is recorded in the spec's `status.md`.
- In progress: work has started and at least one task is checked or code exists on a branch.
- Blocked: work cannot continue until a named dependency, decision, or external input is resolved. The blocker is recorded in the spec's `status.md`.
- Not started: no work has begun.

## Update Rule

When a feature's status changes, update this table and the spec's `status.md` and `tasks.md` checkboxes in the same change. The Evidence column links to the validation section of the spec's `status.md` or names the commit that completed the spec.

| 0018 | Asset organization and product identity | Completed | [Evidence](specs/0018-asset-organization/status.md) | Staged uploads and categorized private assets |

| 0019 | Discovery feed and inline workflow | Completed | [Evidence](specs/0019-discovery-feed/status.md) | Cited local ideas |

| 0020 | Social creatives and testimonial quotes | Completed | [Evidence](specs/0020-social-creatives/status.md) | Instagram posts and reviewed quotes |

| 0021 | Populated local demo and live acceptance | Blocked | [Evidence](specs/0021-local-demo-acceptance/status.md) | Margin populated; feed verified live after schema repair; creative acceptance pending |


| 0022 | Live signals | Blocked | [Evidence](specs/0022-live-signals/status.md) | Implemented and automated checks pass; zero Margin allowance blocks live acceptance |

| 0023 | Telegram approvals | Blocked | [Evidence](specs/0023-telegram-approvals/status.md) | Implemented; 188 Python/29 UI tests pass; real-bot acceptance awaits owner connection and 0022 live run |

| 0024 | Submission package | Not started | Pending local acceptance | Follows 0021; hosting remains deferred |
