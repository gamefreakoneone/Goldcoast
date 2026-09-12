# Real judge recordings

`direct/` contains the two unchanged judge calls from `output/manual/0005/model_calls/`:
landscape passes at 7, and the creative portrait fails at 4 with a correctly
identified “Billes” typo, unnecessary head cutout, and logo contrast issue.

`loop/` contains all original model calls and immutable image bytes from
`output/manual/0005-loop/model_calls/`. It is the real three-attempt portrait
loop: overall scores 6, 5, 7, with the third attempt passing. No synthetic scores
or generated images are substituted. Tests select call 3 for a first-pass-success
scenario and cap retries at 1 to exercise exhaustion with selection of attempt 1
over the lower-scoring attempt 2. These are explicit alternate replay scenarios.

Inputs are the creative ad fixture's brief/moment/hero plus seed assets. Tests
rebase image paths into their temporary output directory and deny network access.
