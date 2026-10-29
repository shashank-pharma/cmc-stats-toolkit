# Next session (written 2026-10-29, after v0.8.0, branch release/1.0.0, not pushed)

Done this session (decisions by Shashank, 2026-10-29; user checked the PDFs; see CHANGELOG 0.8.0):
- PC-STAB-08 confirmed: ICH Q1A(R2) "Current Step 4 version dated 6 February 2003". Stability
  stamp now "ICH Q1A(R2) (Step 4, 6 February 2003) + ICH Q1E (Step 4, 6 February 2003)"
  (URS-STAB-026).
- PC-DISS-05 confirmed: "three to four or more dissolution time points" is FDA 1997 section
  V.A, p. 9 (URS-DISS-010). The warning no longer says "pending confirmation"; it is shown in
  its own warning box rather than promoted under URS-UI-011.
- PC-DISS-04 (still a known limitation): `tests/golden/r/dissolution_gold.R` reproduces
  GOLD-DISS-001 from base R (R 4.6.1; f2 70.597718524, f1 5.572755418).
  `uv run python tests/golden/r/merge_dissolution_gold.py` regenerated the JSON; `git diff
  tests/golden/data` was empty. R writes 3 decimals, the committed precision (tolerance 0.001).
  Note and URS-DISS-014 now say "cross-checked against base R; published example planned for
  v1.1". There is still no bootstrap golden case. The GOLD-DISS-001 `source` field still says
  "Hand calculation ... replace with a published worked example" and was left unchanged so
  the regeneration diff stayed empty. Decide whether to reword it.
- Version 0.8.0 (pre-1.0 minor bump: `/dissolution` response gained `warnings`).
- /verify PASS: 391 tests (10 golden), coverage 99.24%. /gxp-review and /validation-docs not run.

Still open for 1.0.0 (docs/RELEASE-1.0.0.md):
1. BE: PC-BE-01..04, now against FDA text.
Then: /gxp-review, /validation-docs.
Golden regeneration: uv run python tests/golden/r/merge_stability_gold.py and
uv run python tests/golden/r/merge_dissolution_gold.py.
