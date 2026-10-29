"""Unit tests for dissolution similarity. Each test cites the requirement it proves."""

import math
from datetime import UTC, datetime

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from cmc_stats import __version__, criteria
from cmc_stats.core import dissolution as diss
from cmc_stats.models import (
    BootstrapSettings,
    DissolutionInput,
    DissolutionProfile,
)

TIMES = [5.0, 10.0, 15.0, 20.0, 30.0, 45.0]
REF_MEAN = [20.0, 40.0, 60.0, 75.0, 88.0, 95.0]
TEST_MEAN = [18.0, 37.0, 56.0, 72.0, 86.0, 94.0]
FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def units_around(
    means: list[float], spread: float | list[float] = 0.02, n: int = 12
) -> list[list[float]]:
    """Dummy unit data: n units spread symmetrically around each mean (CV ~ 0.63 * spread)."""
    spreads = spread if isinstance(spread, list) else [spread] * len(means)
    factors = [2 * i / (n - 1) - 1 for i in range(n)]
    return [[m * (1 + s * f) for m, s in zip(means, spreads, strict=True)] for f in factors]


def make_input(
    ref_spread: float | list[float] = 0.02,
    test_spread: float | list[float] = 0.02,
    times: list[float] = TIMES,
    ref_mean: list[float] = REF_MEAN,
    test_mean: list[float] = TEST_MEAN,
) -> DissolutionInput:
    return DissolutionInput(
        reference=DissolutionProfile(
            label="Reference", times_min=times, units=units_around(ref_mean, ref_spread)
        ),
        test=DissolutionProfile(
            label="Test", times_min=times, units=units_around(test_mean, test_spread)
        ),
    )


# High CV at the last two points so the CV check fails at a later (10% limit) point
HIGH_LATE_CV = [0.02, 0.02, 0.02, 0.02, 0.4, 0.4]


# --- URS-DISS-002: f1 and f2 -------------------------------------------------------------


def test_identical_profiles_give_f2_100_and_f1_0() -> None:
    """URS-DISS-002: identical mean profiles give f2 = 100 and f1 = 0."""
    assert diss.f2(REF_MEAN, REF_MEAN) == 100.0
    assert diss.f1(REF_MEAN, REF_MEAN) == 0.0


def test_uniform_10_point_difference_matches_analytic_f2() -> None:
    """URS-DISS-002: a uniform 10-point difference gives 50*log10(100/sqrt(101))."""
    ref = [30.0, 50.0, 70.0]
    test = [40.0, 60.0, 80.0]
    assert diss.f2(ref, test) == pytest.approx(50 * math.log10(100 / math.sqrt(101)), abs=1e-12)
    assert diss.f1(ref, test) == pytest.approx(100 * 30 / 150, abs=1e-12)


def test_f1_f2_reject_unequal_lengths() -> None:
    """URS-DISS-002: f1 and f2 need the same time points in both profiles."""
    with pytest.raises(ValueError, match="same number"):
        diss.f2([1.0, 2.0], [1.0])
    with pytest.raises(ValueError, match="same number"):
        diss.f1([1.0, 2.0], [1.0])


def test_f1_rejects_zero_reference_sum() -> None:
    """URS-DISS-002: f1 is undefined when the reference sum is zero; raise, do not return inf."""
    with pytest.raises(ValueError, match="zero"):
        diss.f1([0.0, 0.0], [1.0, 2.0])


def test_f1_f2_reject_empty_profiles() -> None:
    """URS-DISS-002: f1 and f2 need at least one time point."""
    with pytest.raises(ValueError, match="at least one"):
        diss.f2([], [])
    with pytest.raises(ValueError, match="at least one"):
        diss.f1([], [])


profile_values = st.floats(min_value=0.0, max_value=110.0, allow_nan=False)


@given(st.lists(st.tuples(profile_values, profile_values), min_size=1, max_size=12))
def test_f2_is_symmetric_and_at_most_100(pairs: list[tuple[float, float]]) -> None:
    """URS-DISS-002: f2 does not depend on which product is called reference; f2 <= 100."""
    ref = [p[0] for p in pairs]
    test = [p[1] for p in pairs]
    assert diss.f2(ref, test) == diss.f2(test, ref)
    assert diss.f2(ref, test) <= 100.0


