# Requirements: 0008 Web UI and Approval

## Goal

Give the demo its stage: a browser UI where an operator picks a clip, watches the AI analyze it, sees each agent hand-off appear in real time, reviews the generated ads with their judge scores, and approves or rejects each one. After this spec, the full story from hype moment to approved ads plays out in one screen.

## Functional Requirements

- React and Vite application under `web/` in TypeScript, talking only to the API from spec 0007.
- Clip picker listing clips from the API with a Start button, and a toggle to run in replay mode from a chosen previous run.
- Video player showing the selected clip. When a `moment_detected` event arrives, the player seeks to the moment, shows a highlight overlay over the detected window, and pauses on `best_frame_s` with the extracted frame displayed beside it.
- Agent timeline that renders each event as it arrives with a labeled step: watching, hype detected, athlete resolved, business matched, brief created, generating, judged with scores, regenerating with hints, final. The timeline connects to the SSE endpoint and resumes with `Last-Event-ID` after a disconnect.
- Ad gallery grouped by business, showing landscape and portrait side by side with the judge's five scores, overall, pass or fail badge, issues, and the attempt history.
- Approve and reject controls per ad that call the decision endpoint and update in place. Rejected ads show the reason field. Ads without a verdict are not approvable.
- Export button that calls the export endpoint and shows the manifest with links to approved files.
- Detail drawer for the athlete profile and business record behind each brief, read from the seed endpoints, so the audience can see why the match happened.
- Layout works at desktop width for the demo and degrades to a single column on narrow screens.
- Vitest unit tests for the event reducer and the gallery grouping, and one integration test against a mocked API using recorded event JSON from the fixture run.

## Inputs and Outputs

- Inputs: API responses and SSE events.
- Outputs: user decisions posted to the API, export requests.

## Out of Scope

- Authentication.
- Editing prompts or regenerating ads manually from the UI.
- Mobile-first design or accessibility beyond keyboard-operable controls and readable contrast.

## Dependencies

- 0007 for every endpoint and the SSE stream.
- Project owner input: none beyond earlier specs.
