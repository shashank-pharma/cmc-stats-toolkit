"""Unit tests for 2x2 crossover bioequivalence. Each test cites the requirement it proves."""

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
from scipy import stats as sps

from cmc_stats import __version__, criteria
from cmc_stats.core import be
from cmc_stats.models import DISCLAIMER, BeInput, BeRecord

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
TREATMENT_COEF = "C(treatment, Treatment('R'))[T.T]"

# Dummy data (hand-written): subject, sequence, then T and R values for Cmax, AUC0-t, AUC0-inf
BASE = [
    ("S01", "TR", 102.3, 98.7, 1510.2, 1480.6, 1602.4, 1571.0),
    ("S02", "RT", 88.1, 93.4, 1322.8, 1390.1, 1405.5, 1468.3),
    ("S03", "TR", 120.5, 115.2, 1755.0, 1702.3, 1850.2, 1799.9),
    ("S04", "RT", 95.6, 99.8, 1440.7, 1425.2, 1530.1, 1518.8),
    ("S05", "TR", 110.2, 104.9, 1600.3, 1612.7, 1695.0, 1702.6),
    ("S06", "RT", 79.4, 85.0, 1210.5, 1250.9, 1290.4, 1333.7),
    ("S07", "TR", 99.9, 101.2, 1495.5, 1460.0, 1580.2, 1549.3),
    ("S08", "RT", 105.3, 100.1, 1550.8, 1530.4, 1645.6, 1622.0),
    ("S09", "TR", 93.8, 97.2, 1388.4, 1415.9, 1470.3, 1502.8),
    ("S10", "RT", 114.6, 109.3, 1688.2, 1650.7, 1781.9, 1740.5),
    ("S11", "TR", 86.7, 90.1, 1275.3, 1301.8, 1352.6, 1380.2),
    ("S12", "RT", 101.5, 98.4, 1520.9, 1498.3, 1610.7, 1585.4),
]
# One more TR subject, for the unbalanced (7/6) case
EXTRA_TR = ("S13", "TR", 97.4, 95.0, 1460.2, 1442.8, 1548.1, 1530.6)


def records(base: list[tuple[Any, ...]] = BASE, *, with_inf: bool = True) -> list[dict[str, Any]]:
    """Long records: TR -> period 1 T, period 2 R; RT the reverse."""
    out = []
    for subject, seq, c_t, c_r, a_t, a_r, i_t, i_r in base:
        for period in (1, 2):
            trt = ("T" if period == 1 else "R") if seq == "TR" else ("R" if period == 1 else "T")
            rec: dict[str, Any] = {
                "subject": subject,
                "sequence": seq,
                "period": period,
                "treatment": trt,
                "cmax": c_t if trt == "T" else c_r,
                "auc0t": a_t if trt == "T" else a_r,
            }
            if with_inf:
                rec["auc0inf"] = i_t if trt == "T" else i_r
            out.append(rec)
    return out


def make_input(recs: list[dict[str, Any]] | None = None, **overrides: Any) -> BeInput:
    fields: dict[str, Any] = {
        "design": "2x2_crossover",
        "limits": "average",
        "records": recs if recs is not None else records(),
    }
    fields.update(overrides)
    return BeInput.model_validate(fields)


def find(recs: list[dict[str, Any]], subject: str, period: int) -> dict[str, Any]:
    return next(r for r in recs if r["subject"] == subject and r["period"] == period)


def scale_test(recs: list[dict[str, Any]], parameter: str, factor: float) -> list[dict[str, Any]]:
    """Multiply every Test value of one parameter by ``factor``."""
    return [
        {**r, parameter: r[parameter] * factor} if r["treatment"] == "T" else dict(r) for r in recs
    ]


def scale_reference(
    recs: list[dict[str, Any]], parameter: str, factor: float
) -> list[dict[str, Any]]:
    """Multiply every Reference value of one parameter by ``factor``."""
    return [
        {**r, parameter: r[parameter] * factor} if r["treatment"] == "R" else dict(r) for r in recs
    ]


