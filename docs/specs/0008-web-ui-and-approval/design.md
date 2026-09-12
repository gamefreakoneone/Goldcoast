# Design: 0008 Web UI and Approval

## Overview

A single-page React app whose state is a reduction over the run's event stream. Every panel derives from the same store, so the video, timeline, and gallery stay in sync without extra fetches during a run. Ads, verdicts, and decisions are fetched once at the end and after each decision.

## Components

- `web/src/api/client.ts`: typed fetch wrappers for every endpoint and an `EventSource` helper with `Last-Event-ID` resume.
- `web/src/api/types.ts`: TypeScript types mirroring the Pydantic models in `TECHNICAL_DESIGN.md`, generated or hand-written to match field for field.
- `web/src/state/runStore.ts`: a reducer over `PipelineEvent` producing `RunState` with `status`, `moments`, `briefs`, `adsByBrief`, `verdictsByAd`, `timeline`, and `failures`. Implemented with `useReducer` and a context provider.
- `web/src/components/ClipPicker.tsx`: clip list, replay toggle, start action.
- `web/src/components/VideoStage.tsx`: `<video>` element, highlight overlay, seek and pause logic driven by `moments`, extracted frame panel.
- `web/src/components/AgentTimeline.tsx`: ordered step list with icons per event type, live scroll, and expandable payloads.
- `web/src/components/AdGallery.tsx` and `AdCard.tsx`: grouping by business, format pair, scores, badge, issues, attempt history, approve and reject buttons.
- `web/src/components/DetailDrawer.tsx`: athlete and business detail.
- `web/src/components/ExportPanel.tsx`.
- `web/src/App.tsx`: layout with the stage and timeline on the left, gallery on the right.
- `web/src/test/`: Vitest tests and the recorded events fixture copied from `tests/fixtures/runs/<fixture_run_id>/events.jsonl`.

## Data Flow

1. On load, fetch clips and previous runs. The user picks a clip and optionally a replay source, then starts a run; the app stores the run id and opens the event stream.
2. Each SSE message is parsed into a `PipelineEvent` and dispatched to the reducer. The reducer appends to `timeline` and updates the typed collections from the payload.
3. `VideoStage` reacts to the first `moment_detected` by seeking and overlaying, and to `frame_extracted` by showing the frame from `/media/`.
4. `AdGallery` renders from `adsByBrief` and `verdictsByAd` as `ad_generated`, `ad_judged`, and `ad_final` arrive, so cards appear and update live. On `run_completed`, the app fetches `/runs/{id}/ads` once to reconcile.
5. Approve or reject posts a decision, then refetches ads for that run and updates the card.
6. Export calls the endpoint and renders the manifest.

## Interfaces

- API contracts exactly as in `TECHNICAL_DESIGN.md`; no new endpoints.
- `runReducer(state: RunState, event: PipelineEvent): RunState`.
- Vite dev server on port 5173 with a proxy to `http://localhost:8000` so the app uses relative URLs.
- Environment: `VITE_API_BASE` optional override.

## Error Handling

- SSE disconnect: automatic reconnect with the last event id; a banner shows reconnecting state.
- `run_failed`: the timeline shows the reason and the gallery shows whatever was produced.
- Decision request failure: the card reverts and shows the error text.
- Missing media file: the card shows a placeholder with the path so it is debuggable during the demo.

## Open Questions

- Styling approach. Default: plain CSS modules with a small set of design tokens, no UI framework, to keep the build simple.
- Whether the timeline should auto-play the video from the start when a run begins. Default: yes, the video plays from zero while the agent works, then seeks on detection, which reads as the AI watching.
