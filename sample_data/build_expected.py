"""Build sample_data/expected.json from committed sources only (URS-GEN-004).

Run from the repository root: uv run python sample_data/build_expected.py
No expected value is typed by hand:
- stability: the golden R outputs tests/golden/data/GOLD-STAB-001..003.json (same data)
- BE: R's own results in be_r_output.jsonl, written by generate_be.R
- dissolution: this project's core run on the committed CSVs (regression values, not an
  independent reference), labelled with the numpy version in generated_with.json

tests/test_sample_data.py checks that build() reproduces the committed expected.json exactly,
so the manifest cannot drift from its sources. After regenerating data, run this script and
review every change in expected.json before committing.
"""

import json
from pathlib import Path
from typing import Any

from cmc_stats import ui_helpers

HERE = Path(__file__).parent
GOLDEN = HERE.parent / "tests" / "golden" / "data"

STABILITY_SETTINGS = {
    "attribute": "Assay",
    "unit": "% label claim",
    "direction": "decrease",
    "storage_condition": "room_temperature",
    "lower_limit": 95.0,
    "significant_change_at_accelerated": False,
    "statistical_analysis_performed": True,
}
STABILITY_CASES = {"similar": "GOLD-STAB-001", "start": "GOLD-STAB-002", "faster": "GOLD-STAB-003"}
DISSOLUTION_SETTINGS: dict[str, dict[str, int]] = {
    "dissolution_similar.csv": {},
    "dissolution_slow.csv": {},
    "dissolution_similar_high_cv.csv": {"bootstrap_seed": 20261028, "bootstrap_n_resamples": 2000},
}
BE_SETTINGS = {"design": "2x2_crossover", "limits": "average"}


def build() -> dict[str, Any]:
    """The manifest as a dict, from committed sources only."""
    files: dict[str, Any] = {}
    for case, gold in STABILITY_CASES.items():
        e = json.loads((GOLDEN / f"{gold}.json").read_text("utf-8"))["expected"]
        files[f"stability_b003_{case}.csv"] = {
            "area": "stability",
            "settings": STABILITY_SETTINGS,
            "expected": {
                "source": f"independent R output, same data as {gold}",
                "model": e["model"],
                "governing_batch": e["governing_batch"],
                "crossing_months": e["crossing_months"],
                "proposed_shelf_life_months": e["proposed_shelf_life_months"],
            },
        }

    gen = json.loads((HERE / "generated_with.json").read_text("utf-8"))
    for name, settings in DISSOLUTION_SETTINGS.items():
        raw = (HERE / name).read_bytes()
        r = ui_helpers.run_analysis("dissolution", name, raw, settings)
        if r.f1 is None or r.f2 is None:
            raise ValueError(f"{name}: no f1/f2 (rapid dissolution); not a valid sample case")
        exp: dict[str, Any] = {
            "source": (
                "this project's core (regression values, not an independent reference); "
                f"data generated with numpy {gen['numpy']}, seed {gen['seed']}"
            ),
            "decision_basis": r.decision_basis,
            "f2_similar": r.f2_similar,
            "n_points_used": r.n_points_used,
            "f1": round(r.f1, 4),
            "f2": round(r.f2, 4),
        }
        if r.bootstrap is not None:
            exp["bootstrap_lower"] = round(r.bootstrap.lower, 4)
        files[name] = {"area": "dissolution", "settings": settings, "expected": exp}

    for line in (HERE / "be_r_output.jsonl").read_text("utf-8").splitlines():
        c = json.loads(line)
        files[c["file"]] = {
            "area": "be",
            "settings": BE_SETTINGS,
            "expected": {
                "source": (
                    f"independent R output ({c['r_version']}), generate_be.R seed {c['seed']}, "
                    f"true ratio {c['true_ratio']}, CV {c['cv_within']}"
                ),
                "bioequivalent": c["bioequivalent"],
                "parameters": c["parameters"],
            },
        }
    return {
        "description": (
            "Settings and expected results for each sample file; built by build_expected.py "
            "and checked by tests/test_sample_data.py (URS-GEN-004)."
        ),
        "files": dict(sorted(files.items())),
    }


if __name__ == "__main__":
    (HERE / "expected.json").write_text(json.dumps(build(), indent=2) + "\n", "utf-8")
    print("wrote", HERE / "expected.json")
