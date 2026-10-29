"""Single source of truth for regulatory constants.

Every value names its guideline. Change a value only with a cited source, a new test and a
major version bump (see the validation-docs skill).
"""

from typing import Final

# ICH Q1E (2003), Appendix B.2.2.1, p. 10: batch poolability significance level (PC-STAB-03)
POOLABILITY_ALPHA: Final[float] = 0.25
# ICH Q1E (2003): confidence level for the bound on the mean regression line
SHELF_LIFE_CONFIDENCE: Final[float] = 0.95
# ICH Q1E (2003), Appendix A: extrapolation limits when statistical analysis is performed
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

# FDA guidance, Dissolution Testing of IR Solid Oral Dosage Forms (1997)
F2_SIMILAR_MIN: Final[float] = 50.0
DISSOLUTION_MIN_UNITS: Final[int] = 12
DISSOLUTION_PLATEAU_PCT: Final[float] = 85.0
CV_LIMIT_EARLY_PCT: Final[float] = 20.0
CV_LIMIT_LATER_PCT: Final[float] = 10.0
# FDA IR dissolution guidance (1997): earlier time points (for example up to 15 minutes) take
# the 20% CV limit; later points take 10%
CV_EARLY_MAX_TIME_MIN: Final[float] = 15.0
# FDA IR dissolution guidance (1997): >= 85% within 15 minutes, profile comparison unnecessary
RAPID_DISSOLUTION_TIME_MIN: Final[float] = 15.0
# FDA IR dissolution guidance (1997): f1 from 0 to 15 is the companion similarity check
F1_SIMILAR_MAX: Final[float] = 15.0

# Shah et al., Pharm Res 1998 - provisional, pending agency text: percentile bootstrap f2
# interval level; similarity when the lower bound (5th percentile) is at least F2_SIMILAR_MIN
BOOTSTRAP_CI_LEVEL: Final[float] = 0.90
# Project policy, not a regulatory value: input guard so the 5th/95th percentiles are stable
BOOTSTRAP_MIN_RESAMPLES: Final[int] = 1000

# ICH M13A (2024): average bioequivalence acceptance range for the 90% CI of the GMR (%)
BE_LOWER_PCT: Final[float] = 80.00
BE_UPPER_PCT: Final[float] = 125.00
BE_CI_LEVEL: Final[float] = 0.90
BE_ROUND_DECIMALS: Final[int] = 2  # confirm for the target agency
# Placeholder, pending confirmation against the target agency text (URS-BE-016): CI limits
# are rounded half up (decimal.ROUND_HALF_UP) to BE_ROUND_DECIMALS before comparison
BE_ROUNDING_MODE: Final[str] = "ROUND_HALF_UP"
# Agencies differ on whether AUC0-inf is decision-making (FDA vs EMA). Placeholder, pending
# confirmation against the target agency text (URS-BE-014): when False, AUC0-inf is reported
# but does not count towards the overall BE verdict
BE_AUC0INF_DECISION_MAKING: Final[bool] = True
# Project policy, not a regulatory value: each sequence needs a subject (URS-BE-012)
BE_MIN_SUBJECTS_PER_SEQUENCE: Final[int] = 1
# Project policy, not a regulatory value: residual df of the ANOVA must be >= 1 (URS-BE-013)
BE_MIN_RESIDUAL_DF: Final[int] = 1

GUIDELINE_VERSIONS: Final[dict[str, str]] = {
    "stability": "ICH Q1E (Step 4, 2003)",
    "dissolution": "FDA IR dissolution guidance (1997)",
    "bioequivalence": "ICH M13A (Step 4, 2024)",
}
