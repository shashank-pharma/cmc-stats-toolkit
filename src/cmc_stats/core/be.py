"""Average bioequivalence for a 2x2 crossover: log-scale ANOVA, 90% CI of the GMR, TOST, CVw.

Rules follow ICH M13A (2024) and the FDA BE statistics guidance, as summarised in the
ich-stats-rules skill. v1 covers the 2x2 crossover (sequences TR and RT) with average-BE limits
80.00-125.00%; replicate, parallel and reference-scaled analyses are refused by ``BeInput``.
All values are kept at full precision; CI limits are rounded only for the acceptance decision
(round half up, a placeholder pending confirmation against the target agency text).

Design columns, added in this order for the sequential (type I) ANOVA:
intercept | sequence (RT) | subject within sequence (n - 2) | period (2) | treatment (T).
"""

import math
from datetime import datetime
from decimal import Decimal

import numpy as np
from numpy.typing import NDArray
from scipy import stats as sps

from cmc_stats import criteria
from cmc_stats.core._linear import OlsFit, ols
from cmc_stats.models import (
    AnovaRow,
    BeInput,
    BeParameter,
    BeParameterResult,
    BeResult,
    make_metadata,
)

TERMS = ("sequence", "subject(sequence)", "period", "treatment")


def _tost_alpha() -> float:
    return (1.0 - criteria.BE_CI_LEVEL) / 2.0


def _design_blocks(data: BeInput) -> list[NDArray[np.float64]]:
    """Column blocks per term, one row per record in input order."""
    recs = data.records
    subjects: dict[str, list[str]] = {"TR": [], "RT": []}
    for r in recs:
        if r.subject not in subjects[r.sequence]:
            subjects[r.sequence].append(r.subject)
    # within each sequence, the first subject is the baseline (nested coding)
    nested = [s for seq in ("TR", "RT") for s in subjects[seq][1:]]
    n = len(recs)
    return [
        np.ones((n, 1)),
        np.array([[1.0 if r.sequence == "RT" else 0.0] for r in recs]),
        np.array([[1.0 if r.subject == s else 0.0 for s in nested] for r in recs]).reshape(
            n, len(nested)
        ),
        np.array([[1.0 if r.period == 2 else 0.0] for r in recs]),
        np.array([[1.0 if r.treatment == "T" else 0.0] for r in recs]),
    ]


def _response(data: BeInput, parameter: BeParameter) -> NDArray[np.float64]:
    values = [getattr(r, parameter) for r in data.records]
    if any(v is None for v in values):
        raise ValueError(f"{parameter} is not supplied for every record")
    return np.log(np.asarray(values, dtype=np.float64))


def _fit(data: BeInput, parameter: BeParameter) -> tuple[OlsFit, tuple[AnovaRow, ...]]:
    """Full-model fit and the type I ANOVA table from nested sequential fits."""
    y = _response(data, parameter)
    blocks = _design_blocks(data)
    rows = []
    previous = ols(blocks[0], y)
    for k, term in enumerate(TERMS, start=1):
        current = ols(np.hstack(blocks[: k + 1]), y)
        df = blocks[k].shape[1]
        ss = previous.rss - current.rss
        rows.append(AnovaRow(term=term, df=df, ss=ss, ms=ss / df))
        previous = current
    full = previous
    if full.rss == 0.0:
        raise ValueError(
            f"{parameter}: residual error is zero (every subject has the same T/R ratio); "
            "the confidence interval is undefined"
        )
    rows.append(AnovaRow(term="residual", df=full.df, ss=full.rss, ms=full.mse))
    return full, tuple(rows)


def gmr_interval(diff_log: float, se_log: float, df: int) -> tuple[float, float, float]:
    """Point estimate and 90% CI of the T/R geometric mean ratio, in % (URS-BE-001).

    ICH M13A (2024): PE = 100 exp(d); CI = 100 exp(d -/+ t((1 + 0.90) / 2, df) * SE), with d
    the T - R difference of log means from the crossover ANOVA.
    """
    t = float(sps.t.ppf((1.0 + criteria.BE_CI_LEVEL) / 2.0, df))
    return (
        100.0 * math.exp(diff_log),
        100.0 * math.exp(diff_log - t * se_log),
        100.0 * math.exp(diff_log + t * se_log),
    )