def sm_fit(recs: list[dict[str, Any]], parameter: str) -> Any:
    """Independent statsmodels fit of the same 2x2 crossover model."""
    d = pd.DataFrame(recs)
    return smf.ols(
        f"np.log({parameter}) ~ C(sequence) + C(subject) + C(period)"
        " + C(treatment, Treatment('R'))",
        d,
    ).fit()


def param(result: Any, name: str) -> Any:
    return next(p for p in result.parameters if p.parameter == name)


# --- URS-BE-002: log-scale ANOVA ----------------------------------------------------------


@pytest.mark.parametrize("parameter", ["cmax", "auc0t", "auc0inf"])
@pytest.mark.filterwarnings("ignore::statsmodels.tools.sm_exceptions.SingularMatrixWarning")
def test_fit_matches_statsmodels(parameter: str) -> None:
    """URS-BE-002: T - R log difference, SE, MSE and residual df match an independent fit."""
    recs = records()
    ref = sm_fit(recs, parameter)
    res = be.analyse_parameter(make_input(recs), parameter)
    assert res.diff_log == pytest.approx(ref.params[TREATMENT_COEF], abs=1e-12)
    assert res.se_log == pytest.approx(ref.bse[TREATMENT_COEF], abs=1e-12)
    assert res.mse == pytest.approx(ref.mse_resid, abs=1e-14)
    assert res.df == int(ref.df_resid) == len(BASE) - 2


@pytest.mark.filterwarnings("ignore::statsmodels.tools.sm_exceptions.SingularMatrixWarning")
def test_anova_table_terms_ss_and_df() -> None:
    """URS-BE-002, URS-BE-017: type I table in the order sequence, subject(sequence), period,
    treatment, residual; subject(sequence) has n - 2 df.

    Each SS is checked as the drop in residual SS between successive statsmodels fits.
    statsmodels' own ``anova_lm(typ=1)`` is not used: with subject aliased to sequence it
    misassigns both df and SS (checked against R, which matches this code: GOLD-BE-*)."""
    recs = records()
    d = pd.DataFrame(recs)
    formulas = [
        "1",
        "C(sequence)",
        "C(sequence) + C(subject)",
        "C(sequence) + C(subject) + C(period)",
        "C(sequence) + C(subject) + C(period) + C(treatment)",
    ]
    rss = [smf.ols(f"np.log(cmax) ~ {f}", d).fit().ssr for f in formulas]
    rows = be.analyse_parameter(make_input(recs), "cmax").anova
    n = len(BASE)
    assert [(r.term, r.df) for r in rows] == [
        ("sequence", 1),
        ("subject(sequence)", n - 2),
        ("period", 1),
        ("treatment", 1),
        ("residual", n - 2),
    ]
    expected_ss = [rss[k - 1] - rss[k] for k in range(1, 5)] + [rss[4]]
    for row, ss in zip(rows, expected_ss, strict=True):
        assert row.ss == pytest.approx(ss, abs=1e-12), row.term
        assert row.ms == pytest.approx(row.ss / row.df, rel=1e-12), row.term


# --- URS-BE-001, URS-BE-016: acceptance range after rounding ------------------------------


@pytest.mark.parametrize(
    ("lower", "upper", "rounded", "passes"),
    [
        (79.9950000001, 110.0, (80.00, 110.00), True),
        (79.9949999999, 110.0, (79.99, 110.00), False),
        (90.0, 125.0049999999, (90.00, 125.00), True),
        (90.0, 125.0050000001, (90.00, 125.01), False),
        (80.0, 125.0, (80.00, 125.00), True),
        (79.0, 126.0, (79.00, 126.00), False),
    ],
)
def test_decision_uses_limits_rounded_half_up(
    lower: float, upper: float, rounded: tuple[float, float], passes: bool
) -> None:
    """URS-BE-001, URS-BE-016: limits rounded half up to 2 decimals, then compared with
    80.00-125.00 inclusive (rounding mode is a placeholder pending agency text)."""
    lo_r, hi_r, ok = be.be_decision(lower, upper)
    assert (lo_r, hi_r) == rounded
    assert ok is passes