@given(
    st.lists(profile_values, min_size=1, max_size=12),
    st.floats(min_value=0.0, max_value=50.0),
    st.floats(min_value=0.01, max_value=50.0),
)
def test_f2_decreases_as_uniform_offset_grows(ref: list[float], d1: float, extra: float) -> None:
    """URS-DISS-002: a larger uniform difference between profiles gives a smaller f2."""
    d2 = d1 + extra
    assert diss.f2(ref, [r + d1 for r in ref]) > diss.f2(ref, [r + d2 for r in ref])


@given(
    st.lists(
        st.tuples(st.floats(min_value=0.1, max_value=110.0), profile_values),
        min_size=1,
        max_size=12,
    )
)
def test_f1_is_non_negative(pairs: list[tuple[float, float]]) -> None:
    """URS-DISS-002: f1 is a sum of absolute differences, so never negative."""
    assert diss.f1([p[0] for p in pairs], [p[1] for p in pairs]) >= 0.0


# --- URS-DISS-001: 85% cut-off -----------------------------------------------------------


def test_truncation_keeps_points_through_first_where_both_reach_85() -> None:
    """URS-DISS-001: keep up to and including the first point where both means are >= 85%."""
    result = diss.truncate_at_85(TIMES, REF_MEAN, TEST_MEAN)
    assert result.included_indices == (0, 1, 2, 3, 4)
    assert result.excluded_indices == (5,)
    assert result.cutoff_time_min == 30.0


def test_truncation_waits_for_both_products() -> None:
    """URS-DISS-001: one product reaching 85% is not enough."""
    result = diss.truncate_at_85([10.0, 20.0, 30.0], [86.0, 90.0, 95.0], [70.0, 84.9, 85.0])
    assert result.included_indices == (0, 1, 2)
    assert result.excluded_indices == ()
    assert result.cutoff_time_min == 30.0


def test_truncation_at_first_point() -> None:
    """URS-DISS-001: both at 85% at the first point leaves one point and lists the rest."""
    result = diss.truncate_at_85([10.0, 20.0], [85.0, 95.0], [85.0, 96.0])
    assert result.included_indices == (0,)
    assert result.excluded_indices == (1,)


def test_truncation_keeps_all_when_85_never_reached() -> None:
    """URS-DISS-001: if 85% is never reached by both, keep every point and say so."""
    result = diss.truncate_at_85([10.0, 20.0], [50.0, 70.0], [55.0, 90.0])
    assert result.included_indices == (0, 1)
    assert result.excluded_indices == ()
    assert result.cutoff_time_min is None
    assert "not reached" in result.reason


# --- URS-DISS-003: CV checks -------------------------------------------------------------


def test_unit_cv_uses_sample_sd() -> None:
    """URS-DISS-003: CV% = 100 * SD(ddof=1) / mean, per time point."""
    units = np.array([[10.0, 50.0], [20.0, 50.0], [30.0, 50.0]])
    cv = diss.unit_cv_pct(units)
    assert cv[0] == pytest.approx(100 * 10.0 / 20.0, abs=1e-12)
    assert cv[1] == 0.0


def test_unit_cv_rejects_zero_mean() -> None:
    """URS-DISS-003: CV is undefined when the mean is zero; raise instead of returning nan."""
    with pytest.raises(ValueError, match="mean"):
        diss.unit_cv_pct(np.zeros((12, 1)))


def test_cv_limit_is_20_up_to_15_minutes_then_10() -> None:
    """URS-DISS-003: 20% applies at t <= 15 min (inclusive), 10% after."""
    check = diss.check_cv(
        np.array(TIMES),
        np.array(units_around(REF_MEAN)),
        np.array(units_around(TEST_MEAN)),
    )
    limits = {p.time_min: p.limit_pct for p in check.points}
    assert limits[15.0] == criteria.CV_LIMIT_EARLY_PCT
    assert limits[20.0] == criteria.CV_LIMIT_LATER_PCT
    assert check.all_pass


