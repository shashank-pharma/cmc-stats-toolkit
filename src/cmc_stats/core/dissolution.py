"""Dissolution profile similarity: f1, f2, 85% cut-off, CV checks and bootstrap f2.

Rules follow FDA guidance, Dissolution Testing of Immediate Release Solid Oral Dosage Forms
(1997), section V (dissolution profile comparisons) as summarised in the
ich-stats-rules skill. The bootstrap f2 follows Shah et al., Pharm Res 1998 and is provisional,
pending agency text. All values are kept at full precision.
"""

from collections.abc import Sequence
from datetime import datetime

import numpy as np
from numpy.typing import ArrayLike, NDArray

from cmc_stats import criteria
from cmc_stats.models import (
    BootstrapF2Result,
    BootstrapSettings,
    CvCheck,
    CvPoint,
    DissolutionDecisionBasis,
    DissolutionInput,
    DissolutionResult,
    TruncationResult,
    make_metadata,
)

BOOTSTRAP_METHOD_NOTE = (
    "Percentile bootstrap per Shah et al., Pharm Res 1998 - provisional, pending agency text. "
    "Units resampled with replacement, separately per product (reference indices drawn first, "
    "then test), on the time points fixed by the 85% rule from the observed means; "
    "percentiles by linear interpolation (numpy 'linear', R type 7)."
)


def _pair(reference: ArrayLike, test: ArrayLike) -> tuple[NDArray[np.float64], ...]:
    ref = np.asarray(reference, dtype=np.float64)
    tst = np.asarray(test, dtype=np.float64)
    if ref.ndim != 1 or ref.shape != tst.shape:
        raise ValueError(
            "reference and test must be 1-D with the same number of time points; "
            f"got {ref.shape} and {tst.shape}"
        )
    if ref.size == 0:
        raise ValueError("at least one time point is required")
    return ref, tst


def f1(reference: ArrayLike, test: ArrayLike) -> float:
    """Difference factor f1 from mean profiles (URS-DISS-002).

    f1 = 100 * sum(|R_t - T_t|) / sum(R_t). FDA IR dissolution guidance (1997), section V.

    Raises:
        ValueError: unequal or empty profiles, or a reference sum of zero.
    """
    ref, tst = _pair(reference, test)
    total = float(np.sum(ref))
    if total == 0.0:
        raise ValueError("f1 is undefined: the reference profile sums to zero")
    return 100.0 * float(np.sum(np.abs(ref - tst))) / total


def f2(reference: ArrayLike, test: ArrayLike) -> float:
    """Similarity factor f2 from mean profiles (URS-DISS-002).

    f2 = 50 * log10(100 / sqrt(1 + (1/n) * sum((R_t - T_t)^2))).
    FDA IR dissolution guidance (1997), section V.

    Raises:
        ValueError: unequal or empty profiles.
    """
    ref, tst = _pair(reference, test)
    msd = float(np.mean((ref - tst) ** 2))
    return 50.0 * float(np.log10(100.0 / np.sqrt(1.0 + msd)))


def f1_within_limit(f1_value: float) -> bool:
    """Companion check f1 <= 15 (URS-DISS-008). FDA IR dissolution guidance (1997), section V."""
    return f1_value <= criteria.F1_SIMILAR_MAX


def unit_cv_pct(units: ArrayLike) -> NDArray[np.float64]:
    """CV% per time point: 100 * SD (ddof=1) / mean (URS-DISS-003; FDA 1997, section V).

    Args:
        units: rows are dosage units, columns are time points.

    Raises:
        ValueError: a column mean of zero, where CV is undefined.
    """
    arr = np.asarray(units, dtype=np.float64)
    mean = arr.mean(axis=0)
    zero = np.flatnonzero(mean == 0.0)
    if zero.size:
        raise ValueError(f"CV undefined: mean dissolution is zero at time index {zero.tolist()}")
    return np.asarray(100.0 * arr.std(axis=0, ddof=1) / mean, dtype=np.float64)


def check_cv(times_min: ArrayLike, reference_units: ArrayLike, test_units: ArrayLike) -> CvCheck:
    """Check CV limits for both products at each time point (URS-DISS-003).

    FDA IR dissolution guidance (1997), section V: at most 20% at earlier points (here
    t <= ``CV_EARLY_MAX_TIME_MIN``) and at most 10% at later points. Pass only the time points
    that are used after the 85% rule.
    """
    times = np.asarray(times_min, dtype=np.float64)
    cv_ref = unit_cv_pct(reference_units)
    cv_test = unit_cv_pct(test_units)
    points = []
    for t, cr, ct in zip(times, cv_ref, cv_test, strict=True):
        limit = (
            criteria.CV_LIMIT_EARLY_PCT
            if t <= criteria.CV_EARLY_MAX_TIME_MIN
            else criteria.CV_LIMIT_LATER_PCT
        )
        points.append(
            CvPoint(
                time_min=float(t),
                cv_reference_pct=float(cr),
                cv_test_pct=float(ct),
                limit_pct=limit,
                passed=bool(cr <= limit and ct <= limit),
            )
        )
    return CvCheck(points=tuple(points), all_pass=all(p.passed for p in points))