def test_rounding_uses_exact_binary_value() -> None:
    """URS-BE-016: rounding acts on the exact stored value, not the printed one.

    79.985 is stored as 79.98499999..., so half up gives 79.98 (not 79.99); 125.005 is stored
    as 125.00499999..., so it rounds to 125.00 and passes; 79.995 is stored as 79.99500000...05,
    so it rounds to 80.00."""
    assert be.be_decision(79.985, 110.0)[0] == 79.98
    assert be.be_decision(90.0, 125.005) == (90.00, 125.00, True)
    assert be.be_decision(79.995, 110.0) == (80.00, 110.00, True)


def test_result_keeps_unrounded_and_rounded_limits() -> None:
    """URS-BE-016, URS-BE-017: both the full-precision and the rounded limits are reported."""
    res = be.analyse_parameter(make_input(), "cmax")
    assert res.ci_lower_rounded == be.be_decision(res.ci_lower_pct, res.ci_upper_pct)[0]
    assert res.ci_lower_pct != res.ci_lower_rounded
    assert res.within_limits is True


# --- URS-BE-003: TOST and within-subject CV -----------------------------------------------


def test_gmr_interval_formula() -> None:
    """URS-BE-001: PE = 100 exp(d), CI = 100 exp(d -/+ t(0.95, df) SE)."""
    d, se, df = -0.02, 0.05, 10
    t = sps.t.ppf(0.95, df)
    pe, lo, hi = be.gmr_interval(d, se, df)
    assert pe == pytest.approx(100 * math.exp(d), rel=1e-15)
    assert lo == pytest.approx(100 * math.exp(d - t * se), rel=1e-15)
    assert hi == pytest.approx(100 * math.exp(d + t * se), rel=1e-15)


def test_tost_p_values_formula() -> None:
    """URS-BE-003: p_lower = P(T > (d - ln 0.8)/SE), p_upper = P(T < (d - ln 1.25)/SE)."""
    d, se, df = 0.03, 0.06, 12
    p_lower, p_upper = be.tost_p_values(d, se, df)
    assert p_lower == pytest.approx(sps.t.sf((d - math.log(0.80)) / se, df), rel=1e-12)
    assert p_upper == pytest.approx(sps.t.cdf((d - math.log(1.25)) / se, df), rel=1e-12)


def test_tost_agrees_with_ci_away_from_rounding_boundary() -> None:
    """URS-BE-003: away from the boundary, CI within limits <=> both TOST p < 0.05."""
    res = be.analyse_parameter(make_input(), "auc0t")
    assert res.within_limits
    assert res.tost_p_lower < 0.05
    assert res.tost_p_upper < 0.05


@pytest.mark.parametrize("se", [0.0, -0.01])
def test_tost_refuses_non_positive_se(se: float) -> None:
    """URS-BE-003: TOST is undefined without a positive standard error; refuse, don't guess."""
    with pytest.raises(ValueError, match="standard error must be > 0"):
        be.tost_p_values(0.0, se, 10)


def test_cv_within_formula() -> None:
    """URS-BE-003: CVw = 100 sqrt(exp(MSE) - 1)."""
    assert be.cv_within_pct(0.04) == pytest.approx(100 * math.sqrt(math.exp(0.04) - 1))
    res = be.analyse_parameter(make_input(), "cmax")
    assert res.cv_within_pct == pytest.approx(100 * math.sqrt(math.exp(res.mse) - 1))


