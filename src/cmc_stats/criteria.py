"""Single source of truth for regulatory constants.

Every value names its guideline. Change a value only with a cited source, a new test and a
major version bump (see the validation-docs skill).
"""

from typing import Final

# ICH Q1E (2003), Appendix B.2.2.1, p. 10: batch poolability significance level (PC-STAB-03)
POOLABILITY_ALPHA: Final[float] = 0.25
# ICH Q1E (2003), 2.6, p. 7: "the lower one-sided 95 percent confidence limit" for an attribute
# known to decrease (PC-STAB-04)
SHELF_LIFE_CONFIDENCE: Final[float] = 0.95
# ICH Q1E (2003), 2.4.1.2, p. 4, and Appendix A, p. 8: "Y = up to 2X, but not exceeding X + 12
# months" (no significant change at accelerated, statistical analysis performed; PC-STAB-04).
# Room temperature only: the refrigerated 1.5X / X + 6 branch (2.5.1.1, p. 6) is a known
# limitation (URS-STAB-020).
EXTRAPOLATION_FACTOR_STATS: Final[float] = 2.0
EXTRAPOLATION_MAX_EXTRA_MONTHS_STATS: Final[int] = 12
# ICH Q1A(R2) (2003), Selection of Batches: 2.1.3 (drug substance), p. 2, and 2.2.3 (drug
# product), p. 6: at least three primary batches. Warning only (URS-STAB-017, PC-STAB-02).
STABILITY_PRIMARY_BATCHES: Final[int] = 3
# Project policy, not a regulatory value: minimum for the poolability tests (URS-STAB-009)
STABILITY_MIN_BATCHES: Final[int] = 2
# Project policy, not a regulatory value: at least 1 residual df per batch fit (URS-STAB-010)
STABILITY_MIN_POINTS_PER_BATCH: Final[int] = 3
# Project policy, not a regulatory value: a slope needs 2 distinct times (URS-STAB-011)
STABILITY_MIN_DISTINCT_TIMES: Final[int] = 2

# FDA guidance, Dissolution Testing of Immediate Release Solid Oral Dosage Forms (1997),
# section V.A, pp. 8-9 (PC-DISS-02): 12 units each; "Only one measurement should be considered
# after 85% dissolution of both the products"; f2 "greater than 50 (50-100)" means similar,
# read as inclusive of 50 (known limitation, URS-DISS-012)
F2_SIMILAR_MIN: Final[float] = 50.0
DISSOLUTION_MIN_UNITS: Final[int] = 12
DISSOLUTION_PLATEAU_PCT: Final[float] = 85.0
CV_LIMIT_EARLY_PCT: Final[float] = 20.0
CV_LIMIT_LATER_PCT: Final[float] = 10.0
# FDA IR dissolution guidance (1997), section V.A: "at the earlier time points (e.g., 15
# minutes) should not be more than 20%". The 15 minutes is an example; t <= 15 min is this
# tool's reading (known limitation, PC-DISS-03, URS-DISS-011)
CV_EARLY_MAX_TIME_MIN: Final[float] = 15.0
# FDA IR dissolution guidance (1997), section V.A: >= 85% within 15 minutes, profile comparison
# unnecessary
RAPID_DISSOLUTION_TIME_MIN: Final[float] = 15.0
# FDA IR dissolution guidance (1997), section V.A: f1 from 0 to 15 is the companion check
F1_SIMILAR_MAX: Final[float] = 15.0
# FDA IR dissolution guidance (1997), section V.A, p. 9: f2 is "most suitable for dissolution
# profile comparison when three to four or more dissolution time points are available"
# (PC-DISS-05). Warn (not refuse) below 3 points after the 85% cut-off (URS-DISS-010)
DISSOLUTION_MIN_TIME_POINTS: Final[int] = 3

