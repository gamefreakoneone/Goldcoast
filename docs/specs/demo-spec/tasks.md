# Tasks

Sample spec: format reference only, not tracked in FEATURE_STATUS. Copy these headings into a numbered spec's `tasks.md`.

## Task List

An ordered checkbox list. Each task is small enough to complete and verify on its own and names the files it touches. Check tasks off as they are completed and update `status.md` in the same change.

- [ ] Add the models or schema changes this spec needs.
- [ ] Implement the component.
- [ ] Add the CLI or API surface.
- [ ] Add tests that run in replay mode.
- [ ] Update `README.md` if setup, run, or test commands changed.

## Validation Steps

The exact commands to run and what a pass looks like. These are run before committing and their output is recorded in `status.md`.

```powershell
conda activate goldcoast
pytest tests/test_<feature>.py
ruff check .
python -m goldcoast <command> <input>
```

## Definition of Done

- All tasks above are checked.
- All validation steps pass and their output is recorded in `status.md`.
- `docs/FEATURE_STATUS.md` shows this spec as Completed with a link to the evidence.
- The spec is committed on its own.