@pytest.mark.filterwarnings("ignore::statsmodels.tools.sm_exceptions.SingularMatrixWarning")
def test_note_when_rounded_ci_and_tost_disagree() -> None:
    """URS-BE-003, URS-BE-016: lower limit 79.997 rounds to 80.00 (pass) while TOST p_lower
    > 0.05; the result follows the rounded-CI rule and says so in the parameter notes, the
    result notes and the conclusion (URS-BE-017)."""
    base = records()
    lower = 100 * math.exp(sm_fit(base, "cmax").conf_int(alpha=0.10).loc[TREATMENT_COEF].iloc[0])
    recs = scale_test(base, "cmax", 79.997 / lower)
    res = be.analyse_parameter(make_input(recs), "cmax")
    assert res.ci_lower_pct == pytest.approx(79.997, abs=1e-9)
    assert res.ci_lower_rounded == 80.00
    assert res.within_limits is True
    assert res.tost_p_lower > 0.05
    assert any("TOST" in n and "rounded" in n for n in res.notes)

    result = be.assess_bioequivalence(make_input(recs), timestamp=FIXED_TIME)
    assert result.bioequivalent is True
    assert any(n.startswith("cmax: ") and "TOST" in n for n in result.notes)
    assert "verdict for cmax depends on the rounding rule" in result.conclusion


def test_no_rounding_note_away_from_boundary() -> None:
    """URS-BE-017: when rounded CI and TOST agree, no disagreement note or caveat appears."""
    result = be.assess_bioequivalence(make_input(), timestamp=FIXED_TIME)
    assert not any("TOST" in n for n in result.notes)
    assert "rounding rule" not in result.conclusion


# --- URS-BE-012, URS-BE-014, URS-BE-017: parameters, counts, overall decision --------------


@pytest.mark.filterwarnings("ignore::statsmodels.tools.sm_exceptions.SingularMatrixWarning")
def test_unbalanced_sequences_accepted_and_counted() -> None:
    """URS-BE-012: 7 TR / 6 RT runs, matches statsmodels and reports n per sequence."""
    recs = records([*BASE, EXTRA_TR])
    res = be.analyse_parameter(make_input(recs), "cmax")
    assert (res.n_tr, res.n_rt, res.df) == (7, 6, 11)
    assert res.diff_log == pytest.approx(sm_fit(recs, "cmax").params[TREATMENT_COEF], abs=1e-12)


def test_auc0inf_absent_gives_two_parameters() -> None:
    """URS-BE-014: without AUC0-inf only Cmax and AUC0-t are analysed and decide BE."""
    result = be.assess_bioequivalence(make_input(records(with_inf=False)), timestamp=FIXED_TIME)
    assert [p.parameter for p in result.parameters] == ["cmax", "auc0t"]
    assert result.decision_parameters == ("cmax", "auc0t")
    assert result.bioequivalent is True


def test_analysing_absent_auc0inf_is_refused() -> None:
    """URS-BE-014: asking for AUC0-inf when it was not supplied raises, never imputes."""
    with pytest.raises(ValueError, match="auc0inf is not supplied"):
        be.analyse_parameter(make_input(records(with_inf=False)), "auc0inf")


def test_auc0inf_present_is_analysed_and_decides() -> None:
    """URS-BE-014, URS-BE-017: a failing AUC0-inf fails overall BE (decision-making True)."""
    recs = scale_reference(records(), "auc0inf", 1 / 0.7)  # T/R 0.7; keeps AUC0-inf >= AUC0-t
    result = be.assess_bioequivalence(make_input(recs), timestamp=FIXED_TIME)
    assert [p.parameter for p in result.parameters] == ["cmax", "auc0t", "auc0inf"]
    assert param(result, "cmax").within_limits
    assert param(result, "auc0t").within_limits
    assert param(result, "auc0inf").within_limits is False
    assert param(result, "auc0inf").decision_making is True
    assert result.bioequivalent is False
    assert "auc0inf" in result.conclusion