# Shah et al., Pharm Res 1998 - provisional, pending agency text: percentile bootstrap f2
# interval level; similarity when the lower bound (5th percentile) is at least F2_SIMILAR_MIN.
# FDA IR dissolution guidance (1997) does not describe bootstrap f2 (known limitation,
# PC-DISS-01, URS-DISS-013)
BOOTSTRAP_CI_LEVEL: Final[float] = 0.90
# Project policy, not a regulatory value: input guard so the 5th/95th percentiles are stable
BOOTSTRAP_MIN_RESAMPLES: Final[int] = 1000

# BE sources (PC-BE-01..03, quotes confirmed by the user, Shashank 2026-11-03): ICH M13A (2024)
# and FDA, Statistical Approaches to Establishing Bioequivalence (May 2026), "FDA (May 2026)".
# ICH M13A (2024), 2.2.4, p. 13: acceptance range 80.00-125.00% for the 90% CI of the GMR
BE_LOWER_PCT: Final[float] = 80.00
BE_UPPER_PCT: Final[float] = 125.00
# ICH M13A (2024), 2.2.3.1, pp. 11-12: 90% CI on the log scale, equivalent to two one-sided
# tests at the 5% level
BE_CI_LEVEL: Final[float] = 0.90
# FDA (May 2026), I.B footnote 6, p. 3: "the rounded confidence interval value should be at
# least 80.00 percent and not more than 125.00 percent" (PC-BE-01). EMA 4.1.8 (p. 15/27),
# "when rounded to two decimal places", is a note only (URS-GEN-005)
BE_ROUND_DECIMALS: Final[int] = 2
# No guidance states the rounding mode: rounding half up (decimal.ROUND_HALF_UP) is this tool's
# choice (known limitation, PC-BE-01, URS-BE-016, URS-BE-020)
BE_ROUNDING_MODE: Final[str] = "ROUND_HALF_UP"
# FDA (May 2026), II.C.2, p. 13, "Statistical Information and Implementation of Criteria for
# PK Measures (AUC0-t, AUC0-∞, and Cmax)": AUC0-inf is decision-making (PC-BE-02, URS-BE-014).
# Notes only: ICH M13A 2.2.2.2 (p. 11) lists AUC(0-inf) as an additional parameter; EMA 4.1.8
# (p. 15/27) analyses only AUC(0-t) and Cmax. The FDA ANDA PK-endpoints guidance cited in
# footnote 6 was not checked (known limitation, URS-BE-021). When False, AUC0-inf is reported
# but does not count towards the overall BE verdict
BE_AUC0INF_DECISION_MAKING: Final[bool] = True
# ICH M13A (2024), 2.2.3.1, p. 12: a crossover study is not acceptable with fewer than 12
# evaluable subjects (URS-BE-019)
BE_MIN_EVALUABLE_SUBJECTS: Final[int] = 12
# Project policy, not a regulatory value: each sequence needs a subject (URS-BE-012)
BE_MIN_SUBJECTS_PER_SEQUENCE: Final[int] = 1
# Project policy, not a regulatory value: residual df of the ANOVA must be >= 1 (URS-BE-013)
BE_MIN_RESIDUAL_DF: Final[int] = 1

# User decision (Shashank, 2026-10-29; PC-GEN-01, URS-GEN-005): the tool follows US FDA
# expectations with ICH as the harmonised base; EMA differences are recorded as notes only
TARGET_AGENCY: Final[str] = "US FDA (ICH as the harmonised base)"

# Stability stamp (URS-STAB-026): the Step 4 date shown on both ICH Q1A(R2) ("Current Step 4
# version dated 6 February 2003", PC-STAB-08) and ICH Q1E (PC-STAB-01) is 6 February 2003
# (checked by the user)
GUIDELINE_VERSIONS: Final[dict[str, str]] = {
    "stability": "ICH Q1A(R2) (Step 4, 6 February 2003) + ICH Q1E (Step 4, 6 February 2003)",
    "dissolution": "FDA IR dissolution guidance (1997)",
    "bioequivalence": (
        "ICH M13A (Step 4, 2024) + FDA Statistical Approaches to Establishing Bioequivalence "
        "(May 2026)"
    ),
}
