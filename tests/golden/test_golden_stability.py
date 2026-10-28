import json
from pathlib import Path
from typing import Any

import pytest

stab = pytest.importorskip("cmc_stats.core.stability", reason="stability module not built yet")
from cmc_stats.models import StabilityInput  # noqa: E402

CASES = sorted((Path(__file__).parent / "data").glob("GOLD-STAB-*.json"))


def load(case_file: Path) -> dict[str, Any]:
    case: dict[str, Any] = json.loads(case_file.read_text(encoding="utf-8"))
    return case


@pytest.mark.parametrize("case_file", CASES, ids=lambda p: p.stem)
def test_stability_golden(case_file: Path) -> None:
    """URS-STAB-001 to 005, URS-STAB-008: full analysis matches independent R output."""
    case = load(case_file)
    exp, tol = case["expected"], case["tolerance"]
    result = stab.estimate_shelf_life(StabilityInput.model_validate(case["inputs"]))

    pool = result.poolability
    assert pool.model == exp["model"]
    assert pool.slopes.f_value == pytest.approx(exp["slopes"]["F"], abs=tol)
    assert (pool.slopes.df_num, pool.slopes.df_den) == (
        exp["slopes"]["df_num"],
        exp["slopes"]["df_den"],
    )
    assert pool.slopes.p_value == pytest.approx(exp["slopes"]["p"], abs=tol)
    if exp["intercepts"] is None:
        assert pool.intercepts is None
    else:
        assert pool.intercepts is not None
        assert pool.intercepts.f_value == pytest.approx(exp["intercepts"]["F"], abs=tol)
        assert (pool.intercepts.df_num, pool.intercepts.df_den) == (
            exp["intercepts"]["df_num"],
            exp["intercepts"]["df_den"],
        )
        assert pool.intercepts.p_value == pytest.approx(exp["intercepts"]["p"], abs=tol)

    assert len(result.batch_fits) == len(exp["batch_fits"])
    for fit, e in zip(result.batch_fits, exp["batch_fits"], strict=True):
        assert fit.label == e["label"]
        assert fit.residual_df == e["residual_df"]
        for name in ("intercept", "slope", "intercept_se", "slope_se", "mse"):
            assert getattr(fit, name) == pytest.approx(e[name], abs=tol), name

    assert len(result.per_batch) == len(exp["per_batch"])
    for line, e in zip(result.per_batch, exp["per_batch"], strict=True):
        assert line.label == e["label"]
        assert line.df == e["df"]
        for name in ("intercept", "slope", "t_value", "bound_at_0", "crossing_months"):
            assert getattr(line, name) == pytest.approx(e[name], abs=tol), name

    assert result.governing_batch == exp["governing_batch"]
    assert result.crossing_months == pytest.approx(exp["crossing_months"], abs=tol)
    assert result.extrapolation.x_months == pytest.approx(exp["x_months"], abs=tol)
    assert result.extrapolation.cap_months == pytest.approx(exp["cap_months"], abs=tol)
    assert result.proposed_shelf_life_months == exp["proposed_shelf_life_months"]


@pytest.mark.parametrize("case_file", CASES, ids=lambda p: p.stem)
def test_stability_golden_crosscheck(case_file: Path) -> None:
    """URS-STAB-002, URS-STAB-003, URS-STAB-005: agrees with the user's statsmodels results."""
    case = load(case_file)
    check = case["crosscheck"]
    values, tols = check["values"], check["tolerance"]
    result = stab.estimate_shelf_life(StabilityInput.model_validate(case["inputs"]))
    actual: dict[str, Any] = {
        "model": result.poolability.model,
        "slope_p": result.poolability.slopes.p_value,
        "intercept_p": (
            result.poolability.intercepts.p_value if result.poolability.intercepts else None
        ),
        "governing_batch": result.governing_batch,
        "crossing_months": result.crossing_months,
        "proposed_shelf_life_months": result.proposed_shelf_life_months,
    }
    for name, value in values.items():
        if name in tols:
            assert actual[name] == pytest.approx(value, abs=tols[name]), name
        else:
            assert actual[name] == value, name