def test_auc0inf_reported_but_not_deciding_when_flag_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """URS-BE-014: with BE_AUC0INF_DECISION_MAKING False, AUC0-inf is reported only."""
    monkeypatch.setattr(criteria, "BE_AUC0INF_DECISION_MAKING", False)
    recs = scale_reference(records(), "auc0inf", 1 / 0.7)  # T/R 0.7; keeps AUC0-inf >= AUC0-t
    result = be.assess_bioequivalence(make_input(recs), timestamp=FIXED_TIME)
    inf = param(result, "auc0inf")
    assert inf.within_limits is False
    assert inf.decision_making is False
    assert result.decision_parameters == ("cmax", "auc0t")
    assert result.bioequivalent is True
    assert any("AUC0-inf" in n and "not decision-making" in n for n in result.notes)
    assert be.auc0inf_limitation_note() in result.notes


def test_result_reports_every_reviewer_value() -> None:
    """URS-BE-017: counts, df, MSE, difference, SE, t, PE, CI (both forms), pass, TOST, CVw."""
    res = be.analyse_parameter(make_input(), "cmax")
    assert (res.n_tr, res.n_rt, res.df) == (6, 6, 10)
    assert res.t_value == pytest.approx(sps.t.ppf(criteria.BE_CI_LEVEL + 0.05, 10))
    pe, lo, hi = be.gmr_interval(res.diff_log, res.se_log, res.df)
    assert (res.pe_pct, res.ci_lower_pct, res.ci_upper_pct) == (pe, lo, hi)
    assert res.ci_lower_pct != round(res.ci_lower_pct, 2)  # kept at full precision
    assert res.mse > 0
    assert 0 < res.tost_p_lower < 1
    assert 0 < res.tost_p_upper < 1


# --- URS-BE-004 to 006: designs not supported in v1 ---------------------------------------


def test_declared_replicate_design_refused() -> None:
    """URS-BE-004: a declared replicate design is refused."""
    with pytest.raises(ValidationError, match="replicate.*not supported in v1"):
        make_input(design="replicate")


@pytest.mark.parametrize("sequence", ["TRR", "RTR", "TRTR"])
def test_replicate_sequence_refused(sequence: str) -> None:
    """URS-BE-004: a sequence longer than two treatments means a replicate design."""
    recs = records()
    for r in recs:
        if r["subject"] == "S01":
            r["sequence"] = sequence
    with pytest.raises(ValidationError, match="replicate.*not supported in v1"):
        make_input(recs)


def test_third_period_refused_as_replicate() -> None:
    """URS-BE-004: a period other than 1 or 2 means a replicate design."""
    recs = records() + [{**find(records(), "S01", 2), "period": 3}]
    with pytest.raises(ValidationError, match="replicate.*not supported in v1"):
        make_input(recs)


def test_reference_scaled_limits_refused() -> None:
    """URS-BE-005: reference-scaled limits are refused."""
    with pytest.raises(ValidationError, match="reference-scaled.*not supported in v1"):
        make_input(limits="reference_scaled")


def test_parallel_design_refused() -> None:
    """URS-BE-006: a parallel design is refused."""
    with pytest.raises(ValidationError, match="parallel.*not supported in v1"):
        make_input(design="parallel")


@pytest.mark.parametrize("missing", ["design", "limits"])
def test_design_and_limits_have_no_default(missing: str) -> None:
    """URS-BE-004, URS-BE-005: the design and limits must be stated explicitly."""
    fields = make_input().model_dump()
    del fields[missing]
    with pytest.raises(ValidationError, match=missing):
        BeInput.model_validate(fields)


# --- URS-BE-007 to 015: input validation --------------------------------------------------


@pytest.mark.parametrize(
    ("parameter", "value"), [("cmax", 0.0), ("auc0t", -1.0), ("auc0inf", -5.0)]
)
def test_non_positive_value_rejected(parameter: str, value: float) -> None:
    """URS-BE-007: zero or negative values are rejected, naming subject, period, parameter."""
    rec = {**find(records(), "S03", 2), parameter: value}
    with pytest.raises(ValidationError, match=rf"S03.*period 2.*{parameter}"):
        BeRecord.model_validate(rec)