def tost_p_values(diff_log: float, se_log: float, df: int) -> tuple[float, float]:
    """Two one-sided test p-values against ln(0.80) and ln(1.25) (URS-BE-003).

    FDA BE statistics guidance; ICH M13A (2024): p_lower = P(T > (d - ln 0.80) / SE) and
    p_upper = P(T < (d - ln 1.25) / SE) with df residual df. Each test is at alpha 0.05,
    derived as (1 - BE_CI_LEVEL) / 2.

    Raises:
        ValueError: SE is not positive.
    """
    if se_log <= 0.0:
        raise ValueError(f"standard error must be > 0; got {se_log}")
    lower = math.log(criteria.BE_LOWER_PCT / 100.0)
    upper = math.log(criteria.BE_UPPER_PCT / 100.0)
    return (
        float(sps.t.sf((diff_log - lower) / se_log, df)),
        float(sps.t.cdf((diff_log - upper) / se_log, df)),
    )


def cv_within_pct(mse: float) -> float:
    """Within-subject CV in % from the log-scale residual MSE (URS-BE-003).

    FDA BE statistics guidance: CVw = 100 * sqrt(exp(MSE) - 1).
    """
    return 100.0 * math.sqrt(math.exp(mse) - 1.0)


def be_decision(lower_pct: float, upper_pct: float) -> tuple[float, float, bool]:
    """Round the CI limits, then compare with 80.00-125.00% inclusive (URS-BE-001, 016).

    ICH M13A (2024) acceptance range; limits rounded to ``BE_ROUND_DECIMALS`` with
    ``BE_ROUNDING_MODE`` (round half up: placeholder, pending confirmation against the target
    agency text). Rounding uses the exact binary value of each limit, and the comparison is
    done in decimal arithmetic.
    """
    quantum = Decimal(1).scaleb(-criteria.BE_ROUND_DECIMALS)
    mode = criteria.BE_ROUNDING_MODE
    lo = Decimal(lower_pct).quantize(quantum, rounding=mode)
    hi = Decimal(upper_pct).quantize(quantum, rounding=mode)
    ok = lo >= Decimal(repr(criteria.BE_LOWER_PCT)) and hi <= Decimal(repr(criteria.BE_UPPER_PCT))
    return float(lo), float(hi), ok


def _decision_making(parameter: BeParameter) -> bool:
    return parameter != "auc0inf" or criteria.BE_AUC0INF_DECISION_MAKING


def analyse_parameter(data: BeInput, parameter: BeParameter) -> BeParameterResult:
    """Log-scale crossover ANOVA and BE assessment for one parameter (URS-BE-001 to 003, 017).

    ICH M13A (2024); FDA BE statistics guidance. Terms: sequence, subject(sequence), period,
    treatment. Reports the type I ANOVA table, the T - R log difference and SE, PE and 90% CI
    (full precision and rounded), the decision, both TOST p-values and CVw. Adds a note when the
    rounded-CI decision and TOST at alpha 0.05 disagree (possible only at the rounding edge).

    Raises:
        ValueError: the parameter is not supplied, or the residual error is zero.
    """
    fit, anova = _fit(data, parameter)
    diff = float(fit.coef[-1])
    se = math.sqrt(fit.mse * float(fit.xtx_inv[-1, -1]))
    pe, lo, hi = gmr_interval(diff, se, fit.df)
    lo_r, hi_r, ok = be_decision(lo, hi)
    p_lower, p_upper = tost_p_values(diff, se, fit.df)
    alpha = _tost_alpha()
    notes = []
    tost_ok = p_lower < alpha and p_upper < alpha
    if tost_ok != ok:
        notes.append(
            f"Rounded CI limits {lo_r:.2f}-{hi_r:.2f} {'pass' if ok else 'fail'} but TOST at "
            f"alpha {alpha:.2f} {'passes' if tost_ok else 'fails'} (unrounded limits "
            f"{lo}-{hi}); the decision follows the rounded-CI rule ({criteria.BE_ROUNDING_MODE}, "
            "pending confirmation against the target agency text)."
        )
    subjects = {r.subject: r.sequence for r in data.records}
    return BeParameterResult(
        parameter=parameter,
        decision_making=_decision_making(parameter),
        n_tr=sum(1 for s in subjects.values() if s == "TR"),
        n_rt=sum(1 for s in subjects.values() if s == "RT"),
        df=fit.df,
        mse=fit.mse,
        diff_log=diff,
        se_log=se,
        t_value=float(sps.t.ppf((1.0 + criteria.BE_CI_LEVEL) / 2.0, fit.df)),
        pe_pct=pe,
        ci_lower_pct=lo,
        ci_upper_pct=hi,
        ci_lower_rounded=lo_r,
        ci_upper_rounded=hi_r,
        within_limits=ok,
        tost_p_lower=p_lower,
        tost_p_upper=p_upper,
        cv_within_pct=cv_within_pct(fit.mse),
        anova=anova,
        notes=tuple(notes),
    )


