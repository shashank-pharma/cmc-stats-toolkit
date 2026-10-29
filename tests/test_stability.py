"""Unit tests for ICH Q1E stability shelf-life. Each test cites the requirement it proves."""

import math
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import pytest
import statsmodels.formula.api as smf
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError
from scipy import optimize
from scipy import stats as sps
from statsmodels.stats.anova import anova_lm

from cmc_stats import __version__, criteria
from cmc_stats.core import stability as stab
from cmc_stats.models import DISCLAIMER, StabilityBatch, StabilityInput

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
TIMES = [0.0, 3.0, 6.0, 9.0, 12.0, 18.0, 24.0]
LIMIT = 95.0

# Dummy data supplied by the user (2026-10-27), as in GOLD-STAB-001..003
B001 = [99.9, 99.7, 99.5, 98.6, 98.6, 97.6, 96.6]
B002 = [100.5, 99.8, 99.0, 98.9, 98.5, 97.5, 96.9]
B003_SIMILAR = [100.1, 99.8, 99.5, 98.7, 98.5, 97.5, 96.8]
B003_LOWER_START = [99.4, 99.1, 98.8, 98.0, 97.8, 96.8, 96.1]
B003_FASTER = [100.1, 99.6, 99.1, 98.2, 97.8, 96.4, 95.4]
# Assay that increases: the lower bound never meets 95 (checked with statsmodels)
RISING = {
    "U1": [99.0, 99.3, 99.5, 99.9, 100.1, 100.8, 101.5],
    "U2": [99.2, 99.4, 99.8, 100.0, 100.4, 101.0, 101.6],
    "U3": [98.9, 99.3, 99.6, 99.8, 100.2, 100.9, 101.4],
}


def make_input(
    batches: dict[str, list[float]] | None = None,
    times: dict[str, list[float]] | None = None,
    **overrides: Any,
) -> StabilityInput:
    """Build a StabilityInput; batches default to the pooled case (GOLD-STAB-001 data)."""
    batches = (
        batches
        if batches is not None
        else {
            "B001": B001,
            "B002": B002,
            "B003": B003_SIMILAR,
        }
    )
    times = times or {}
    fields: dict[str, Any] = {
        "attribute": "Assay",
        "unit": "% label claim",
        "direction": "decrease",
        "lower_limit": LIMIT,
        "significant_change_at_accelerated": False,
        "statistical_analysis_performed": True,
        "batches": [
            {"label": k, "times_months": times.get(k, TIMES), "values": v}
            for k, v in batches.items()
        ],
    }
    fields.update(overrides)
    return StabilityInput.model_validate(fields)


def with_b003(b003: list[float]) -> StabilityInput:
    return make_input({"B001": B001, "B002": B002, "B003": b003})


def frame(data: StabilityInput) -> pd.DataFrame:
    """Long data frame for the independent statsmodels cross-checks."""
    rows = [
        (b.label, t, y) for b in data.batches for t, y in zip(b.times_months, b.values, strict=True)
    ]
    return pd.DataFrame(rows, columns=["batch", "time", "y"])


# --- URS-STAB-001: per-batch least-squares fit --------------------------------------------


def test_exact_lines_give_exact_coefficients_and_zero_residual() -> None:
    """URS-STAB-001: data on an exact line gives that line back with zero residual error."""
    data = make_input(
        {
            "A": [100.0 - 0.2 * t for t in TIMES],
            "B": [99.0 - 0.1 * t for t in TIMES],
        }
    )
    fits = stab.fit_batches(data)
    assert [f.label for f in fits] == ["A", "B"]
    assert fits[0].intercept == pytest.approx(100.0, abs=1e-10)
    assert fits[0].slope == pytest.approx(-0.2, abs=1e-12)
    assert fits[1].intercept == pytest.approx(99.0, abs=1e-10)
    assert fits[1].slope == pytest.approx(-0.1, abs=1e-12)
    assert fits[0].mse == pytest.approx(0.0, abs=1e-20)
    assert fits[0].residual_df == len(TIMES) - 2


