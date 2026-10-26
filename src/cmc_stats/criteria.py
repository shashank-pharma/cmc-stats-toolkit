"""Single source of truth for regulatory constants.

Every value names its guideline. Change a value only with a cited source, a new test and a
major version bump (see the validation-docs skill).
"""

from typing import Final

# ICH Q1E (2003), section 2.3 and Appendix B: batch poolability significance level
POOLABILITY_ALPHA: Final[float] = 0.25
# ICH Q1E (2003): confidence level for the bound on the mean regression line
SHELF_LIFE_CONFIDENCE: Final[float] = 0.95
# ICH Q1E (2003), Appendix A: extrapolation limits when statistical analysis is performed
EXTRAPOLATION_FACTOR_STATS: Final[float] = 2.0
EXTRAPOLATION_MAX_EXTRA_MONTHS_STATS: Final[int] = 12

# FDA guidance, Dissolution Testing of IR Solid Oral Dosage Forms (1997)
F2_SIMILAR_MIN: Final[float] = 50.0
DISSOLUTION_MIN_UNITS: Final[int] = 12
DISSOLUTION_PLATEAU_PCT: Final[float] = 85.0
CV_LIMIT_EARLY_PCT: Final[float] = 20.0
CV_LIMIT_LATER_PCT: Final[float] = 10.0

# ICH M13A (2024): average bioequivalence acceptance range for the 90% CI of the GMR (%)
BE_LOWER_PCT: Final[float] = 80.00
BE_UPPER_PCT: Final[float] = 125.00
BE_CI_LEVEL: Final[float] = 0.90
BE_ROUND_DECIMALS: Final[int] = 2  # confirm for the target agency

GUIDELINE_VERSIONS: Final[dict[str, str]] = {
    "stability": "ICH Q1E (Step 4, 2003)",
    "dissolution": "FDA IR dissolution guidance (1997)",
    "bioequivalence": "ICH M13A (Step 4, 2024)",
}