def test_subject_missing_period_rejected() -> None:
    """URS-BE-008: a subject with only one period is rejected and named."""
    recs = [r for r in records() if not (r["subject"] == "S03" and r["period"] == 2)]
    with pytest.raises(ValidationError, match=r"S03.*missing period 2"):
        make_input(recs)


def test_duplicate_subject_period_rejected() -> None:
    """URS-BE-009: two records for the same subject and period are rejected."""
    recs = records()
    find(recs, "S03", 2)["period"] = 1
    with pytest.raises(ValidationError, match=r"duplicate.*S03.*period 1"):
        make_input(recs)


def test_unknown_sequence_rejected() -> None:
    """URS-BE-010: a two-letter sequence other than TR or RT is rejected."""
    recs = records()
    for r in recs:
        if r["subject"] == "S01":
            r["sequence"] = "AB"
    with pytest.raises(ValidationError, match=r"S01.*'TR' or 'RT'"):
        make_input(recs)


def test_treatment_not_matching_sequence_rejected() -> None:
    """URS-BE-010: TR means period 1 T and period 2 R; a swap is rejected and named."""
    recs = records()
    find(recs, "S01", 1)["treatment"] = "R"
    find(recs, "S01", 2)["treatment"] = "T"
    with pytest.raises(ValidationError, match=r"S01.*TR.*period 1.*T"):
        make_input(recs)


def test_subject_in_both_sequences_rejected() -> None:
    """URS-BE-011: one subject listed under TR and RT is rejected."""
    recs = records()
    rec = find(recs, "S01", 2)
    rec["sequence"], rec["treatment"] = "RT", "T"
    with pytest.raises(ValidationError, match=r"S01.*both sequences"):
        make_input(recs)


def test_empty_sequence_rejected() -> None:
    """URS-BE-012: each sequence needs at least 1 subject."""
    tr_only = [row for row in BASE if row[1] == "TR"]
    with pytest.raises(ValidationError, match=r"RT.*at least 1 subject"):
        make_input(records(tr_only))


def test_residual_df_below_one_rejected() -> None:
    """URS-BE-013: one subject per sequence gives residual df 0 and is rejected."""
    with pytest.raises(
        ValidationError, match=r"2 subjects.*residual degrees of freedom 0.*at least 3"
    ):
        make_input(records(BASE[:2]))


def test_three_subjects_pass_the_df_check_then_meet_the_12_subject_rule() -> None:
    """URS-BE-013, URS-BE-019: 3 subjects (residual df 1) pass the df check and are then
    refused by the 12-subject rule, not by the df rule."""
    with pytest.raises(ValidationError) as err:
        make_input(records(BASE[:3]))
    assert "residual degrees of freedom" not in str(err.value)
    assert "3 evaluable subjects supplied; at least 12 required" in str(err.value)


# --- URS-BE-019: at least 12 evaluable subjects ---------------------------------------------


def test_eleven_subjects_rejected_naming_the_count() -> None:
    """URS-BE-019: ICH M13A 2.2.3.1, p. 12: fewer than 12 evaluable subjects (here 6 TR /
    5 RT) is refused, giving the count, the minimum and the source."""
    with pytest.raises(
        ValidationError,
        match=r"11 evaluable subjects supplied; at least 12 required "
        r"\(ICH M13A, 2024, 2\.2\.3\.1\)",
    ):
        make_input(records(BASE[:11]))


def test_twelve_subjects_accepted() -> None:
    """URS-BE-019: exactly 12 evaluable subjects is accepted."""
    data = make_input()
    assert len({r.subject for r in data.records}) == criteria.BE_MIN_EVALUABLE_SUBJECTS == 12
    assert be.analyse_parameter(data, "cmax").df == 10


