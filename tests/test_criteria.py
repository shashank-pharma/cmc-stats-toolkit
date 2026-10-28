import pytest

from cmc_stats import criteria


def test_be_range_is_symmetric_on_log_scale() -> None:
    """URS-BE-001: the acceptance range 80.00-125.00% is symmetric around 100% on a log scale."""
    assert criteria.BE_LOWER_PCT * criteria.BE_UPPER_PCT == 10000.0


def test_tost_alpha_is_derived_as_0_05_from_the_90_percent_ci() -> None:
    """URS-BE-003: each one-sided test runs at (1 - 0.90) / 2 = 0.05."""
    assert criteria.BE_CI_LEVEL == 0.90
    assert pytest.approx(0.05) == (1 - criteria.BE_CI_LEVEL) / 2


def test_ci_limits_rounded_half_up_to_two_decimals() -> None:
    """URS-BE-016: two decimals, round half up (placeholder pending agency text)."""
    assert criteria.BE_ROUND_DECIMALS == 2
    assert criteria.BE_ROUNDING_MODE == "ROUND_HALF_UP"


def test_be_minimums_and_auc0inf_placeholder() -> None:
    """URS-BE-012, URS-BE-013, URS-BE-014: project-policy minimums and AUC0-inf default."""
    assert criteria.BE_MIN_SUBJECTS_PER_SEQUENCE == 1
    assert criteria.BE_MIN_RESIDUAL_DF == 1
    assert criteria.BE_AUC0INF_DECISION_MAKING is True


def test_dissolution_time_constants_match_15_minutes() -> None:
    """URS-DISS-003, URS-DISS-006: early-CV and rapid-dissolution cut-offs are 15 minutes."""
    assert criteria.CV_EARLY_MAX_TIME_MIN == 15.0
    assert criteria.RAPID_DISSOLUTION_TIME_MIN == 15.0


def test_f1_companion_limit() -> None:
    """URS-DISS-008: f1 companion limit is 15."""
    assert criteria.F1_SIMILAR_MAX == 15.0


def test_bootstrap_interval_is_90_percent() -> None:
    """URS-DISS-007: percentile 90% interval, so the lower bound is the 5th percentile."""
    assert criteria.BOOTSTRAP_CI_LEVEL == 0.90


def test_poolability_alpha_is_0_25() -> None:
    """URS-STAB-002: slopes and intercepts are tested at significance 0.25."""
    assert criteria.POOLABILITY_ALPHA == 0.25


def test_shelf_life_bound_is_one_sided_95() -> None:
    """URS-STAB-003: the bound on the mean is one-sided 95%."""
    assert criteria.SHELF_LIFE_CONFIDENCE == 0.95


def test_extrapolation_cap_is_2x_but_at_most_12_months_beyond() -> None:
    """URS-STAB-004: Appendix A, statistical analysis performed: 2x, at most 12 months more."""
    assert criteria.EXTRAPOLATION_FACTOR_STATS == 2.0
    assert criteria.EXTRAPOLATION_MAX_EXTRA_MONTHS_STATS == 12


def test_batch_minimum_and_primary_batch_warning_threshold() -> None:
    """URS-STAB-009, URS-STAB-017: reject below 2 batches; warn below 3 primary batches."""
    assert criteria.STABILITY_MIN_BATCHES == 2
    assert criteria.STABILITY_PRIMARY_BATCHES == 3


def test_every_area_has_a_guideline_version() -> None:
    """URS-GEN-002: every result can be stamped with the guideline version it follows."""
    assert set(criteria.GUIDELINE_VERSIONS) == {"stability", "dissolution", "bioequivalence"}
