# Requirements

## Product Goal

Goldcoast turns live Olympic excitement into foot traffic for local businesses. A video agent watches LA 2028 Olympics footage, detects hype moments such as a Japanese archer's bullseye that makes the crowd erupt, and identifies the single best frame for marketing use. An ad-generation agent then combines that frame with the athlete's profile (nationality, favorite foods, interests), finds local businesses that match those preferences, chooses an ad style, and produces one landscape ad for digital billboards and one portrait ad for Instagram Reels per matched business. A judge agent scores each ad for quality and adherence to the brief. A web UI shows the AI watching the video, the detection, the agent hand-offs, the verdicts, and the ads, and lets an operator approve or reject each one. The result is that a single hype moment yields ready-to-review ads for every related local business within minutes.

## Core Requirements

- Ingest pre-recorded MP4 clips from `sample_clips/` through a `ClipSource` interface that can later support a live stream.
- Detect hype moments in a clip with a Gemini video-capable model, returning start and end times, a best-frame timestamp, a hype score, a description, the sport, and athlete hints.
- Extract the best frame as a PNG with ffmpeg and store it in the run directory.
- Resolve the athlete from seed data using the hints, and fail explicitly when no confident match exists.
- Match local businesses by tag overlap between the athlete's cuisines and interests and the business tags, then rank candidates with a model re-rank. Never match a business without an overlapping tag.
- Select an ad style from seed data based on the moment and sport.
- Produce an `AdBrief` per matched business and generate two ads per brief: landscape 1920 x 1080 and portrait 1080 x 1920, using a Gemini image model with the hype frame as the hero image, the athlete portrait as an identity reference, business details, and style guidance.
- MVP scope: one athlete (Simone Biles, gymnastics) and one clip, taken through the whole flow before any second athlete or sport is added.
- Judge every generated ad on a fixed rubric (image quality, style adherence, business accuracy, format compliance, brand safety) and regenerate failing ads with the judge's hints up to a retry cap.
- Orchestrate the stages in a pipeline that emits typed events, persists all artifacts and model calls under `output/runs/<run_id>/`, and supports a replay mode that never calls the network.
- Expose the pipeline through a FastAPI service with an SSE event stream, media serving, ad listing with verdicts, and approval decisions.
- Provide a React and Vite web UI with a video player synced to events, an agent timeline, an ad gallery with judge scores, and approve or reject controls, plus export of approved ads.
- Keep all inter-stage data as typed Pydantic models and all seed data in JSON files under `data/`.
- Run on Windows 11 in a Conda environment with Python 3.12, and Node 20 for the frontend.

## Delivery Order

1. `0001-project-scaffold-and-seed-data`: Conda environment, `pyproject.toml`, configuration, Pydantic models, seed JSON files and loaders, CLI entry point.
2. `0002-video-hype-detection`: video agent that analyzes a clip with Gemini, returns `HypeMoment` records, and extracts the best frame with ffmpeg.
3. `0003-context-matching`: matching agent that resolves the athlete, matches businesses, selects an ad style, and emits an `AdBrief` per business.
4. `0004-ad-generation`: ad agent that generates landscape and portrait ads per brief with the Gemini image model and stores `GeneratedAd` records.
5. `0005-ad-quality-judge`: judge agent that scores each ad into a `QualityVerdict` and drives a bounded regeneration loop.
6. `0006-pipeline-orchestration-and-run-store`: orchestrator chaining stages 2 to 5, event bus, run directory layout, and replay mode.
7. `0007-api-and-live-events`: FastAPI service with run management, SSE events, media, ads with verdicts, decisions, and export.
8. `0008-web-ui-and-approval`: React and Vite UI with player, timeline, gallery with scores, approval controls, and export.

## Bar Raisers

- Sport-venue matching: match businesses such as archery ranges by the athlete's sport, not only by food and interests.
- Radio ads: generate a short spoken ad per business with a text-to-speech model.
- Live stream ingestion: an HLS or RTMP `ClipSource` that analyzes rolling windows in near real time.
- Multi-language ad copy for the athlete's home language and English.
- Additional ad formats such as square social posts or vertical billboard sizes.
- A hosted database backend replacing the seed JSON files.
- A/B variants per business and format.

## Non-Goals (Current Scope)

- Live broadcast rights, real-time broadcast ingestion, or any integration with official Olympic feeds.
- Delivering ads to real billboards, Instagram, or any ad network.
- Business onboarding, payments, or self-service portals for businesses.
- User authentication or multi-tenant access control in the web UI.
- A mobile application.
- Production scaling, queueing, or multi-worker deployments.
- Editing generated images in the UI beyond approve or reject.
- Multiple athletes, sports, or clips in the MVP demo. The contracts allow them, but the demo is one athlete and one clip until that flow is proven.
- Any commercial or public use of ads featuring a real athlete's likeness.
