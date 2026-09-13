# Tasks: marketing workspace

- [x] Read requirements/design and relevant frontend skills.
- [x] Generate and inspect main, brand and review design concepts; record design tokens.
- [x] Implement typed OIDC/client/SSE and private media handling.
- [x] Implement all workspace screens and backend-connected actions.
- [x] Validate frontend types/lint/tests and backend route compatibility.
- [x] Run API/frontend/worker and verify onboarding, login, workflow and review in Chrome.
- [x] Compare rendered screenshots with concept images, fix responsive/visual issues, record evidence and commit.

## Validation Steps

`pnpm --dir web test`

`pnpm --dir web lint`

`pnpm --dir web build`

Run studio API on 8001, Vite on 5173 and worker; use Chrome computer use for actual OIDC login, profile save, image upload, brand confirmation, workflow start/history and review controls. Capture desktop and mobile states and compare with concept files using view_image. Live provider validation consumes at most one explicitly allocated brand analysis and campaign; keep global live disabled afterward. Packaged replay installation follows in 0016.