def truncate_at_85(
    times_min: Sequence[float], mean_reference: ArrayLike, mean_test: ArrayLike
) -> TruncationResult:
    """Keep points up to and including the first where both means reach 85% (URS-DISS-001).

    FDA IR dissolution guidance (1997), section V: only one measurement after 85% dissolution
    of both products. Excluded points are listed, never silently dropped. If both products never
    reach 85% at the same point, every point is kept and the reason says so.
    """
    ref, tst = _pair(mean_reference, mean_test)
    n = ref.size
    if len(times_min) != n:
        raise ValueError(f"{len(times_min)} time points for profiles of length {n}")
    plateau = criteria.DISSOLUTION_PLATEAU_PCT
    both = np.flatnonzero((ref >= plateau) & (tst >= plateau))
    if both.size == 0:
        return TruncationResult(
            included_indices=tuple(range(n)),
            excluded_indices=(),
            cutoff_time_min=None,
            reason=f"{plateau}% not reached by both products at any time point; all points used",
        )
    cut = int(both[0])
    return TruncationResult(
        included_indices=tuple(range(cut + 1)),
        excluded_indices=tuple(range(cut + 1, n)),
        cutoff_time_min=float(times_min[cut]),
        reason=(
            f"both products reach {plateau}% at {times_min[cut]} min; "
            "later points excluded (FDA IR dissolution guidance, 1997)"
        ),
    )


def is_rapidly_dissolving(
    times_min: ArrayLike, mean_reference: ArrayLike, mean_test: ArrayLike
) -> bool:
    """True when each product reaches 85% at some point within 15 min (URS-DISS-006).

    FDA IR dissolution guidance (1997), section V: profile comparison is then usually
    unnecessary, so no f2 verdict is given.
    """
    times = np.asarray(times_min, dtype=np.float64)
    early = times <= criteria.RAPID_DISSOLUTION_TIME_MIN
    plateau = criteria.DISSOLUTION_PLATEAU_PCT
    ref = np.asarray(mean_reference, dtype=np.float64)
    tst = np.asarray(mean_test, dtype=np.float64)
    return bool(np.any(ref[early] >= plateau) and np.any(tst[early] >= plateau))


def bootstrap_f2(
    times_min: ArrayLike,
    reference_units: ArrayLike,
    test_units: ArrayLike,
    settings: BootstrapSettings,
) -> BootstrapF2Result:
    """Percentile bootstrap interval for f2 (URS-DISS-003, URS-DISS-007).

    Shah et al., Pharm Res 1998 - provisional, pending agency text. Each resample draws units
    with replacement, separately for reference and test, and computes f2 from the resampled
    means. Pass only the time points used after the 85% rule. Reports the ``BOOTSTRAP_CI_LEVEL``
    percentile interval; similar when the lower bound is at least ``F2_SIMILAR_MIN``.
    """
    times = np.asarray(times_min, dtype=np.float64)
    ref = np.asarray(reference_units, dtype=np.float64)
    tst = np.asarray(test_units, dtype=np.float64)
    if ref.ndim != 2 or tst.ndim != 2 or not (ref.shape[1] == tst.shape[1] == times.size):
        raise ValueError("unit arrays must be 2-D with one column per time point")
    rng = np.random.default_rng(settings.seed)
    b = settings.n_resamples
    idx_ref = rng.integers(0, ref.shape[0], size=(b, ref.shape[0]))
    idx_tst = rng.integers(0, tst.shape[0], size=(b, tst.shape[0]))
    mean_ref = ref[idx_ref].mean(axis=1)
    mean_tst = tst[idx_tst].mean(axis=1)
    msd = np.mean((mean_ref - mean_tst) ** 2, axis=1)
    f2s = 50.0 * np.log10(100.0 / np.sqrt(1.0 + msd))
    tail = (1.0 - criteria.BOOTSTRAP_CI_LEVEL) / 2.0 * 100.0
    lower, median, upper = np.percentile(f2s, [tail, 50.0, 100.0 - tail], method="linear")
    return BootstrapF2Result(
        seed=settings.seed,
        n_resamples=b,
        ci_level=criteria.BOOTSTRAP_CI_LEVEL,
        time_points_used=tuple(float(t) for t in times),
        lower=float(lower),
        median=float(median),
        upper=float(upper),
        similar=bool(lower >= criteria.F2_SIMILAR_MIN),
        method_note=BOOTSTRAP_METHOD_NOTE,
    )