def assess_bioequivalence(data: BeInput, *, timestamp: datetime | None = None) -> BeResult:
    """Average bioequivalence of a 2x2 crossover (URS-BE-001 to 017, URS-GEN-001, 002).

    ICH M13A (2024); FDA BE statistics guidance. Analyses Cmax and AUC0-t, and AUC0-inf when
    supplied. Bioequivalent when every decision-making parameter's rounded 90% CI lies within
    80.00-125.00%. Whether AUC0-inf is decision-making is ``BE_AUC0INF_DECISION_MAKING``
    (placeholder; agencies differ, pending confirmation against the target agency text).
    """
    metadata = make_metadata({"inputs": data.model_dump(mode="json")}, "bioequivalence", timestamp)
    names: list[BeParameter] = ["cmax", "auc0t"]
    if data.records[0].auc0inf is not None:
        names.append("auc0inf")
    results = tuple(analyse_parameter(data, p) for p in names)
    deciding = tuple(r for r in results if r.decision_making)
    bioequivalent = all(r.within_limits for r in deciding)

    lo, hi = criteria.BE_LOWER_PCT, criteria.BE_UPPER_PCT
    notes = [
        f"90% CI limits rounded {criteria.BE_ROUNDING_MODE} to {criteria.BE_ROUND_DECIMALS} "
        f"decimals before comparison with {lo:.2f}-{hi:.2f}% (placeholder rounding rule, "
        "pending confirmation against the target agency text)."
    ]
    if "auc0inf" in names:
        notes.append(
            "AUC0-inf is decision-making (BE_AUC0INF_DECISION_MAKING = True)."
            if criteria.BE_AUC0INF_DECISION_MAKING
            else "AUC0-inf is reported but not decision-making "
            "(BE_AUC0INF_DECISION_MAKING = False)."
        )
        notes[-1] += (
            " Agencies differ (FDA vs EMA); pending confirmation against the target agency text."
        )
    # Rounded-CI vs TOST disagreements are the only per-parameter notes; surface them here
    rounding_sensitive = [r.parameter for r in results if r.notes]
    notes.extend(f"{r.parameter}: {n}" for r in results for n in r.notes)

    if bioequivalent:
        passed = ", ".join(r.parameter for r in deciding)
        conclusion = (
            f"Bioequivalent: the rounded 90% CI of the T/R geometric mean ratio lies within "
            f"{lo:.2f}-{hi:.2f}% for {passed}."
        )
    else:
        failed = ", ".join(
            f"{r.parameter} ({r.ci_lower_rounded:.2f}-{r.ci_upper_rounded:.2f}%)"
            for r in deciding
            if not r.within_limits
        )
        conclusion = (
            f"Not bioequivalent: the rounded 90% CI lies outside {lo:.2f}-{hi:.2f}% for {failed}."
        )
    if rounding_sensitive:
        conclusion += (
            f" The verdict for {', '.join(rounding_sensitive)} depends on the rounding rule "
            "(rounded CI and TOST disagree); see notes."
        )

    return BeResult(
        inputs=data,
        metadata=metadata,
        parameters=results,
        decision_parameters=tuple(r.parameter for r in deciding),
        bioequivalent=bioequivalent,
        conclusion=conclusion,
        notes=tuple(notes),
        warnings=(),
    )
