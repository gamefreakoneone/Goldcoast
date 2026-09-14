# Tasks

- [x] Inspect feature ledger, current README, runtime configuration and setup scripts.
- [x] Rewrite README and preserve useful detailed development guidance.
- [x] Add workflow and deployment architecture diagrams.
- [x] Capture and inspect real product screenshots without spending model credits.
- [x] Validate links, images, CLI documentation and staged changes.

## Validation steps
- Run the temporary submission capture script against http://localhost:5173 and inspect all committed screenshots.
- Run a Markdown relative-link checker over changed documentation; require no missing targets.
- Run python -m goldcoast.studio.admin --help and inspect documented subcommands.
- Run git diff --check and review staged file names for unintended files or credentials.
- Record commands and results in status.md.
