# Kickoff Prompt

Paste the block below into a fresh agent session opened at the repo root. The two MCP servers (context7, playwright) are configured in `.mcp.json` for Claude Code and in `opencode.json` for OpenCode. Claude Code asks you to approve them on first use; OpenCode loads `opencode.json` on startup, so restart it after the file is added and check with `/mcp` or the tools list.

```
Implement specs 0002 through 0008 in numeric order, all in this session, following the working rules in AGENTS.md. Spec 0001 is Completed. Do not ask me questions; make every decision from the spec documents, and where a spec's Open Questions section lists a default, use that default.

Step 0, housekeeping: the working tree has uncommitted planning docs and the Simone Biles seed data. Run validate-seed, pytest, and ruff, then commit everything except .env, output/, and any .mp4 as "0001: planning docs and Simone Biles MVP seed data".

For each spec from 0002 to 0008:
1. Read docs/FEATURE_STATUS.md, then the spec's requirements.md, design.md, and tasks.md in full. Read TECHNICAL_DESIGN.md before touching any shared contract. Mark the spec In progress in FEATURE_STATUS.md and status.md.
2. Implement every task. Tick the checkboxes in tasks.md as you go.
3. Run every command in the spec's Validation Steps. Paste the commands and their relevant output into status.md under Evidence. Manual checks get a one-paragraph description and, for spec 0008, a screenshot saved under output/manual/0008/ taken with the Playwright MCP.
4. Mark the spec Completed in status.md and FEATURE_STATUS.md, then commit that spec on its own with a message starting "NNNN:". Never commit .env, output/, or .mp4 files.
5. Only then start the next spec.

Real inputs are ready. The clip is sample_clips/gymnastics_simone.mp4 (41 MB, so use the Gemini Files API upload path, not inline bytes). Its manifest entry in sample_clips/manifest.json already names athlete_id simone-biles. Seed data, logos, the athlete portrait, and business reference photos are in data/. .env has GEMINI_API_KEY and the three model ids (gemini-3.8-flash for video and judge, gemini-3.1-flash-image for images).

Credits: analyze the clip with Gemini exactly once. After that the manifest entry is analyzed: true and every later run must read from it. Use --force-analysis only if the first analysis is unusable, and say so in status.md. Record the real model calls from the first live run of each stage as the replay fixtures the tests use, so the test suite never hits the network.

Before writing any code that calls the google-genai SDK, use the context7 MCP to pull the current google-genai Python docs and confirm: how to upload a video with the Files API and wait for it to become active, how to request structured JSON output with a response schema, how to pass reference images plus a text prompt to gemini-3.1-flash-image, how to set the output aspect ratio to 16:9 and 9:16, and how to read the image bytes from the response. The SDK surface has changed across versions; trust the docs over memory. If the image model returns a size other than 1920x1080 or 1080x1920 at the right aspect ratio, resize as spec 0004 describes.

Environment: Windows 11, PowerShell. Activate with conda activate goldcoast. Node 22 and pnpm 10 are installed for web/. If pytest fails with a PermissionError creating its temp directory, run it as: pytest -p no:cacheprovider --basetemp output/pytest-tmp

If a spec becomes blocked (for example the image model refuses to render the athlete even after the retry without the portrait), record Blocked with the exact error in status.md and FEATURE_STATUS.md, then apply the fallback the spec's design.md names if one exists and continue. If no fallback exists and later specs depend on it, stop and report.

When all eight specs are Completed, or you are blocked, finish with a report: which specs completed, which are blocked and why, the run id of the end-to-end run, and the exact commands to start the API and the web UI and replay that run for the demo.
```
