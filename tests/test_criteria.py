from cmc_stats import criteria


def test_be_range_is_symmetric_on_log_scale() -> None:
    """URS-BE-001: the acceptance range 80.00-125.00% is symmetric around 100% on a log scale."""
    assert criteria.BE_LOWER_PCT * criteria.BE_UPPER_PCT == 10000.0


def test_every_area_has_a_guideline_version() -> None:
    """URS-GEN-002: every result can be stamped with the guideline version it follows."""
    assert set(criteria.GUIDELINE_VERSIONS) == {"stability", "dissolution", "bioequivalence"}
