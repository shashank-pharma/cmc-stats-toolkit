import json
from pathlib import Path

import pytest

diss = pytest.importorskip("cmc_stats.core.dissolution", reason="dissolution module not built yet")

CASES = sorted((Path(__file__).parent / "data").glob("GOLD-DISS-*.json"))


@pytest.mark.parametrize("case_file", CASES, ids=lambda p: p.stem)
def test_dissolution_golden(case_file: Path) -> None:
    case = json.loads(case_file.read_text(encoding="utf-8"))
    reference, test = case["inputs"]["reference"], case["inputs"]["test"]
    tolerance = case["tolerance"]
    assert diss.f2(reference, test) == pytest.approx(case["expected"]["f2"], abs=tolerance)
    assert diss.f1(reference, test) == pytest.approx(case["expected"]["f1"], abs=tolerance)
