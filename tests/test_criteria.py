from cmc_stats import criteria


def test_be_range_is_symmetric_on_log_scale() -> None:
    """URS-BE-001: the acceptance range 80.00-125.00% is symmetric around 100% on a log scale."""
    assert criteria.BE_LOWER_PCT * criteria.BE_UPPER_PCT == 10000.0


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


def test_every_area_has_a_guideline_version() -> None:
    """URS-GEN-002: every result can be stamped with the guideline version it follows."""
    assert set(criteria.GUIDELINE_VERSIONS) == {"stability", "dissolution", "bioequivalence"}
