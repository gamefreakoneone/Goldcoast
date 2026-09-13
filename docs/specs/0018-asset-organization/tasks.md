# Tasks

- [x] Add typed product identity and validated editable asset metadata.
- [x] Implement staged categorized uploads, product assignment and retry.
- [x] Populate Today brand summary and update shared contract documentation.
- [x] Validate and record evidence.

## Validation Steps

Run `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`, `pnpm --dir web test`, `pnpm --dir web lint`, and `pnpm --dir web build`. Add regression coverage for stable identities, cross-tenant product assignment, metadata conflicts and upload staging. Inspect the rendered library in Chrome; paid calls are unnecessary for this spec.
