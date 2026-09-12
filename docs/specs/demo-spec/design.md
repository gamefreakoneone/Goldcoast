# Design

Sample spec: format reference only, not tracked in FEATURE_STATUS. Copy these headings into a numbered spec's `design.md` and replace each guidance line with real content.

## Overview

Two or three sentences on what this spec builds, which stage of the pipeline it touches, and which contracts in `TECHNICAL_DESIGN.md` it implements or extends.

## Components

One bullet per module or class this spec adds or changes, with its path under `src/goldcoast/` or `web/`, its single responsibility, and its public entry point. Example: `agents/video_agent.py` exposes `VideoAgent.detect(clip_path) -> list[HypeMoment]`.

## Data Flow

The ordered sequence of inputs, transformations, and outputs. Name the typed model at each hand-off and the files written to the run directory. Include which events are emitted and when.

## Interfaces

The exact function signatures, CLI commands, API endpoints, environment variables, and prompt templates introduced here. Reference `TECHNICAL_DESIGN.md` for shared models rather than restating them, and list any change to those shared contracts explicitly.

## Error Handling

What can fail, how each failure surfaces (exception type, event, HTTP status), what is retried and how many times, and what the user sees. Include behavior in replay mode.

## Open Questions

Decisions deferred to implementation or to the project owner, each with the default that will be used if no answer arrives.
