# Golden tests

Each `data/GOLD-<AREA>-<NNN>.json` file is one published worked example with its citation,
inputs, expected outputs and tolerance. Tests load every file for their area.

Rules: never edit an expected value to make a test pass; add cases with the `/golden-test`
skill; prefer published examples or independent R/SAS output over values from this code.

Stability R reference: `tests/golden/r/stability_gold.R` computes GOLD-STAB-001..003, and
`uv run python tests/golden/r/merge_stability_gold.py` runs it and writes R's `expected`
objects into the JSON files (inputs and R version checked; curated `source` and `crosscheck`
text kept). Review `git diff tests/golden/data` afterwards; an empty diff means the committed
values are exactly R's output.

Dissolution R reference: `tests/golden/r/dissolution_gold.R` reproduces GOLD-DISS-001 from
base R, and `uv run python tests/golden/r/merge_dissolution_gold.py` writes R's `expected`
values (3 decimals, the committed precision) into the JSON file the same way.