def test_batch_fit_matches_statsmodels_ols() -> None:
    """URS-STAB-001: coefficients, standard errors and MSE match an independent OLS fit."""
    data = with_b003(B003_FASTER)
    d = frame(data)
    for fit in stab.fit_batches(data):
        ref = smf.ols("y ~ time", d[d.batch == fit.label]).fit()
        assert fit.intercept == pytest.approx(ref.params["Intercept"], abs=1e-10)
        assert fit.slope == pytest.approx(ref.params["time"], abs=1e-12)
        assert fit.intercept_se == pytest.approx(ref.bse["Intercept"], abs=1e-10)
        assert fit.slope_se == pytest.approx(ref.bse["time"], abs=1e-12)
        assert fit.mse == pytest.approx(ref.mse_resid, abs=1e-12)
        assert fit.residual_df == int(ref.df_resid)


def test_replicate_time_points_are_accepted() -> None:
    """URS-STAB-001: replicate results at the same time point are all used in the fit."""
    reps = [0.0, 0.0, 6.0, 6.0, 12.0, 12.0]
    data = make_input(
        {"A": [100.0, 100.2, 99.0, 99.4, 98.1, 98.3], "B": [100.1, 99.9, 99.2, 99.0, 98.0, 98.2]},
        times={"A": reps, "B": reps},
    )
    fit = stab.fit_batches(data)[0]
    assert fit.residual_df == 4
    assert fit.slope == pytest.approx(
        np.polyfit(reps, [100.0, 100.2, 99.0, 99.4, 98.1, 98.3], 1)[0]
    )


def test_data_kept_as_entered_not_sorted() -> None:
    """URS-STAB-001: unsorted input is kept in its order and gives the same fit as sorted."""
    unsorted_times = [12.0, 0.0, 24.0, 6.0, 18.0, 3.0, 9.0]
    order = [TIMES.index(t) for t in unsorted_times]
    data = make_input(
        {"B001": [B001[i] for i in order], "B002": B002},
        times={"B001": unsorted_times},
    )
    assert data.batches[0].times_months == tuple(unsorted_times)
    fit_unsorted = stab.fit_batches(data)[0]
    fit_sorted = stab.fit_batches(make_input({"B001": B001, "B002": B002}))[0]
    assert fit_unsorted.slope == pytest.approx(fit_sorted.slope, abs=1e-12)
    assert fit_unsorted.intercept == pytest.approx(fit_sorted.intercept, abs=1e-10)


# --- URS-STAB-002: poolability ------------------------------------------------------------


@pytest.mark.parametrize("b003", [B003_SIMILAR, B003_LOWER_START, B003_FASTER])
def test_slope_test_matches_statsmodels_with_full_model_error(b003: list[float]) -> None:
    """URS-STAB-002: slope equality F test = anova(common slope, full), full-model error."""
    data = with_b003(b003)
    d = frame(data)
    full = smf.ols("y ~ C(batch) * time", d).fit()
    common = smf.ols("y ~ C(batch) + time", d).fit()
    ref = anova_lm(common, full)
    pool = stab.poolability(data)
    assert pool.alpha == criteria.POOLABILITY_ALPHA
    assert pool.slopes.f_value == pytest.approx(ref["F"].iloc[1], rel=1e-9)
    assert pool.slopes.p_value == pytest.approx(ref["Pr(>F)"].iloc[1], rel=1e-9)
    assert pool.slopes.df_num == 2
    assert pool.slopes.df_den == 15


@pytest.mark.parametrize("b003", [B003_SIMILAR, B003_LOWER_START])
def test_intercept_test_uses_common_slope_error(b003: list[float]) -> None:
    """URS-STAB-002: intercept F test is sequential: common-slope model error, df N-k-1."""
    data = with_b003(b003)
    d = frame(data)
    common = smf.ols("y ~ C(batch) + time", d).fit()
    pooled = smf.ols("y ~ time", d).fit()
    ref = anova_lm(pooled, common)
    k, n = 3, 21
    expected_f = ((pooled.ssr - common.ssr) / (k - 1)) / (common.ssr / (n - k - 1))
    pool = stab.poolability(data)
    assert pool.intercepts is not None
    assert pool.intercepts.df_num == k - 1
    assert pool.intercepts.df_den == n - k - 1 == 17
    assert pool.intercepts.f_value == pytest.approx(expected_f, rel=1e-9)
    assert pool.intercepts.f_value == pytest.approx(ref["F"].iloc[1], rel=1e-9)
    assert pool.intercepts.p_value == pytest.approx(ref["Pr(>F)"].iloc[1], rel=1e-9)