def test_subject_missing_a_period_is_rejected_not_counted_as_unevaluable() -> None:
    """URS-BE-008, URS-BE-019: 12 subjects with one period missing is refused for the missing
    period; the tool never drops the subject and counts 11 evaluable ones."""
    recs = [r for r in records() if not (r["subject"] == "S12" and r["period"] == 1)]
    with pytest.raises(ValidationError, match=r"S12.*missing period 1"):
        make_input(recs)


def test_partial_auc0inf_rejected_listing_records() -> None:
    """URS-BE-014: AUC0-inf for some records but not all is rejected, listing the gaps."""
    recs = records()
    del find(recs, "S02", 1)["auc0inf"]
    del find(recs, "S05", 2)["auc0inf"]
    with pytest.raises(ValidationError, match=r"auc0inf.*S02 period 1.*S05 period 2"):
        make_input(recs)


@pytest.mark.parametrize(
    ("field", "value"),
    [("cmax", float("nan")), ("auc0t", float("inf")), ("auc0inf", float("nan"))],
)
def test_non_finite_value_rejected(field: str, value: float) -> None:
    """URS-BE-015: NaN and infinity are rejected."""
    with pytest.raises(ValidationError):
        BeRecord.model_validate({**find(records(), "S01", 1), field: value})


def test_empty_subject_rejected() -> None:
    """URS-BE-015: subject IDs must not be empty."""
    with pytest.raises(ValidationError):
        BeRecord.model_validate({**find(records(), "S01", 1), "subject": ""})


@pytest.mark.parametrize("subject", ["S01 ", " S01", "S01\t"])
def test_padded_subject_rejected(subject: str) -> None:
    """URS-BE-015: leading or trailing whitespace would silently create a second subject."""
    with pytest.raises(ValidationError, match="leading or trailing whitespace"):
        BeRecord.model_validate({**find(records(), "S01", 1), "subject": subject})


def test_subject_ids_differing_only_by_case_rejected() -> None:
    """URS-BE-015: 'S01' and 's01' are reported as a clash, not treated as two subjects."""
    recs = records()
    find(recs, "S01", 2)["subject"] = "s01"
    with pytest.raises(ValidationError, match=r"differ only by letter case: 'S01', 's01'"):
        make_input(recs)


def test_auc0inf_below_auc0t_rejected() -> None:
    """URS-BE-018: AUC0-inf smaller than AUC0-t is impossible; subject and period named."""
    rec = {**find(records(), "S04", 2), "auc0inf": 1000.0}
    with pytest.raises(ValidationError, match=r"S04.*period 2.*auc0inf.*smaller than auc0t"):
        BeRecord.model_validate(rec)


def test_auc0inf_equal_to_auc0t_accepted() -> None:
    """URS-BE-018: no extrapolated area (AUC0-inf = AUC0-t) is valid and kept as entered."""
    rec = {**find(records(), "S04", 2)}
    rec["auc0inf"] = rec["auc0t"]
    assert BeRecord.model_validate(rec).auc0inf == rec["auc0t"]


def test_records_kept_as_entered() -> None:
    """URS-BE-017: input records are returned unchanged and in their original order."""
    recs = list(reversed(records()))
    result = be.assess_bioequivalence(make_input(recs), timestamp=FIXED_TIME)
    assert [r.subject for r in result.inputs.records] == [r["subject"] for r in recs]


# --- URS-GEN-001, URS-GEN-002 -------------------------------------------------------------


def test_result_carries_disclaimer_and_traceability_stamp() -> None:
    """URS-GEN-001, URS-GEN-002: disclaimer, versions, input hash and timestamp."""
    data = make_input()
    result = be.assess_bioequivalence(data, timestamp=FIXED_TIME)
    meta = result.metadata
    assert meta.disclaimer == DISCLAIMER
    assert meta.app_version == __version__
    assert meta.guideline_version == criteria.GUIDELINE_VERSIONS["bioequivalence"]
    assert meta.timestamp == FIXED_TIME
    assert result.inputs == data