def test_cv_just_over_limit_fails_and_just_under_passes() -> None:
    """URS-DISS-003: CV at most the limit passes; above it fails (checked for both products)."""
    # spread s gives CV = s * sd(linspace(-1, 1, 12)); pick s to land either side of 10%
    sd_factor = float(np.std(np.linspace(-1, 1, 12), ddof=1))
    under = 0.0999 / sd_factor
    over = 0.1001 / sd_factor
    times = np.array([20.0])
    good = np.array(units_around([50.0], under))
    bad = np.array(units_around([50.0], over))
    assert diss.check_cv(times, good, good).all_pass
    assert not diss.check_cv(times, good, bad).all_pass
    assert not diss.check_cv(times, bad, good).all_pass


# --- URS-DISS-004, 005, 009: input validation --------------------------------------------


def test_eleven_reference_units_rejected() -> None:
    """URS-DISS-004: fewer than 12 reference units is rejected and the error names the product."""
    with pytest.raises(ValidationError) as exc:
        DissolutionInput(
            reference=DissolutionProfile(
                label="Reference", times_min=TIMES, units=units_around(REF_MEAN, n=11)
            ),
            test=DissolutionProfile(label="Test", times_min=TIMES, units=units_around(TEST_MEAN)),
        )
    message = str(exc.value)
    assert "reference" in message.lower()
    assert "11 units" in message


def test_eleven_test_units_rejected() -> None:
    """URS-DISS-004: fewer than 12 test units is rejected and the error names the product."""
    with pytest.raises(ValidationError) as exc:
        DissolutionInput(
            reference=DissolutionProfile(
                label="Reference", times_min=TIMES, units=units_around(REF_MEAN)
            ),
            test=DissolutionProfile(
                label="Test", times_min=TIMES, units=units_around(TEST_MEAN, n=11)
            ),
        )
    message = str(exc.value)
    assert "test" in message.lower()
    assert "11 units" in message


def test_twelve_units_each_accepted() -> None:
    """URS-DISS-004: exactly 12 units per product is accepted."""
    data = make_input()
    assert len(data.reference.units) == criteria.DISSOLUTION_MIN_UNITS
    assert len(data.test.units) == criteria.DISSOLUTION_MIN_UNITS


def test_time_point_count_mismatch_rejected() -> None:
    """URS-DISS-005: reference and test with different numbers of time points are rejected."""
    with pytest.raises(ValidationError, match="6 time points.*5"):
        DissolutionInput(
            reference=DissolutionProfile(
                label="Reference", times_min=TIMES, units=units_around(REF_MEAN)
            ),
            test=DissolutionProfile(
                label="Test", times_min=TIMES[:5], units=units_around(TEST_MEAN[:5])
            ),
        )


def test_time_point_value_mismatch_rejected() -> None:
    """URS-DISS-005: one differing time point (15 vs 15.5) is rejected and its index listed."""
    test_times = [5.0, 10.0, 15.5, 20.0, 30.0, 45.0]
    with pytest.raises(ValidationError, match="index 2"):
        DissolutionInput(
            reference=DissolutionProfile(
                label="Reference", times_min=TIMES, units=units_around(REF_MEAN)
            ),
            test=DissolutionProfile(
                label="Test", times_min=test_times, units=units_around(TEST_MEAN)
            ),
        )


def test_identical_time_points_accepted() -> None:
    """URS-DISS-005: identical time points are accepted and shared."""
    assert make_input().times_min == tuple(TIMES)


@pytest.mark.parametrize(
    ("times", "units"),
    [
        pytest.param(TIMES, [*units_around(REF_MEAN)[:11], REF_MEAN[:5]], id="ragged-row"),
        pytest.param(TIMES, [*units_around(REF_MEAN)[:11], [math.nan] * 6], id="nan"),
        pytest.param(TIMES, [*units_around(REF_MEAN)[:11], [-1.0] * 6], id="negative"),
        pytest.param([5.0, 10.0, 15.0, 15.0, 30.0, 45.0], units_around(REF_MEAN), id="repeat"),
        pytest.param([0.0, 10.0, 15.0, 20.0, 30.0, 45.0], units_around(REF_MEAN), id="zero"),
        pytest.param([5.0, 10.0, 30.0, 20.0, 15.0, 45.0], units_around(REF_MEAN), id="unsorted"),
        pytest.param([], [], id="empty"),
    ],
)
def test_bad_profile_rejected(times: list[float], units: list[list[float]]) -> None:
    """URS-DISS-009: ragged rows, non-finite or negative values and bad times are rejected."""
    with pytest.raises(ValidationError):
        DissolutionProfile(label="Reference", times_min=times, units=units)