def test_intercepts_not_tested_when_slopes_differ() -> None:
    """URS-STAB-002: when slope p <= 0.25 the intercept test is not run."""
    pool = stab.poolability(with_b003(B003_FASTER))
    assert pool.slopes.p_value < criteria.POOLABILITY_ALPHA
    assert pool.intercepts is None
    assert pool.model == "separate"


@pytest.mark.parametrize(
    ("b003", "model"),
    [
        (B003_SIMILAR, "pooled"),
        (B003_LOWER_START, "common_slope"),
        (B003_FASTER, "separate"),
    ],
)
def test_model_chosen_for_each_branch(b003: list[float], model: str) -> None:
    """URS-STAB-002: pooled, common-slope and separate branches are each chosen correctly."""
    assert stab.poolability(with_b003(b003)).model == model


@pytest.mark.parametrize(
    ("slope_p", "intercept_p", "model"),
    [
        (0.25, None, "separate"),
        (0.2499999, None, "separate"),
        (0.2500001, 0.25, "common_slope"),
        (0.9, 0.25, "common_slope"),
        (0.2500001, 0.2500001, "pooled"),
    ],
)
def test_select_model_rejects_equality_at_p_0_25(
    slope_p: float, intercept_p: float | None, model: str
) -> None:
    """URS-STAB-019: only p > 0.25 pools; p equal to 0.25 rejects equality."""
    assert stab.select_model(slope_p, intercept_p) == model


def test_poolability_tests_intercepts_only_above_0_25(monkeypatch: pytest.MonkeyPatch) -> None:
    """URS-STAB-019: a slope p exactly at alpha rejects equal slopes; intercepts are not tested."""
    data = with_b003(B003_SIMILAR)
    slope_p = stab.poolability(data).slopes.p_value
    assert slope_p > criteria.POOLABILITY_ALPHA
    monkeypatch.setattr(criteria, "POOLABILITY_ALPHA", slope_p)
    pool = stab.poolability(data)
    assert pool.slopes.p_value == slope_p
    assert pool.intercepts is None
    assert pool.model == "separate"


@pytest.mark.parametrize(
    ("model", "label", "message"),
    [("pooled", "B001", "label=None"), ("separate", "B999", "unknown batch label")],
)
def test_bound_rejects_label_not_in_model(model: str, label: str, message: str) -> None:
    """URS-STAB-003: a bound is only given for a line that exists in the chosen model."""
    with pytest.raises(ValueError, match=message):
        stab.lower_bound(with_b003(B003_SIMILAR), model, label, [0.0])


def test_select_model_requires_intercept_p_when_slopes_pool() -> None:
    """URS-STAB-002: slopes poolable but no intercept p-value is a programming error."""
    with pytest.raises(ValueError, match="intercept"):
        stab.select_model(0.5, None)


# --- URS-STAB-003: one-sided 95% lower bound and crossing ---------------------------------


def test_pooled_bound_matches_statsmodels_90_two_sided_lower_limit() -> None:
    """URS-STAB-003: one-sided 95% lower bound = lower limit of the two-sided 90% CI (pooled)."""
    data = with_b003(B003_SIMILAR)
    grid = np.array([0.0, 6.0, 24.0, 36.0])
    ref = smf.ols("y ~ time", frame(data)).fit()
    expected = ref.get_prediction(pd.DataFrame({"time": grid})).conf_int(alpha=0.10)[:, 0]
    actual = stab.lower_bound(data, "pooled", None, grid)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)


def test_common_slope_bound_uses_common_model_for_each_batch() -> None:
    """URS-STAB-003: common-slope bound uses that model's error and df (17)."""
    data = with_b003(B003_LOWER_START)
    grid = np.array([0.0, 12.0, 30.0])
    ref = smf.ols("y ~ C(batch) + time", frame(data)).fit()
    new = pd.DataFrame({"batch": ["B003"] * grid.size, "time": grid})
    expected = ref.get_prediction(new).conf_int(alpha=0.10)[:, 0]
    np.testing.assert_allclose(
        stab.lower_bound(data, "common_slope", "B003", grid), expected, rtol=0, atol=1e-10
    )


