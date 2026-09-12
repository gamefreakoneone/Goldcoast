# Full real pipeline fixture

`20260912-230559-0d2470` is the unchanged first real end-to-end run, copied from
`output/runs/20260912-230559-0d2470`. It used the existing analyzed Simone Biles
manifest, made zero video requests, and produced three moments, six briefs, and
twelve final judged ads. Every model response, original image, generated attempt,
verdict, event, and seed/settings snapshot is retained. No MP4 or secret is included.

Fixture sidecars retain original paths as provenance. RunStore resolves media
against its installed run directory; full replay creates new IDs and run-local
paths, preserving deterministic child suffixes. Tests copy this fixture to an
isolated store and deny all application network connections. On Windows only
Python's internal socketpair connection used to wake the asyncio loop is exempt.
