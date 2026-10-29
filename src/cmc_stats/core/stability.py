"""Stability shelf-life: per-batch regression, ANCOVA poolability, bound crossing, Appendix A cap.

Rules follow ICH Q1E (2003), Evaluation for Stability Data, Appendices A and B, as summarised
in the ich-stats-rules skill. v1 covers an attribute expected to decrease
(one-sided 95% lower bound against a lower limit) and the Appendix A branch "no significant
change at accelerated, statistical analysis performed" at room temperature (Q1E 2.4.1.2 and
Appendix A; refrigerated, freezer and other branches are refused at input and noted as known
limitations, URS-STAB-020 to 024). All values are kept at full precision;
only the proposed shelf-life is rounded down to whole months.

Design matrices (k batches, N results):
- full: one intercept and one slope per batch (2k columns); same lines as separate per-batch
  fits, but one pooled mean square error with df N - 2k (used when slopes differ, Q1E B.2.2.1)
- common slope: one intercept per batch and one shared slope (k + 1 columns)
- pooled: one intercept and one slope for all batches (2 columns)
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats as sps

from cmc_stats import criteria
from cmc_stats.core._linear import OlsFit as _Fit
from cmc_stats.core._linear import ols as _ols
from cmc_stats.models import (
    BatchFit,
    BatchShelfLife,
    ExtrapolationCap,
    PoolabilityResult,
    PoolabilityTest,
    ShelfLifeLimitedBy,
    SourceFile,
    StabilityInput,
    StabilityModel,
    StabilityResult,
    make_metadata,
)

APPENDIX_A_BRANCH_LIMITATION_NOTE = (
    "Known limitation: the extrapolation cap uses only the branch room temperature, no "
    "significant change at accelerated, statistical analysis performed (ICH Q1E 2.4.1.2 and "
    "Appendix A: Y up to 2X, but not exceeding X + 12 months). The refrigerated branch (up to "
    "1.5X, but not exceeding X + 6 months, Q1E 2.5.1.1), freezer storage and the other "
    "Appendix A branches are not supported in v1 and are refused at input."
)
X_DEFINITION_LIMITATION_NOTE = (
    "Known limitation: X, the period covered by long-term data (ICH Q1E Appendix A), is taken "
    "as the shortest of the batches' last time points. This is a conservative reading; Q1E "
    "does not define X further."
)
GUIDELINE_BASIS_LIMITATION_NOTE = (
    "Known limitation: the rules follow ICH Q1A(R2) and ICH Q1E (Step 4, 2003). The "
    "consolidated ICH Q1 is a Step 2 draft (11 April 2025), not final, and is not applied; "
    "re-check these rules when ICH Q1 reaches Step 4 or is adopted by FDA."
)
SEPARATE_MODEL_NOTE = (
    "Slopes differ: each batch's bound uses its own intercept and slope with the pooled mean "
    "square error of the full model (df = N - 2k), ICH Q1E Appendix B.2.2.1; the earliest "
    "crossing governs."
)


@dataclass(frozen=True)
class _Line:
    """Mean line x(t) . coef with x(t) = x0 + t * x1, from fit ``fit``."""

    label: str | None
    fit: _Fit
    x0: NDArray[np.float64]
    x1: NDArray[np.float64]

    @property
    def intercept(self) -> float:
        return float(self.x0 @ self.fit.coef)

    @property
    def slope(self) -> float:
        return float(self.x1 @ self.fit.coef)

    @property
    def t_value(self) -> float:
        return float(sps.t.ppf(criteria.SHELF_LIFE_CONFIDENCE, self.fit.df))

    def variance_terms(self) -> tuple[float, float, float]:
        """(q0, q1, q2) with Var(mean at t) = mse * (q0 + 2 q1 t + q2 t^2)."""
        v = self.fit.xtx_inv
        return (
            float(self.x0 @ v @ self.x0),
            float(self.x0 @ v @ self.x1),
            float(self.x1 @ v @ self.x1),
        )


def _stacked(
    data: StabilityInput,
) -> tuple[NDArray[np.intp], NDArray[np.float64], NDArray[np.float64]]:
    """Batch index, time and value for every result, in input order."""
    group = np.concatenate(
        [np.full(len(b.values), i, dtype=np.intp) for i, b in enumerate(data.batches)]
    )
    time = np.concatenate([np.asarray(b.times_months, dtype=np.float64) for b in data.batches])
    value = np.concatenate([np.asarray(b.values, dtype=np.float64) for b in data.batches])
    return group, time, value


def _batch_ols(data: StabilityInput, index: int) -> _Fit:
    batch = data.batches[index]
    t = np.asarray(batch.times_months, dtype=np.float64)
    return _ols(np.column_stack([np.ones_like(t), t]), np.asarray(batch.values, np.float64))


def _model_fits(data: StabilityInput) -> tuple[_Fit, _Fit, _Fit]:
    """Full, common-slope and pooled ANCOVA fits (ICH Q1E Appendix B)."""
    group, time, y = _stacked(data)
    k = len(data.batches)
    dummies = (group[:, None] == np.arange(k)[None, :]).astype(np.float64)
    full = _ols(np.hstack([dummies, dummies * time[:, None]]), y)
    common = _ols(np.hstack([dummies, time[:, None]]), y)
    pooled = _ols(np.column_stack([np.ones_like(time), time]), y)
    return full, common, pooled


def _f_test(rss_reduced: float, rss_larger: float, df_num: int, larger: _Fit) -> PoolabilityTest:
    if larger.rss == 0.0:
        raise ValueError(
            "residual error is zero (data lie exactly on the fitted lines): the poolability "
            "F test is undefined"
        )
    f_value = ((rss_reduced - rss_larger) / df_num) / larger.mse
    return PoolabilityTest(
        f_value=f_value,
        df_num=df_num,
        df_den=larger.df,
        p_value=float(sps.f.sf(f_value, df_num, larger.df)),
    )


def fit_batches(data: StabilityInput) -> tuple[BatchFit, ...]:
    """Least-squares line of attribute against time for each batch (URS-STAB-001).

    ICH Q1E (2003), Appendix B: each batch fitted on its own data. Returns
    intercept, slope, their standard errors, residual df and MSE, in input batch order.
    """
    fits = []
    for i, batch in enumerate(data.batches):
        fit = _batch_ols(data, i)
        se = np.sqrt(fit.mse * np.diag(fit.xtx_inv))
        fits.append(
            BatchFit(
                label=batch.label,
                intercept=float(fit.coef[0]),
                slope=float(fit.coef[1]),
                intercept_se=float(se[0]),
                slope_se=float(se[1]),
                residual_df=fit.df,
                mse=fit.mse,
            )
        )
    return tuple(fits)


def select_model(slope_p: float, intercept_p: float | None) -> StabilityModel:
    """Choose the model from the poolability p-values (URS-STAB-002, URS-STAB-019).

    ICH Q1E (2003), Appendix B.2.2.1, at ``POOLABILITY_ALPHA`` (0.25): slope p at or below
    alpha -> separate; otherwise intercept p at or below alpha -> common slope; otherwise
    pooled. Only p > 0.25 pools (ICH Q1A(R2) 2.1.9 and 2.2.9, "more than 0.25"; user decision
    2026-10-29).

    Raises:
        ValueError: slopes are poolable but no intercept p-value was given.
    """
    alpha = criteria.POOLABILITY_ALPHA
    if slope_p <= alpha:
        return "separate"
    if intercept_p is None:
        raise ValueError("an intercept p-value is required when slopes are poolable")
    return "common_slope" if intercept_p <= alpha else "pooled"


def poolability(data: StabilityInput) -> PoolabilityResult:
    """ANCOVA tests of slope then intercept equality at 0.25 (URS-STAB-002, 005, 019).

    ICH Q1E (2003), Appendix B.2.2.1. Slopes: common-slope vs full model, F on the
    full model's residual error. Intercepts, only when slope p > 0.25: pooled vs common-slope
    model, F on the common-slope model's residual error (sequential ANCOVA).

    Raises:
        ValueError: residual error is zero, so the F test is undefined.
    """
    k = len(data.batches)
    full, common, pooled = _model_fits(data)
    slopes = _f_test(common.rss, full.rss, k - 1, full)
    intercepts = None
    if slopes.p_value > criteria.POOLABILITY_ALPHA:
        intercepts = _f_test(pooled.rss, common.rss, k - 1, common)
    return PoolabilityResult(
        alpha=criteria.POOLABILITY_ALPHA,
        slopes=slopes,
        intercepts=intercepts,
        model=select_model(slopes.p_value, intercepts.p_value if intercepts else None),
    )


def _lines(data: StabilityInput, model: StabilityModel) -> tuple[_Line, ...]:
    """The mean line(s) whose bound decides the shelf-life under ``model``.

    Separate lines are the full model's lines: each batch's own intercept and slope with the
    pooled mean square error calculated from all batches (ICH Q1E Appendix B.2.2.1). The full
    design is block diagonal, so each batch's coefficients and (X'X)^-1 block equal its own
    fit; taking them from that fit keeps identical batches bit-identical (ties stay exact),
    and the full model supplies the residual sum of squares and df N - 2k.
    """
    k = len(data.batches)
    full, common, pooled = _model_fits(data)
    if model == "pooled":
        return (_Line(None, pooled, np.array([1.0, 0.0]), np.array([0.0, 1.0])),)
    if model == "common_slope":
        slope_col = np.zeros(k + 1)
        slope_col[k] = 1.0
        return tuple(
            _Line(b.label, common, np.eye(k + 1)[i], slope_col) for i, b in enumerate(data.batches)
        )
    lines = []
    for i, b in enumerate(data.batches):
        own = _batch_ols(data, i)
        fit = _Fit(coef=own.coef, xtx_inv=own.xtx_inv, rss=full.rss, df=full.df)
        lines.append(_Line(b.label, fit, np.array([1.0, 0.0]), np.array([0.0, 1.0])))
    return tuple(lines)


def _line(data: StabilityInput, model: StabilityModel, label: str | None) -> _Line:
    lines = _lines(data, model)
    if model == "pooled":
        if label is not None:
            raise ValueError("the pooled model has one line: pass label=None")
        return lines[0]
    for line in lines:
        if line.label == label:
            return line
    raise ValueError(f"unknown batch label {label!r}")


def _bound(line: _Line, times: NDArray[np.float64]) -> NDArray[np.float64]:
    q0, q1, q2 = line.variance_terms()
    var = line.fit.mse * (q0 + 2.0 * q1 * times + q2 * times**2)
    mean = line.intercept + line.slope * times
    return np.asarray(mean - line.t_value * np.sqrt(var), dtype=np.float64)


def lower_bound(
    data: StabilityInput, model: StabilityModel, label: str | None, times: ArrayLike
) -> NDArray[np.float64]:
    """One-sided 95% lower confidence bound of the mean line at ``times`` (URS-STAB-003).

    ICH Q1E (2003), 2.6, p. 7 (lower one-sided 95 percent confidence limit for an attribute
    known to decrease) and Appendix B.1: mean - t(0.95, df) * SE(mean). Pooled and common-slope
    lines use that model's residual error and df. Separate lines use each batch's intercept
    and slope with the pooled mean square error of the full model, df N - 2k (Appendix
    B.2.2.1). ``label`` is ``None`` for the pooled line.

    Raises:
        ValueError: ``label`` does not match the model's lines.
    """
    return _bound(_line(data, model, label), np.asarray(times, dtype=np.float64))


def _crossing(line: _Line, limit: float) -> float | None:
    """Earliest t >= 0 where the lower bound is at or below ``limit``, in closed form.

    With m(t) = a + b t - limit and k = t value, the bound meets the limit where
    m(t)^2 = k^2 mse (q0 + 2 q1 t + q2 t^2) and m(t) >= 0: a quadratic in t.

    Once the bound is above the limit at t = 0, a positive definite variance makes the
    discriminant positive, so a negative one signals a numerical fault and is raised rather
    than read as "never meets the limit".
    """
    if _bound(line, np.array([0.0]))[0] <= limit:
        return 0.0
    a, b = line.intercept - limit, line.slope
    q0, q1, q2 = line.variance_terms()
    k2s2 = line.t_value**2 * line.fit.mse
    qa, qb, qc = b * b - k2s2 * q2, a * b - k2s2 * q1, a * a - k2s2 * q0  # qa t^2 + 2 qb t + qc
    if qa == 0.0:
        roots = [] if qb == 0.0 else [-qc / (2.0 * qb)]
    else:
        disc = qb * qb - qa * qc
        if disc < 0.0:
            raise ValueError(
                f"internal error: negative discriminant {disc} in the crossing equation; "
                "the variance of the mean line is not positive definite"
            )
        h = -(qb + math.copysign(math.sqrt(disc), qb))
        roots = [h / qa] + ([qc / h] if h != 0.0 else [])
    valid = [t for t in roots if t > 0.0 and a + b * t >= 0.0]
    return min(valid) if valid else None


def crossing_time(data: StabilityInput, model: StabilityModel, label: str | None) -> float | None:
    """Earliest time the one-sided 95% lower bound meets the lower limit (URS-STAB-003, 016).

    ICH Q1E (2003), Appendix B. Returns 0.0 if the bound is already at or
    below the limit at time 0, and ``None`` if it never meets the limit. Full precision.

    Raises:
        ValueError: ``label`` does not match the model's lines, or a numerical fault in the
            crossing equation.
    """
    return _crossing(_line(data, model, label), data.lower_limit)


def extrapolation_cap(data: StabilityInput) -> ExtrapolationCap:
    """Appendix A cap: min(2X, X + 12) months (URS-STAB-004, URS-STAB-007, URS-STAB-008).

    ICH Q1E (2003), 2.4.1.2, p. 4, and Appendix A, p. 8: "Y = up to 2X, but not exceeding
    X + 12 months", branch "no significant change at accelerated, statistical analysis
    performed" (the only branch ``StabilityInput`` accepts), room temperature only; the
    refrigerated branch is refused at input (URS-STAB-022; known limitation, URS-STAB-020).
    X ("period covered by long-term data") is the shortest of the batches' last time points
    (user decision 2026-10-27; known limitation, URS-STAB-021).
    """
    x = min(max(b.times_months) for b in data.batches)
    factor = criteria.EXTRAPOLATION_FACTOR_STATS
    extra = criteria.EXTRAPOLATION_MAX_EXTRA_MONTHS_STATS
    return ExtrapolationCap(
        x_months=x, factor=factor, max_extra_months=extra, cap_months=min(factor * x, x + extra)
    )


def propose_shelf_life(
    crossing_months: float | None, cap_months: float
) -> tuple[int, ShelfLifeLimitedBy]:
    """Proposed shelf-life: floor(min(crossing, cap)) in whole months (URS-STAB-005, 016).

    ICH Q1E (2003): shelf-life is where the bound meets the limit, limited by Appendix A;
    rounded down, never up. A crossing at 0 means no shelf-life is supported; no crossing
    means the cap applies.
    """
    if crossing_months is None:
        return math.floor(cap_months), "extrapolation_cap"
    if crossing_months <= 0.0:
        return 0, "bound_below_limit_at_start"
    if crossing_months <= cap_months:
        return math.floor(crossing_months), "crossing"
    return math.floor(cap_months), "extrapolation_cap"


def estimate_shelf_life(
    data: StabilityInput,
    *,
    timestamp: datetime | None = None,
    source_files: Sequence[SourceFile] = (),
) -> StabilityResult:
    """Full ICH Q1E shelf-life evaluation (URS-STAB-001 to 018, URS-GEN-001 to 003).

    ICH Q1E (2003), Appendices A and B. Steps: per-batch fits; poolability
    at 0.25 (slopes, then intercepts); bound of each line of the chosen model; earliest
    crossing (worst batch governs); Appendix A cap; shelf-life rounded down to whole months.
    Warns when there are fewer than 3 batches (ICH Q1A(R2), Selection of Batches, 2.1.3 and
    2.2.3).
    ``source_files`` (raw uploads the data came from) are recorded in the metadata only.
    """
    metadata = make_metadata(
        {"inputs": data.model_dump(mode="json")},
        "stability",
        timestamp,
        source_files=source_files,
    )
    pool = poolability(data)
    model = pool.model
    per_batch = []
    for line in _lines(data, model):
        per_batch.append(
            BatchShelfLife(
                label=line.label,
                intercept=line.intercept,
                slope=line.slope,
                df=line.fit.df,
                t_value=line.t_value,
                bound_at_0=float(_bound(line, np.array([0.0]))[0]),
                crossing_months=_crossing(line, data.lower_limit),
            )
        )
    crossed = [p for p in per_batch if p.crossing_months is not None]
    first = min(crossed, key=lambda p: p.crossing_months or 0.0) if crossed else None
    crossing = first.crossing_months if first else None
    governing = first.label if first and model != "pooled" else None
    tied = [p.label for p in crossed if p.crossing_months == crossing]
    ext = extrapolation_cap(data)
    months, limited_by = propose_shelf_life(crossing, ext.cap_months)

    model_text = {
        "pooled": "batches pooled into one line",
        "common_slope": "common slope, separate intercepts",
        "separate": "separate lines per batch",
    }[model]
    notes = [
        f"Model: {model_text} (poolability tested at {pool.alpha}).",
        APPENDIX_A_BRANCH_LIMITATION_NOTE,
        X_DEFINITION_LIMITATION_NOTE,
        GUIDELINE_BASIS_LIMITATION_NOTE,
    ]
    if model == "separate":
        notes.append(SEPARATE_MODEL_NOTE)
    if governing is not None and len(tied) > 1:
        notes.append(
            f"Batches {tied} reach the limit at the same time ({crossing} months); "
            f"{governing} is reported as governing because it is first in input order."
        )
    if crossing is None:
        notes.append(
            "The one-sided 95% lower bound never meets the limit; the Appendix A cap sets "
            "the shelf-life."
        )
    elif limited_by == "extrapolation_cap":
        notes.append(
            f"The bound meets the limit at {crossing} months, beyond the Appendix A cap of "
            f"{ext.cap_months} months; the cap sets the shelf-life."
        )
    warnings = []
    n = len(data.batches)
    if n < criteria.STABILITY_PRIMARY_BATCHES:
        warnings.append(
            f"Only {n} batches supplied; ICH Q1A(R2), Selection of Batches (2.1.3 drug "
            f"substance, 2.2.3 drug product) calls for at least "
            f"{criteria.STABILITY_PRIMARY_BATCHES} primary batches."
        )

    who = f"batch {governing} governs" if governing else "all batches"
    if limited_by == "bound_below_limit_at_start":
        conclusion = (
            f"No shelf-life supported: the one-sided 95% lower bound ({who}) is at or below "
            f"the lower limit {data.lower_limit} at time 0."
        )
    elif limited_by == "crossing":
        conclusion = (
            f"Proposed shelf-life {months} months: {model_text}; {who}; the one-sided 95% "
            f"lower bound meets {data.lower_limit} at {crossing:.2f} months (rounded down)."
        )
    else:
        conclusion = (
            f"Proposed shelf-life {months} months: limited by the ICH Q1E Appendix A cap "
            f"(X = {ext.x_months} months); {model_text}."
        )

    return StabilityResult(
        inputs=data,
        metadata=metadata,
        batch_fits=fit_batches(data),
        poolability=pool,
        per_batch=tuple(per_batch),
        governing_batch=governing,
        crossing_months=crossing,
        extrapolation=ext,
        proposed_shelf_life_months=months,
        limited_by=limited_by,
        conclusion=conclusion,
        notes=tuple(notes),
        warnings=tuple(warnings),
    )