@pytest.mark.parametrize("label", ["B001", "B002", "B003"])
def test_separate_bound_uses_full_model_pooled_mse(label: str) -> None:
    """URS-STAB-003: separate model uses each batch's intercept and slope with the pooled mean
    square error of the full model, df N - 2k (ICH Q1E Appendix B.2.2.1, p. 10)."""
    data = with_b003(B003_FASTER)
    grid = np.array([0.0, 12.0, 24.3])
    ref = smf.ols("y ~ C(batch) * time", frame(data)).fit()
    assert ref.df_resid == 15
    new = pd.DataFrame({"batch": [label] * grid.size, "time": grid})
    expected = ref.get_prediction(new).conf_int(alpha=0.10)[:, 0]
    np.testing.assert_allclose(
        stab.lower_bound(data, "separate", label, grid), expected, rtol=0, atol=1e-10
    )


def synthetic_line(slope: float, intercept: float, xtx_inv: list[list[float]]) -> Any:
    """A mean line with mse = 1 (rss 10, df 10) and a chosen (X'X)^-1, for _crossing edges."""
    fit = stab._Fit(coef=np.array([intercept, slope]), xtx_inv=np.array(xtx_inv), rss=10.0, df=10)
    return stab._Line(None, fit, np.array([1.0, 0.0]), np.array([0.0, 1.0]))


def test_crossing_when_quadratic_term_vanishes() -> None:
    """URS-STAB-003: slope^2 = t^2 * mse * q2 makes the equation linear; root found exactly.

    With k = t value, intercept 3k, slope -k, mse 1, (X'X)^-1 = I and limit 0:
    bound(t) = 3k - k t - k sqrt(1 + t^2) = 0 at t = 4/3 (sqrt(1 + 16/9) = 5/3).
    """
    k = float(sps.t.ppf(criteria.SHELF_LIFE_CONFIDENCE, 10))
    line = synthetic_line(slope=-k, intercept=3.0 * k, xtx_inv=[[1.0, 0.0], [0.0, 1.0]])
    crossing = stab._crossing(line, 0.0)
    assert crossing == pytest.approx(4.0 / 3.0, abs=1e-12)
    assert stab._bound(line, np.array([crossing]))[0] == pytest.approx(0.0, abs=1e-9)


def test_crossing_refuses_negative_discriminant() -> None:
    """URS-STAB-003: an impossible (non positive definite) variance raises, never 'no crossing'."""
    k = float(sps.t.ppf(criteria.SHELF_LIFE_CONFIDENCE, 10))
    line = synthetic_line(slope=0.0, intercept=3.0 * k, xtx_inv=[[1.0, 0.0], [0.0, -1.0]])
    with pytest.raises(ValueError, match="negative discriminant"):
        stab._crossing(line, 0.0)


@pytest.mark.parametrize(
    ("b003", "model", "label"),
    [
        (B003_SIMILAR, "pooled", None),
        (B003_LOWER_START, "common_slope", "B001"),
        (B003_LOWER_START, "common_slope", "B003"),
        (B003_FASTER, "separate", "B002"),
        (B003_FASTER, "separate", "B003"),
    ],
)
def test_crossing_agrees_with_numeric_root_of_bound(
    b003: list[float], model: str, label: str | None
) -> None:
    """URS-STAB-003: closed-form crossing equals a brentq root of bound(t) - limit."""
    data = with_b003(b003)
    crossing = stab.crossing_time(data, model, label)
    assert crossing is not None

    def gap(t: float) -> float:
        return float(stab.lower_bound(data, model, label, np.array([t]))[0]) - LIMIT

    root = optimize.brentq(gap, 1.0, 100.0, xtol=1e-14)
    assert crossing == pytest.approx(root, abs=1e-9)
    # earliest crossing: the bound is above the limit everywhere before it
    before = np.linspace(0.0, crossing, 200, endpoint=False)
    assert np.all(stab.lower_bound(data, model, label, before) > LIMIT)


@pytest.mark.parametrize(
    ("b003", "model"), [(B003_LOWER_START, "common_slope"), (B003_FASTER, "separate")]
)
def test_batch_reaching_limit_first_governs(b003: list[float], model: str) -> None:
    """URS-STAB-003: with separate intercepts or slopes, the earliest-crossing batch governs."""
    result = stab.estimate_shelf_life(with_b003(b003), timestamp=FIXED_TIME)
    assert result.poolability.model == model
    crossings = {p.label: p.crossing_months for p in result.per_batch}
    assert result.governing_batch == "B003"
    assert result.crossing_months == min(c for c in crossings.values() if c is not None)


