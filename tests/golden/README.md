# Golden tests

Each `data/GOLD-<AREA>-<NNN>.json` file is one published worked example with its citation,
inputs, expected outputs and tolerance. Tests load every file for their area.

Rules: never edit an expected value to make a test pass; add cases with the `/golden-test`
skill; prefer published examples or independent R/SAS output over values from this code.
