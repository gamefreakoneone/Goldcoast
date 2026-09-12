# PLANS.md

Use this template when no spec exists yet for a piece of work, or when an existing spec needs re-planning. Copy the sections below into a working plan, fill them in, and once the plan is stable turn it into a numbered spec folder under `docs/specs/NNNN-feature-name/` with `requirements.md`, `design.md`, `tasks.md`, and `status.md`. Add the new spec to `docs/FEATURE_STATUS.md` when the folder is created.

## Title

A short name for the work, in the form `NNNN-feature-name` if it will become a spec.

## Goal

One or two sentences on the outcome this work delivers and who benefits from it.

## Scope

What is included and what is explicitly excluded. Name the stages, modules, and files that will change.

## Current Context

What exists today that this work builds on or replaces. Reference the relevant specs, contracts in `TECHNICAL_DESIGN.md`, and any status in `docs/FEATURE_STATUS.md`.

## Design Decisions

Each decision as a bullet: the choice, the alternatives considered, and why this one was picked. Note anything that should later be recorded under Intentional Design Decisions in `TECHNICAL_DESIGN.md`.

## Interfaces

The typed models, function signatures, CLI commands, API endpoints, event types, and file layouts this work introduces or changes. Reference existing contracts rather than restating them.

## Tasks

An ordered checkbox list of concrete steps. Each task should be small enough to complete and verify on its own.

- [ ] Task 1
- [ ] Task 2

## Acceptance Criteria

Observable conditions that must be true when the work is done. Each criterion should map to at least one verification step.

## Verification

The exact commands to run and the expected results, including tests, lint, and any manual check in the CLI or web UI. This section becomes the Validation Steps of the spec's `tasks.md`.