def test_tied_governing_batches_are_all_named() -> None:
    """URS-STAB-003: when batches cross at the same time, all are named; the first governs."""
    data = make_input({"A": B003_FASTER, "B": B003_FASTER, "C": B001})
    result = stab.estimate_shelf_life(data, timestamp=FIXED_TIME)
    assert result.poolability.model == "separate"
    assert result.governing_batch == "A"
    assert any("['A', 'B']" in n and "first in input order" in n for n in result.notes)


def test_no_tie_note_when_one_batch_governs() -> None:
    """URS-STAB-003: a single earliest batch gives no tie note."""
    result = stab.estimate_shelf_life(with_b003(B003_FASTER), timestamp=FIXED_TIME)
    assert not any("same time" in n for n in result.notes)


def test_pooled_result_has_one_line_and_no_governing_batch() -> None:
    """URS-STAB-003: pooled model reports a single line for all batches."""
    result = stab.estimate_shelf_life(with_b003(B003_SIMILAR), timestamp=FIXED_TIME)
    assert len(result.per_batch) == 1
    assert result.per_batch[0].label is None
    assert result.governing_batch is None


# --- URS-STAB-004, URS-STAB-008: Appendix A cap -------------------------------------------


@pytest.mark.parametrize(("x", "cap"), [(6.0, 12.0), (12.0, 24.0), (24.0, 36.0), (36.0, 48.0)])
def test_cap_is_min_of_2x_and_x_plus_12(x: float, cap: float) -> None:
    """URS-STAB-004: Appendix A (statistical analysis performed): min(2X, X + 12)."""
    t = [0.0, x / 2, x]
    data = make_input({"A": [100.0, 99.0, 98.1], "B": [100.2, 99.1, 98.0]}, times={"A": t, "B": t})
    ext = stab.extrapolation_cap(data)
    assert ext.x_months == x
    assert ext.factor == criteria.EXTRAPOLATION_FACTOR_STATS
    assert ext.max_extra_months == criteria.EXTRAPOLATION_MAX_EXTRA_MONTHS_STATS
    assert ext.cap_months == cap


def test_x_is_shortest_batch_coverage() -> None:
    """URS-STAB-008: X is the shortest of the batches' last time points."""
    data = make_input(
        {"A": B001, "B": B002[:5]},
        times={"A": TIMES, "B": TIMES[:5]},
    )
    ext = stab.extrapolation_cap(data)
    assert ext.x_months == 12.0
    assert ext.cap_months == 24.0


def test_x_uses_last_time_point_not_list_order() -> None:
    """URS-STAB-008: X is the latest time in each batch even when entered unsorted."""
    t = [24.0, 0.0, 12.0]
    data = make_input({"A": [97.0, 100.0, 98.5], "B": [96.9, 100.1, 98.4]}, times={"A": t, "B": t})
    assert stab.extrapolation_cap(data).x_months == 24.0


# --- URS-STAB-005 and URS-STAB-016: reporting, rounding down, edge outcomes ----------------


@pytest.mark.parametrize(
    ("crossing", "cap", "months", "limited_by"),
    [
        (34.60179115, 36.0, 34, "crossing"),
        (29.99999999, 36.0, 29, "crossing"),
        (24.0, 36.0, 24, "crossing"),
        (40.0, 36.0, 36, "extrapolation_cap"),
        (36.0, 36.0, 36, "crossing"),
        (None, 36.0, 36, "extrapolation_cap"),
        (0.0, 36.0, 0, "bound_below_limit_at_start"),
    ],
)
def test_proposed_shelf_life_rounds_down_and_respects_cap(
    crossing: float | None, cap: float, months: int, limited_by: str
) -> None:
    """URS-STAB-005, URS-STAB-016: floor(min(crossing, cap)); never rounded up."""
    assert stab.propose_shelf_life(crossing, cap) == (months, limited_by)


def test_result_reports_every_reviewer_value() -> None:
    """URS-STAB-005: model, both tests, df, t value, crossing at full precision, shelf-life."""
    result = stab.estimate_shelf_life(with_b003(B003_LOWER_START), timestamp=FIXED_TIME)
    pool = result.poolability
    assert pool.model == "common_slope"
    assert pool.slopes.p_value >= 0.25
    assert pool.intercepts is not None
    assert pool.intercepts.p_value < 0.25
    for line in result.per_batch:
        assert line.df == 17
        assert line.t_value == pytest.approx(sps.t.ppf(criteria.SHELF_LIFE_CONFIDENCE, 17))
        assert line.slope == pytest.approx(result.per_batch[0].slope)
    assert result.crossing_months is not None
    assert result.crossing_months != round(result.crossing_months, 2)  # not rounded
    assert result.proposed_shelf_life_months == math.floor(result.crossing_months) == 29
    assert result.limited_by == "crossing"
    assert "B003" in result.conclusion
    assert "29" in result.conclusion