def test_input_hash_tracks_inputs() -> None:
    """URS-GEN-002: equal inputs give equal hashes; any change gives a different hash."""
    a = be.assess_bioequivalence(make_input(), timestamp=FIXED_TIME)
    b = be.assess_bioequivalence(make_input(), timestamp=FIXED_TIME)
    c = be.assess_bioequivalence(make_input(scale_test(records(), "cmax", 1.01)))
    assert a.metadata.input_hash == b.metadata.input_hash
    assert a.metadata.input_hash != c.metadata.input_hash


# --- Properties ---------------------------------------------------------------------------


@settings(max_examples=25, deadline=None)
@given(factor=st.floats(min_value=0.5, max_value=2.0))
def test_scaling_test_values_scales_the_ratio(factor: float) -> None:
    """URS-BE-001, URS-BE-002: Test values x c gives PE x c and an unchanged MSE."""
    r0 = be.analyse_parameter(make_input(), "cmax")
    r1 = be.analyse_parameter(make_input(scale_test(records(), "cmax", factor)), "cmax")
    assert r1.pe_pct == pytest.approx(r0.pe_pct * factor, rel=1e-9)
    assert r1.mse == pytest.approx(r0.mse, rel=1e-9)


def test_swapping_labels_inverts_the_ratio() -> None:
    """URS-BE-001, URS-BE-002: relabelling T as R inverts the GMR and swaps the CI limits."""
    swapped = [
        {
            **r,
            "sequence": "RT" if r["sequence"] == "TR" else "TR",
            "treatment": "R" if r["treatment"] == "T" else "T",
        }
        for r in records()
    ]
    r0 = be.analyse_parameter(make_input(), "auc0t")
    r1 = be.analyse_parameter(make_input(swapped), "auc0t")
    assert r1.pe_pct == pytest.approx(10000.0 / r0.pe_pct, rel=1e-12)
    assert r1.ci_lower_pct == pytest.approx(10000.0 / r0.ci_upper_pct, rel=1e-12)
    assert r1.ci_upper_pct == pytest.approx(10000.0 / r0.ci_lower_pct, rel=1e-12)
    assert np.isclose(r1.mse, r0.mse, rtol=1e-12)


# --- URS-BE-020 to 022: known limitations ---------------------------------------------------


def test_every_result_carries_rounding_and_validation_limitations() -> None:
    """URS-BE-020, URS-BE-022: with or without AUC0-inf, every result carries the rounding-mode
    and validation-evidence known-limitation notes."""
    for recs in (records(), records(with_inf=False)):
        result = be.assess_bioequivalence(make_input(recs), timestamp=FIXED_TIME)
        for note in (be.ROUNDING_LIMITATION_NOTE, be.VALIDATION_LIMITATION_NOTE):
            assert note in result.notes
            assert note.startswith("Known limitation:")
    assert "at least 80.00 percent and not more than 125.00 percent" in (
        be.ROUNDING_LIMITATION_NOTE
    )
    assert "No guidance states the rounding mode" in be.ROUNDING_LIMITATION_NOTE
    assert "Schutz et al. 2014" in be.VALIDATION_LIMITATION_NOTE
    assert "v1.1" in be.VALIDATION_LIMITATION_NOTE


def test_auc0inf_limitation_only_when_auc0inf_is_analysed() -> None:
    """URS-BE-014, URS-BE-021: the AUC0-inf note cites FDA II.C.2 and the unchecked ANDA
    PK-endpoints guidance, and appears only when AUC0-inf is supplied."""
    with_inf = be.assess_bioequivalence(make_input(), timestamp=FIXED_TIME)
    without = be.assess_bioequivalence(make_input(records(with_inf=False)), timestamp=FIXED_TIME)
    note = be.auc0inf_limitation_note()
    assert note in with_inf.notes
    assert note not in without.notes
    assert note.startswith("Known limitation: AUC0-inf is decision-making")
    assert "II.C.2, p. 13" in note
    assert "was not checked" in note
