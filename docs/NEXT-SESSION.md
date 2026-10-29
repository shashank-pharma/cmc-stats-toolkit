# Next session (written 2026-10-29, v0.6.0, branch release/1.0.0, not pushed)

Done: PC-STAB-01 confirmed (Q1E App. B.2.2.1 p. 10, pooled full-model MSE); URS-STAB-019
(only p > 0.25 pools); GOLD-STAB-003 regenerated from R (crossing 24.33389941, shelf-life 24);
/verify PASS (355 tests, 99.03%), /gxp-review and /validation-docs run, .mailmap added.
Phase 3 reading of PC-STAB-02..07 is in ~/.claude/plans/phase-3-stability-only-effervescent-sphinx.md.

Next, stability (docs/RELEASE-1.0.0.md):
1. PC-STAB-02: confirmed by Q1A(R2) 2.1.3 p. 2 and 2.2.3 p. 6; update URS-STAB-017,
   criteria.py, warning text (drop "pending confirmation"), then UI-011 test.
2. PC-STAB-03: value 0.25 confirmed; fix criteria.py comment ("section 2.3" is wrong:
   cite Q1E App. B.2.2.1 p. 10).
3. PC-STAB-04: confirmed (Q1E 2.6 p. 7; 2.4.1.2 p. 4 and Appendix A p. 8); add citations.
4. PC-STAB-05, 06: not addressed by the texts; record as known limitations (needs your
   decision and the UI-011 wording rule from RELEASE-1.0.0.md).
5. PC-STAB-07: needs a published shelf-life example with batch data (Q1E/Q1 figures are
   graphs only).
Then dissolution (PC-DISS-01..04), BE (PC-BE-01..04) and PC-GEN-01 (target agency first).
Golden stability regeneration: uv run python tests/golden/r/merge_stability_gold.py.