def test_separate_model_uses_full_model_df_and_t() -> None:
    """URS-STAB-005: separate model reports the full model's df (N - 2k) and its t value, while
    the per-batch fits keep their own df (n - 2)."""
    data = with_b003(B003_FASTER)
    result = stab.estimate_shelf_life(data, timestamp=FIXED_TIME)
    n, k = sum(len(b.values) for b in data.batches), len(data.batches)
    assert result.poolability.model == "separate"
    for line in result.per_batch:
        assert line.df == n - 2 * k == 15
        assert line.t_value == pytest.approx(sps.t.ppf(criteria.SHELF_LIFE_CONFIDENCE, 15))
    assert all(f.residual_df == 5 for f in result.batch_fits)


def test_bound_below_limit_at_start_gives_zero_shelf_life() -> None:
    """URS-STAB-016: bound at or below the limit at time 0 -> shelf-life 0, none supported."""
    data = make_input(lower_limit=100.1)
    result = stab.estimate_shelf_life(data, timestamp=FIXED_TIME)
    assert result.per_batch[0].bound_at_0 < 100.1
    assert result.crossing_months == 0.0
    assert result.proposed_shelf_life_months == 0
    assert result.limited_by == "bound_below_limit_at_start"
    assert "no shelf-life" in result.conclusion.lower()


def test_bound_never_meeting_limit_is_capped_with_note() -> None:
    """URS-STAB-016: if the bound never meets the limit, the cap sets the shelf-life."""
    result = stab.estimate_shelf_life(make_input(RISING), timestamp=FIXED_TIME)
    assert result.crossing_months is None
    assert all(p.crossing_months is None for p in result.per_batch)
    assert result.proposed_shelf_life_months == 36
    assert result.limited_by == "extrapolation_cap"
    assert any("never meets" in n for n in result.notes)


def test_cap_limits_shelf_life_when_crossing_is_later() -> None:
    """URS-STAB-004: a crossing beyond the cap is reported but the cap sets the shelf-life."""
    short = [0.0, 3.0, 6.0, 9.0, 12.0]
    data = make_input(
        {"B001": B001[:5], "B002": B002[:5], "B003": B003_SIMILAR[:5]},
        times={"B001": short, "B002": short, "B003": short},
    )
    result = stab.estimate_shelf_life(data, timestamp=FIXED_TIME)
    assert result.extrapolation.cap_months == 24.0
    assert result.crossing_months is not None
    assert result.crossing_months > 24.0
    assert result.proposed_shelf_life_months == 24
    assert result.limited_by == "extrapolation_cap"


# --- URS-STAB-017: fewer than 3 primary batches -------------------------------------------


def test_two_batches_run_with_q1a_warning() -> None:
    """URS-STAB-017: 2 batches -> result returned with an ICH Q1A(R2) warning."""
    result = stab.estimate_shelf_life(make_input({"B001": B001, "B002": B002}))
    assert any("ICH Q1A(R2), Selection of Batches" in w for w in result.warnings)
    assert result.proposed_shelf_life_months > 0


def test_three_batches_give_no_warning() -> None:
    """URS-STAB-017: 3 batches -> no primary-batch warning."""
    assert stab.estimate_shelf_life(with_b003(B003_SIMILAR)).warnings == ()


# --- URS-STAB-006, 007, 009 to 015: input validation --------------------------------------


@pytest.mark.parametrize("direction", ["increase", "either"])
def test_only_decreasing_attribute_supported(direction: str) -> None:
    """URS-STAB-006: increase and either are refused as not supported in v1."""
    with pytest.raises(ValidationError, match="not supported in v1"):
        make_input(direction=direction)


@pytest.mark.parametrize(
    ("significant_change", "analysis_performed"),
    [(True, True), (False, False), (True, False)],
)
def test_only_statistical_analysis_branch_of_appendix_a(
    significant_change: bool, analysis_performed: bool
) -> None:
    """URS-STAB-007: any branch other than no significant change + statistics is refused."""
    with pytest.raises(ValidationError, match="Appendix A"):
        make_input(
            significant_change_at_accelerated=significant_change,
            statistical_analysis_performed=analysis_performed,
        )