def compare_profiles(
    data: DissolutionInput,
    bootstrap: BootstrapSettings | None = None,
    *,
    timestamp: datetime | None = None,
) -> DissolutionResult:
    """Compare reference and test dissolution profiles (URS-DISS-001 to 008, URS-GEN-001/002).

    FDA IR dissolution guidance (1997), section V; bootstrap per Shah et al., Pharm Res 1998
    (provisional). Steps: mean profiles; rapid-dissolution flag (no f2 verdict); 85% cut-off;
    CV checks on the points used; f1 and f2 from means. If CV limits pass, mean-data f2
    decides. If they fail, bootstrap f2 decides and ``bootstrap`` settings are required.

    Raises:
        ValueError: CV limits fail and no ``BootstrapSettings`` were given, or CV is undefined.
    """
    times = np.asarray(data.times_min, dtype=np.float64)
    ref_units = np.asarray(data.reference.units, dtype=np.float64)
    test_units = np.asarray(data.test.units, dtype=np.float64)
    mean_ref = ref_units.mean(axis=0)
    mean_test = test_units.mean(axis=0)
    metadata = make_metadata(
        {
            "inputs": data.model_dump(mode="json"),
            "bootstrap": bootstrap.model_dump(mode="json") if bootstrap else None,
        },
        "dissolution",
        timestamp,
    )
    mean_reference = tuple(float(x) for x in mean_ref)
    mean_test_tuple = tuple(float(x) for x in mean_test)

    if is_rapidly_dissolving(times, mean_ref, mean_test):
        return DissolutionResult(
            inputs=data,
            bootstrap_settings=bootstrap,
            metadata=metadata,
            mean_reference=mean_reference,
            mean_test=mean_test_tuple,
            rapid_dissolution=True,
            truncation=None,
            cv_check=None,
            n_points_used=None,
            f1=None,
            f1_within_limit=None,
            f2=None,
            bootstrap=None,
            decision_basis="rapid_dissolution",
            f2_similar=None,
            conclusion=(
                f"Both products reach {criteria.DISSOLUTION_PLATEAU_PCT}% within "
                f"{criteria.RAPID_DISSOLUTION_TIME_MIN} min: profile comparison is usually "
                "unnecessary (FDA IR dissolution guidance, 1997). No f2 verdict given."
            ),
            notes=(),
        )

    truncation = truncate_at_85(data.times_min, mean_ref, mean_test)
    used = list(truncation.included_indices)
    cv = check_cv(times[used], ref_units[:, used], test_units[:, used])
    f1_value = f1(mean_ref[used], mean_test[used])
    f2_value = f2(mean_ref[used], mean_test[used])
    notes: list[str] = [truncation.reason]
    limit = criteria.F2_SIMILAR_MIN

    boot: BootstrapF2Result | None = None
    basis: DissolutionDecisionBasis
    if cv.all_pass:
        similar = f2_value >= limit
        basis = "mean_f2"
        verdict = f"mean-data f2 {'>=' if similar else '<'} {limit}"
        if bootstrap is not None:
            notes.append("CV limits met: bootstrap settings supplied but bootstrap not run")
    else:
        failed = [p.time_min for p in cv.points if not p.passed]
        if bootstrap is None:
            raise ValueError(
                f"CV limits fail at {failed} min, so bootstrap f2 is required: supply "
                "BootstrapSettings with an explicit seed and n_resamples"
            )
        boot = bootstrap_f2(times[used], ref_units[:, used], test_units[:, used], bootstrap)
        similar = boot.similar
        basis = "bootstrap_f2"
        verdict = f"bootstrap f2 lower bound {'>=' if similar else '<'} {limit}"
        notes.append(f"CV limits fail at {failed} min: bootstrap f2 decides similarity")

    return DissolutionResult(
        inputs=data,
        bootstrap_settings=bootstrap,
        metadata=metadata,
        mean_reference=mean_reference,
        mean_test=mean_test_tuple,
        rapid_dissolution=False,
        truncation=truncation,
        cv_check=cv,
        n_points_used=len(used),
        f1=f1_value,
        f1_within_limit=f1_within_limit(f1_value),
        f2=f2_value,
        bootstrap=boot,
        decision_basis=basis,
        f2_similar=similar,
        conclusion=f"{'Similar' if similar else 'Not similar'}: {verdict}",
        notes=tuple(notes),
    )