def test_values_above_100_are_kept_not_clipped() -> None:
    """URS-DISS-009: values over 100% are valid assay data and are kept as entered."""
    units = units_around([50.0, 101.5])
    profile = DissolutionProfile(label="Reference", times_min=[10.0, 20.0], units=units)
    assert max(row[1] for row in profile.units) > 101.5


def test_bootstrap_settings_require_seed_and_count() -> None:
    """URS-DISS-007: seed and resample count are required, with no defaults."""
    with pytest.raises(ValidationError):
        BootstrapSettings(n_resamples=2000)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BootstrapSettings(seed=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        BootstrapSettings(seed=1, n_resamples=criteria.BOOTSTRAP_MIN_RESAMPLES - 1)


# --- URS-DISS-006: rapid dissolution -----------------------------------------------------


def test_rapid_dissolution_flagged_without_f2_verdict() -> None:
    """URS-DISS-006: both >= 85% within 15 min gives a flag and no f2 verdict."""
    times = [5.0, 10.0, 15.0, 20.0]
    data = make_input(
        times=times, ref_mean=[70.0, 88.0, 95.0, 98.0], test_mean=[60.0, 80.0, 90.0, 97.0]
    )
    assert diss.is_rapidly_dissolving(
        np.array(times), np.array([70.0, 88.0, 95.0, 98.0]), np.array([60.0, 80.0, 90.0, 97.0])
    )
    result = diss.compare_profiles(data, timestamp=FIXED_TIME)
    assert result.rapid_dissolution
    assert result.decision_basis == "rapid_dissolution"
    assert result.f2 is None
    assert result.f2_similar is None


def test_one_product_reaching_85_after_15_min_is_not_rapid() -> None:
    """URS-DISS-006: the flag needs both products at >= 85% by 15 min."""
    assert not diss.is_rapidly_dissolving(
        np.array([10.0, 15.0, 20.0]), np.array([88.0, 95.0, 98.0]), np.array([70.0, 84.0, 90.0])
    )


# --- URS-DISS-008: f1 companion check ----------------------------------------------------


def test_f1_limit_is_inclusive_at_15() -> None:
    """URS-DISS-008: f1 exactly 15 is within the companion limit; f2 alone decides similarity."""
    # 3 points, reference sum 200, absolute differences sum 30 -> f1 = 15 exactly
    ref = [40.0, 70.0, 90.0]
    test = [30.0, 60.0, 80.0]
    assert diss.f1(ref, test) == 15.0
    assert diss.f1_within_limit(15.0)
    assert not diss.f1_within_limit(15.000001)


# --- URS-DISS-001/002/003 together: compare_profiles ---------------------------------------


def test_compare_profiles_mean_f2_path() -> None:
    """URS-DISS-001, URS-DISS-002, URS-DISS-003: low CV uses mean-data f2 on truncated points."""
    result = diss.compare_profiles(make_input(), timestamp=FIXED_TIME)
    assert result.decision_basis == "mean_f2"
    assert result.n_points_used == 5
    assert result.f2 == pytest.approx(diss.f2(REF_MEAN[:5], TEST_MEAN[:5]), abs=1e-9)
    assert result.f2_similar is True
    assert result.f1_within_limit is True
    assert result.bootstrap is None
    assert result.truncation is not None
    assert result.truncation.excluded_indices == (5,)


def test_compare_profiles_requires_bootstrap_settings_when_cv_fails() -> None:
    """URS-DISS-003, URS-DISS-007: failing CV without a seed raises; no seed is ever invented."""
    with pytest.raises(ValueError, match="seed"):
        diss.compare_profiles(make_input(test_spread=HIGH_LATE_CV), timestamp=FIXED_TIME)


# --- URS-DISS-010: fewer than 3 time points after the cut-off -----------------------------

SLOW_START_TIMES = [10.0, 20.0, 30.0, 45.0]


def test_fewer_than_three_points_after_cutoff_warns() -> None:
    """URS-DISS-010: 2 points left after the 85% cut-off adds a warning; f2 is still given."""
    data = make_input(
        times=SLOW_START_TIMES,
        ref_mean=[60.0, 88.0, 95.0, 98.0],
        test_mean=[55.0, 86.0, 94.0, 97.0],
    )
    result = diss.compare_profiles(data, timestamp=FIXED_TIME)
    assert result.n_points_used == 2
    assert result.f2 is not None
    assert len(result.warnings) == 1
    assert "Only 2 time point(s)" in result.warnings[0]
    assert "three to four or more dissolution time points" in result.warnings[0]


def test_three_points_after_cutoff_do_not_warn() -> None:
    """URS-DISS-010: 3 points after the cut-off give no warning."""
    data = make_input(
        times=SLOW_START_TIMES,
        ref_mean=[60.0, 75.0, 88.0, 98.0],
        test_mean=[55.0, 72.0, 86.0, 97.0],
    )
    result = diss.compare_profiles(data, timestamp=FIXED_TIME)
    assert result.n_points_used == 3
    assert result.warnings == ()


# --- URS-DISS-011 to 014: known limitations -------------------------------------------------

DISSOLUTION_LIMITATIONS = (
    diss.CV_EARLY_LIMITATION_NOTE,
    diss.F2_BOUNDARY_LIMITATION_NOTE,
    diss.VALIDATION_LIMITATION_NOTE,
)


def test_compared_results_carry_known_limitation_notes() -> None:
    """URS-DISS-011, 012, 014: every result with f1/f2 carries the CV reading, f2 = 50 and
    validation-evidence notes; a rapid-dissolution result (no f2) carries none."""
    mean_path = diss.compare_profiles(make_input(), timestamp=FIXED_TIME)
    boot_path = diss.compare_profiles(
        make_input(test_spread=HIGH_LATE_CV), BootstrapSettings(seed=1, n_resamples=1000)
    )
    for result in (mean_path, boot_path):
        for note in DISSOLUTION_LIMITATIONS:
            assert note in result.notes
            assert note.startswith("Known limitation:")
    rapid = diss.compare_profiles(
        make_input(ref_mean=[60, 90, 95, 97, 98, 99], test_mean=[58, 88, 94, 96, 98, 99])
    )
    assert rapid.rapid_dissolution is True
    assert rapid.notes == ()
    assert "e.g., 15 minutes" in diss.CV_EARLY_LIMITATION_NOTE
    assert "greater than 50 (50-100)" in diss.F2_BOUNDARY_LIMITATION_NOTE
    assert "v1.1" in diss.VALIDATION_LIMITATION_NOTE


def test_f2_exactly_50_is_treated_as_similar(monkeypatch: pytest.MonkeyPatch) -> None:
    """URS-DISS-012: the guidance's "greater than 50 (50-100)" is read as inclusive, so f2 = 50
    exactly is similar (known limitation; logic unchanged)."""
    monkeypatch.setattr(diss, "f2", lambda reference, test: 50.0)
    result = diss.compare_profiles(make_input(), timestamp=FIXED_TIME)
    assert result.f2 == 50.0
    assert result.f2_similar is True


def test_bootstrap_path_notes_fda_does_not_describe_bootstrap() -> None:
    """URS-DISS-013: when bootstrap f2 decides, the result notes that FDA 1997 does not describe
    it, quotes section V.B and says the FDA-named MSD method is not in v1."""
    boot = diss.compare_profiles(
        make_input(test_spread=HIGH_LATE_CV), BootstrapSettings(seed=1, n_resamples=1000)
    )
    note = diss.BOOTSTRAP_LIMITATION_NOTE
    assert note in boot.notes
    assert note.startswith("Known limitation:")
    assert "more than 15% CV" in note
    assert "MSD" in note
    assert "not in v1" in note
    assert note not in diss.compare_profiles(make_input()).notes


def test_dissolution_functions_cite_section_v_a() -> None:
    """URS-DISS-002 (PC-DISS-02): f1/f2 rules cite FDA 1997 section V.A."""
    for func in (diss.f1, diss.f2, diss.check_cv, diss.truncate_at_85, diss.compare_profiles):
        assert func.__doc__ is not None
        assert "section V.A" in func.__doc__


# --- URS-DISS-007: bootstrap f2 ----------------------------------------------------------


def test_bootstrap_is_reproducible_and_records_seed() -> None:
    """URS-DISS-007: same seed gives the same interval; seed, count and level are recorded."""
    data = make_input(test_spread=HIGH_LATE_CV)
    settings = BootstrapSettings(seed=20261026, n_resamples=2000)
    first = diss.compare_profiles(data, settings, timestamp=FIXED_TIME)
    second = diss.compare_profiles(data, settings, timestamp=FIXED_TIME)
    assert first == second
    assert first.decision_basis == "bootstrap_f2"
    assert first.bootstrap is not None
    boot = first.bootstrap
    assert boot.seed == 20261026
    assert boot.n_resamples == 2000
    assert boot.ci_level == criteria.BOOTSTRAP_CI_LEVEL
    assert boot.lower <= boot.median <= boot.upper
    assert boot.similar is (boot.lower >= criteria.F2_SIMILAR_MIN)
    assert first.f2_similar is boot.similar
    assert "Shah" in boot.method_note
    assert "provisional" in boot.method_note


def test_bootstrap_different_seed_gives_different_draws() -> None:
    """URS-DISS-007: the seed drives the resampling."""
    ref = np.array(units_around(REF_MEAN[:5]))
    test = np.array(units_around(TEST_MEAN[:5], HIGH_LATE_CV[:5]))
    times = np.array(TIMES[:5])
    a = diss.bootstrap_f2(times, ref, test, BootstrapSettings(seed=1, n_resamples=1000))
    b = diss.bootstrap_f2(times, ref, test, BootstrapSettings(seed=2, n_resamples=1000))
    assert (a.lower, a.upper) != (b.lower, b.upper)


def test_bootstrap_of_identical_units_is_100() -> None:
    """URS-DISS-007: resampling identical products gives f2 = 100 in every resample."""
    units = np.array(units_around(REF_MEAN[:5]))
    result = diss.bootstrap_f2(
        np.array(TIMES[:5]), units, units.copy(), BootstrapSettings(seed=7, n_resamples=1000)
    )
    # Units differ in resamples, so f2 < 100 in general; only the identical-unit case is exact
    assert result.upper <= 100.0
    same = np.tile(np.array(REF_MEAN[:5]), (12, 1))
    exact = diss.bootstrap_f2(
        np.array(TIMES[:5]), same, same.copy(), BootstrapSettings(seed=7, n_resamples=1000)
    )
    assert exact.lower == exact.upper == 100.0


# --- URS-GEN-001, URS-GEN-002: result metadata ---------------------------------------------


def test_result_carries_disclaimer_and_traceability_stamp() -> None:
    """URS-GEN-001, URS-GEN-002: disclaimer, app and guideline versions, input hash, timestamp."""
    result = diss.compare_profiles(make_input(), timestamp=FIXED_TIME)
    meta = result.metadata
    assert "not validated for gxp" in meta.disclaimer.lower()
    assert meta.app_version == __version__
    assert meta.guideline_version == criteria.GUIDELINE_VERSIONS["dissolution"]
    assert meta.timestamp == FIXED_TIME
    assert len(meta.input_hash) == 64
    int(meta.input_hash, 16)


def test_input_hash_tracks_inputs() -> None:
    """URS-GEN-002: same inputs give the same hash; any change to inputs changes it."""
    a = diss.compare_profiles(make_input(), timestamp=FIXED_TIME).metadata.input_hash
    b = diss.compare_profiles(make_input(), timestamp=FIXED_TIME).metadata.input_hash
    c = diss.compare_profiles(make_input(ref_spread=0.03), timestamp=FIXED_TIME)
    assert a == b
    assert a != c.metadata.input_hash


def test_result_keeps_inputs_and_full_precision_means() -> None:
    """URS-GEN-002: the result echoes the inputs unchanged and keeps unrounded means."""
    data = make_input()
    result = diss.compare_profiles(data, timestamp=FIXED_TIME)
    assert result.inputs == data
    expected = np.mean(np.array(data.reference.units), axis=0)
    assert result.mean_reference == tuple(float(x) for x in expected)