@pytest.mark.parametrize(
    "missing", ["significant_change_at_accelerated", "statistical_analysis_performed"]
)
def test_appendix_a_flags_have_no_default(missing: str) -> None:
    """URS-STAB-007: the Appendix A conditions must be stated explicitly."""
    fields = make_input().model_dump()
    del fields[missing]
    with pytest.raises(ValidationError, match=missing):
        StabilityInput.model_validate(fields)


def test_one_batch_rejected() -> None:
    """URS-STAB-009: fewer than 2 batches is rejected."""
    with pytest.raises(ValidationError, match="at least 2 batches"):
        make_input({"B001": B001})


def test_batch_with_two_observations_rejected() -> None:
    """URS-STAB-010: a batch needs at least 3 observations; the batch is named."""
    with pytest.raises(ValidationError, match=r"B002.*2 observations.*at least 3"):
        StabilityBatch(label="B002", times_months=(0.0, 6.0), values=(100.0, 99.0))


def test_batch_with_one_distinct_time_rejected() -> None:
    """URS-STAB-011: a batch needs at least 2 distinct time points; the batch is named."""
    with pytest.raises(ValidationError, match=r"B002.*1 distinct time point"):
        StabilityBatch(label="B002", times_months=(6.0, 6.0, 6.0), values=(100.0, 99.0, 99.5))


def test_length_mismatch_rejected() -> None:
    """URS-STAB-012: times and values must have the same length; the batch is named."""
    with pytest.raises(ValidationError, match=r"B001.*7 time points.*6 values"):
        StabilityBatch(label="B001", times_months=tuple(TIMES), values=tuple(B001[:6]))


def test_negative_time_rejected() -> None:
    """URS-STAB-013: negative time points are rejected; the batch is named."""
    with pytest.raises(ValidationError, match=r"B001.*negative time"):
        StabilityBatch(label="B001", times_months=(-1.0, 3.0, 6.0), values=(100.0, 99.5, 99.0))


@pytest.mark.parametrize(
    "fields",
    [
        {"label": "B001", "times_months": (0.0, 3.0, float("nan")), "values": (100.0, 99.0, 98.0)},
        {"label": "B001", "times_months": (0.0, 3.0, float("inf")), "values": (100.0, 99.0, 98.0)},
        {"label": "B001", "times_months": (0.0, 3.0, 6.0), "values": (100.0, float("nan"), 98.0)},
        {"label": "B001", "times_months": (0.0, 3.0, 6.0), "values": (100.0, -float("inf"), 98.0)},
    ],
)
def test_non_finite_batch_values_rejected(fields: dict[str, Any]) -> None:
    """URS-STAB-014: NaN and infinity are rejected in times and values."""
    with pytest.raises(ValidationError):
        StabilityBatch(**fields)


@pytest.mark.parametrize("limit", [float("nan"), float("inf")])
def test_non_finite_limit_rejected(limit: float) -> None:
    """URS-STAB-014: the lower limit must be finite."""
    with pytest.raises(ValidationError):
        make_input(lower_limit=limit)


def test_negative_value_rejected() -> None:
    """URS-STAB-018: negative results are impossible and rejected; the batch is named."""
    with pytest.raises(ValidationError, match=r"B002.*negative value"):
        StabilityBatch(label="B002", times_months=(0.0, 3.0, 6.0), values=(100.0, -0.1, 99.0))


def test_negative_lower_limit_rejected() -> None:
    """URS-STAB-018: a negative lower limit is rejected."""
    with pytest.raises(ValidationError, match="lower_limit"):
        make_input(lower_limit=-1.0)


def test_values_above_100_are_kept_not_clipped() -> None:
    """URS-STAB-018: values above 100% are valid and kept exactly as entered."""
    batch = StabilityBatch(label="B001", times_months=(0.0, 3.0, 6.0), values=(101.5, 100.8, 0.0))
    assert batch.values == (101.5, 100.8, 0.0)


@pytest.mark.parametrize("value", ["yes", "true", 1, 0])
@pytest.mark.parametrize(
    "field", ["significant_change_at_accelerated", "statistical_analysis_performed"]
)
def test_appendix_a_flags_must_be_true_booleans(field: str, value: Any) -> None:
    """URS-STAB-007: the Appendix A conditions must be explicit true/false, not coerced."""
    fields = make_input().model_dump()
    fields[field] = value
    with pytest.raises(ValidationError, match=field):
        StabilityInput.model_validate(fields)


