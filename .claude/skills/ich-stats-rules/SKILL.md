---
name: ich-stats-rules
description: Regulatory statistics rules for this project - ICH Q1E stability shelf-life and poolability, dissolution f1/f2 and bootstrap f2, and bioequivalence 90% CI and TOST. Use this whenever writing, changing, testing or explaining any calculation in src/cmc_stats/core, criteria.py or tests, even if the request only mentions "stability", "shelf-life", "f2", "dissolution", "BE", "GMR" or "confidence interval".
---

# Regulatory statistics rules

Implement exactly these rules. If something needed is not here, stop and ask the user to
supply the guideline text. Never fill a gap from memory. Put every numeric constant in
`src/cmc_stats/criteria.py` with its source.

## 1. Stability shelf-life (ICH Q1E, 2003)

1. Fit assay (or other attribute) against time by least squares, per batch.
2. Poolability, tested at significance level 0.25 (ANCOVA):
   - First test equality of slopes (batch x time interaction) using the full model's error.
   - Only p > 0.25 pools; p <= 0.25 rejects equality (user decision 2026-10-29; ICH Q1A(R2)
     2.1.9 and 2.2.9 "more than 0.25"; ICH Q1 Step 2 draft Annex 2 p. A2-6; URS-STAB-019).
   - If slope p > 0.25, refit with a common slope and test equality of intercepts, using the
     common-slope model's residual error (sequential ANCOVA; confirmed by the user 2026-10-27).
   - Both p > 0.25: pool all batches into one line.
   - Slopes equal, intercepts differ: common slope, separate intercepts; worst batch governs.
   - Slopes differ: individual intercepts and individual slopes with the pooled mean square
     error calculated from all batches (the full ANCOVA model, df = N - 2k); the batch that
     reaches the limit first governs. ICH Q1E (2003) Appendix B.2.2.1 (also B.2.1), p. 10;
     confirmed against the Q1E text 2026-10-29. A batch's own error (df = n - 2) is not used.
3. Shelf-life is the earliest time the 95% confidence bound for the mean line meets the
   acceptance criterion (ICH Q1E 2.6, p. 7, confirmed 2026-10-29):
   - One-sided lower bound for an attribute expected to decrease (assay).
   - One-sided upper bound for an attribute expected to increase (degradants).
   - Two-sided 95% interval when the attribute may move either way.
4. Extrapolation beyond the long-term data follows the ICH Q1E Appendix A decision tree.
   Common case (no significant change at accelerated, statistical analysis performed):
   up to 2x the long-term period, but not more than 12 months beyond it. Without statistical
   analysis: up to 1.5x, but not more than 6 months beyond. Implement the other branches only
   after the user provides the decision-tree text. Q1E 2.4.1.2, p. 4, and Appendix A, p. 8
   (confirmed 2026-10-29) add "or if refrigerated, Y = up to 1.5X, but not exceeding X + 6
   months"; v1 supports room temperature only (known limitation, Shashank 2026-10-29,
   URS-STAB-020). X, "period covered by long-term data", is taken as the shortest batch
   coverage (known limitation, URS-STAB-021).
5. Report the model chosen, both p-values, degrees of freedom, the t value used, the
   crossing time and the proposed shelf-life (rounded down to whole months).

Note: ICH Q1 is being consolidated (Step 2 draft, 11 April 2025). Keep Q1A(R2) and Q1E as the
rule set until the user confirms the final text, and store the guideline version in each result.
Known limitation (Shashank, 2026-10-29, PC-STAB-06, URS-STAB-024): re-check these rules when
ICH Q1 reaches Step 4 or is adopted by FDA. v1 requires the storage condition and refuses
refrigerated, freezer and significant change at accelerated (URS-STAB-022, 023).

## 2. Dissolution similarity

- f1 = 100 * sum(|R_t - T_t|) / sum(R_t)
- f2 = 50 * log10(100 / sqrt(1 + (1/n) * sum((R_t - T_t)^2)))
- f2 from 50 to 100 means similar. f1 up to 15 is the usual companion check.
- Conditions for using mean data (FDA IR dissolution guidance, 1997):
  - At least 12 units of each product; identical time points and conditions.
  - Use only one time point after both products reach 85% dissolved.
  - CV at earlier points (for example up to 15 minutes) at most 20%; other points at most 10%.
  - If both products dissolve 85% or more within 15 minutes, profile comparison is
    usually unnecessary: flag this instead of calculating f2.
- When CV conditions fail: bootstrap f2. Resample units with replacement, recompute f2,
  report the percentile 90% interval; similarity if the 5th percentile is at least 50.
  Take the number of resamples and the seed as inputs and return both. Target agency is US
  FDA with ICH as the harmonised base; EMA differences are notes only (Shashank, 2026-10-29,
  PC-GEN-01, URS-GEN-005). FDA 1997 does not describe bootstrap f2: V.B (pp. 9-10) names a
  multivariate model independent procedure for within-batch CV above 15%, which is not in v1.
  Bootstrap f2 stays supplementary and provisional (known limitation, PC-DISS-01,
  URS-DISS-013).
- Section and readings (Shashank, 2026-10-29): f1/f2, 12 units, the 85% rule and CV limits
  are FDA 1997 section V.A, pp. 8-9 (PC-DISS-02). "Earlier time points (e.g., 15 minutes)"
  is read as t <= 15 min (known limitation, PC-DISS-03, URS-DISS-011). "f2 values greater
  than 50 (50-100)" is read as inclusive: f2 = 50 is similar (known limitation,
  URS-DISS-012). Warn when fewer than 3 points remain after the 85% cut-off ("three to four
  or more dissolution time points"; subsection pending confirmation, URS-DISS-010).

## 3. Bioequivalence, 2x2 crossover (ICH M13A, 2024; FDA BE statistics guidance)

- Log-transform AUC0-t, AUC0-inf and Cmax.
- ANOVA terms: sequence, subject nested in sequence, period, treatment.
- Point estimate and 90% CI of the Test/Reference geometric mean ratio = exp(difference).
- Bioequivalent when the 90% CI lies within 80.00-125.00% for each required parameter.
  Equivalent to two one-sided tests at alpha 0.05; report both TOST p-values.
- Report within-subject CV = sqrt(exp(MSE) - 1) * 100.
- Compare CI limits after rounding to two decimals; confirm the rounding rule for the target
  agency and store it in criteria.py.
- Out of scope for version 1: replicate designs, reference-scaled limits (highly variable
  and narrow therapeutic index drugs), parallel designs. Refuse these with a clear message.

## Coding consequences

- Each function docstring names the guideline and section it implements.
- Return result objects (pydantic) that include inputs, settings, version and every
  intermediate value a reviewer would check.
