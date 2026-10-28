import json
from pathlib import Path
from typing import Any

import pytest

be = pytest.importorskip("cmc_stats.core.be", reason="bioequivalence module not built yet")
from cmc_stats.models import BeInput  # noqa: E402

CASES = sorted((Path(__file__).parent / "data").glob("GOLD-BE-*.json"))
VALUES = (
    "mse",
    "diff_log",
    "se_log",
    "t_value",
    "pe_pct",
    "ci_lower_pct",
    "ci_upper_pct",
    "tost_p_lower",
    "tost_p_upper",
    "cv_within_pct",
)


@pytest.mark.parametrize("case_file", CASES, ids=lambda p: p.stem)
def test_be_golden(case_file: Path) -> None:
    """URS-BE-001, URS-BE-002, URS-BE-003, URS-BE-016, URS-BE-017: full analysis matches
    independent R output (GOLD-BE-003 also URS-BE-012 unbalanced, URS-BE-014 no AUC0-inf)."""
    case: dict[str, Any] = json.loads(case_file.read_text(encoding="utf-8"))
    exp, tol = case["expected"], case["tolerance"]
    result = be.assess_bioequivalence(BeInput.model_validate(case["inputs"]))

    assert [p.parameter for p in result.parameters] == [e["parameter"] for e in exp["parameters"]]
    for par, e in zip(result.parameters, exp["parameters"], strict=True):
        assert (par.n_tr, par.n_rt, par.df) == (e["n_tr"], e["n_rt"], e["df"]), par.parameter
        for name in VALUES:
            assert getattr(par, name) == pytest.approx(e[name], abs=tol), (par.parameter, name)
        assert par.ci_lower_rounded == e["ci_lower_rounded"], par.parameter
        assert par.ci_upper_rounded == e["ci_upper_rounded"], par.parameter
        assert par.within_limits == e["within_limits"], par.parameter
        assert [(r.term, r.df) for r in par.anova] == [(a["term"], a["df"]) for a in e["anova"]]
        for row, a in zip(par.anova, e["anova"], strict=True):
            assert row.ss == pytest.approx(a["ss"], abs=tol), (par.parameter, row.term)
            assert row.ms == pytest.approx(a["ms"], abs=tol), (par.parameter, row.term)
    assert result.bioequivalent == exp["bioequivalent"]