def test_empty_label_rejected() -> None:
    """URS-STAB-015: batch labels must not be empty."""
    with pytest.raises(ValidationError):
        StabilityBatch(label="", times_months=(0.0, 3.0, 6.0), values=(100.0, 99.5, 99.0))


def test_duplicate_labels_rejected() -> None:
    """URS-STAB-015: duplicate batch labels are rejected and named."""
    fields = make_input().model_dump()
    fields["batches"][2]["label"] = "B001"
    with pytest.raises(ValidationError, match="duplicate batch label.*B001"):
        StabilityInput.model_validate(fields)


@pytest.mark.parametrize("label", ["B001 ", " B001", "B001\t"])
def test_padded_label_rejected(label: str) -> None:
    """URS-STAB-015: leading or trailing whitespace would silently make a second batch."""
    with pytest.raises(ValidationError, match="leading or trailing whitespace"):
        StabilityBatch(label=label, times_months=(0.0, 3.0, 6.0), values=(100.0, 99.5, 99.0))


def test_labels_differing_only_by_case_rejected() -> None:
    """URS-STAB-015: 'B001' and 'b001' are reported as a clash, not treated as two batches."""
    fields = make_input().model_dump()
    fields["batches"][2]["label"] = "b001"
    with pytest.raises(ValidationError, match=r"differ only by letter case: 'B001', 'b001'"):
        StabilityInput.model_validate(fields)


# --- URS-GEN-001, URS-GEN-002: disclaimer and traceability --------------------------------


def test_result_carries_disclaimer_and_traceability_stamp() -> None:
    """URS-GEN-001, URS-GEN-002: disclaimer, versions, input hash and timestamp."""
    data = with_b003(B003_SIMILAR)
    result = stab.estimate_shelf_life(data, timestamp=FIXED_TIME)
    meta = result.metadata
    assert meta.disclaimer == DISCLAIMER
    assert meta.app_version == __version__
    assert meta.guideline_version == criteria.GUIDELINE_VERSIONS["stability"]
    assert meta.timestamp == FIXED_TIME
    assert result.inputs == data


def test_input_hash_tracks_inputs() -> None:
    """URS-GEN-002: equal inputs give equal hashes; any change gives a different hash."""
    a = stab.estimate_shelf_life(with_b003(B003_SIMILAR), timestamp=FIXED_TIME)
    b = stab.estimate_shelf_life(with_b003(B003_SIMILAR), timestamp=FIXED_TIME)
    c = stab.estimate_shelf_life(make_input(lower_limit=94.9), timestamp=FIXED_TIME)
    assert a.metadata.input_hash == b.metadata.input_hash
    assert a.metadata.input_hash != c.metadata.input_hash


# --- Properties ---------------------------------------------------------------------------


@settings(max_examples=25, deadline=None)
@given(shift=st.floats(min_value=0.01, max_value=2.0))
def test_raising_every_value_never_shortens_shelf_life(shift: float) -> None:
    """URS-STAB-002, URS-STAB-003: a uniform upward shift leaves the poolability tests
    unchanged and moves the crossing later."""
    original = {"B001": B001, "B002": B002, "B003": B003_LOWER_START}
    up = {k: [v + shift for v in vals] for k, vals in original.items()}
    r0 = stab.estimate_shelf_life(make_input(original), timestamp=FIXED_TIME)
    r1 = stab.estimate_shelf_life(make_input(up), timestamp=FIXED_TIME)
    assert r1.poolability.model == r0.poolability.model
    assert r1.poolability.slopes.p_value == pytest.approx(r0.poolability.slopes.p_value)
    assert r0.crossing_months is not None
    assert r1.crossing_months is None or r1.crossing_months > r0.crossing_months
    assert r1.proposed_shelf_life_months >= r0.proposed_shelf_life_months


@settings(max_examples=25, deadline=None)
@given(limit=st.floats(min_value=90.0, max_value=99.0))
def test_shelf_life_never_exceeds_cap(limit: float) -> None:
    """URS-STAB-004: whatever the limit, the proposed shelf-life is at most the cap."""
    result = stab.estimate_shelf_life(make_input(lower_limit=limit), timestamp=FIXED_TIME)
    assert 0 <= result.proposed_shelf_life_months <= result.extrapolation.cap_months
