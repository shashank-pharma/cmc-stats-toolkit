# Next session (written 2026-10-29, after v0.7.0, unreleased, branch release/1.0.0, not pushed)

Done this session (decisions by Shashank, 2026-10-29; see CHANGELOG "Unreleased"):
- PC-STAB-07 known limitation (URS-STAB-025). Stability stamp now
  "ICH Q1A(R2) (Step 4, 2003) + ICH Q1E (Step 4, 6 February 2003)" (URS-STAB-026).
- PC-GEN-01 confirmed: US FDA, ICH as harmonised base, EMA as notes only (URS-GEN-005).
- PC-DISS-02 confirmed (V.A, pp. 8-9; all citations fixed). PC-DISS-01, 03, 04 and the new
  PC-DISS-06 (f2 = 50 treated as similar) recorded as known limitations (URS-DISS-011..014),
  each shown in the warning box. URS-DISS-010: warning below 3 points after the 85% cut-off.
- /verify PASS: 391 tests, coverage 99.24%. /gxp-review and /validation-docs not run.

Correction to flag: PC-DISS-04 was decided as "golden values cross-checked against base R", but
GOLD-DISS-001 is a hand calculation and there is no bootstrap golden case. Base R reproduces
GOLD-DISS-001 (f2 70.597718524, f1 5.572755418); no R script is committed. The register and
note state this. Decide whether to commit tests/golden/r/dissolution_gold.R.

Still open for 1.0.0 (docs/RELEASE-1.0.0.md):
1. PC-STAB-08: ICH Q1A(R2) Step 4 day and month for the stamp (cover page check).
2. PC-DISS-05: subsection and page for "three to four or more dissolution time points".
3. BE: PC-BE-01..04, now against FDA text.
Then: version bump (0.8.0 under the pre-1.0 policy), /gxp-review, /validation-docs.
Golden stability regeneration: uv run python tests/golden/r/merge_stability_gold.py.
