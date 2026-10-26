---
name: gxp-review
description: Review uncommitted changes for data integrity (ALCOA+) and regulatory correctness before merging - silent data changes, rounding, missing citations, unseeded randomness, unvalidated input. Use when the user asks for a review, before a release, or after changes to calculations, reports or input handling.
---

# Data-integrity review

Changes under review:

!`git diff HEAD`

Check the diff against each point and report only real findings, each with file, line and a
suggested fix. Mark each finding High, Medium or Low.

1. Attributable and traceable: results carry the app version, guideline version, input hash
   and timestamp; reports show who or what generated them.
2. Original data kept: inputs are never overwritten, filtered, sorted away or imputed without
   being recorded and shown to the user.
3. Accurate: calculations use full precision; rounding happens only at display or report
   time and follows criteria.py.
4. Validated input: pydantic models reject impossible values (negative assay, fewer than
   12 dissolution units, unmatched time points, odd subject counts per sequence).
5. Reproducible: every random step takes a seed and the result records it.
6. Cited: new constants live in criteria.py with guideline and section; new functions cite
   their guideline in the docstring.
7. Tested: changed behaviour has a golden test or a requirement-linked unit test.
8. Honest output: user-facing text never claims the tool is validated for GxP use.

If there are no findings, say "No data-integrity findings" and list what you checked.
