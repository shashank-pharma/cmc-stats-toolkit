# Next session (written 2026-10-29, v0.7.0, branch release/1.0.0, not pushed)

Done: PC-STAB-01 confirmed (Q1E App. B.2.2.1 p. 10, pooled full-model MSE); URS-STAB-019
(only p > 0.25 pools); GOLD-STAB-003 regenerated from R (crossing 24.33389941, shelf-life 24);
/verify PASS (355 tests, 99.03%), /gxp-review and /validation-docs run, .mailmap added.
Phase 3 reading of PC-STAB-02..07 is in ~/.claude/plans/phase-3-stability-only-effervescent-sphinx.md.

Next, stability (docs/RELEASE-1.0.0.md):
1. DONE 2026-10-29 (0.7.0): PC-STAB-02 and PC-STAB-03 closed
   in the register; URS-STAB-017, criteria.py, warning text and UI-011 test updated.
2. DONE 2026-10-29: PC-STAB-04 confirmed (with refrigerated-branch known limitation,
   URS-STAB-020); PC-STAB-05 known limitation (URS-STAB-021); URS-UI-011 promotes
   "known limitation".
3. DONE 2026-10-29 (0.7.0): PC-STAB-06 known limitation (URS-STAB-024); storage condition
   (URS-STAB-022) and significant change (URS-STAB-023) refused at input; 2.2.9 page fixed.
4. PC-STAB-07: needs a published shelf-life example with batch data (Q1E/Q1 figures are
   graphs only).
Then dissolution (PC-DISS-01..04), BE (PC-BE-01..04) and PC-GEN-01 (target agency first).
Golden stability regeneration: uv run python tests/golden/r/merge_stability_gold.py.
