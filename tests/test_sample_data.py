"""Sample-data pack: every file runs through the UI parsing and core path and gives its
documented result (URS-GEN-004). Each test cites the requirement it proves."""

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from cmc_stats import ui_helpers as ui
from cmc_stats.models import BeResult, DissolutionResult, StabilityResult

SAMPLES = Path(__file__).parents[1] / "sample_data"
MANIFEST: dict[str, Any] = json.loads((SAMPLES / "expected.json").read_text("utf-8"))
FILES = sorted(MANIFEST["files"])

# The outcomes stated when the pack was requested; the manifest must agree with these
STATED = {
    "stability_b003_similar.csv": ("pooled", None, 34),
    "stability_b003_start.csv": ("common_slope", "B003", 29),
    "stability_b003_faster.csv": ("separate", "B003", 24),
    "dissolution_similar.csv": True,
    "dissolution_slow.csv": False,
    "be_24_subjects_cv20.csv": True,
    "be_12_subjects_cv45.csv": False,
}


def run(name: str) -> Any:
    entry = MANIFEST["files"][name]
    raw = (SAMPLES / name).read_bytes()
    return ui.run_analysis(entry["area"], name, raw, entry["settings"]), entry["expected"]


def test_manifest_readme_and_folder_agree() -> None:
    """URS-GEN-004: every CSV in the folder is in the manifest and the README, and back."""
    on_disk = sorted(p.name for p in SAMPLES.glob("*.csv"))
    assert on_disk == FILES
    readme = (SAMPLES / "README.md").read_text("utf-8")
    for name in FILES:
        assert name in readme, name
    assert set(STATED) <= set(FILES)


def test_builder_reproduces_committed_manifest() -> None:
    """URS-GEN-004: expected.json is exactly what build_expected.py makes from its committed
    sources (golden R outputs, R's BE output, the core on the committed CSVs)."""
    spec = importlib.util.spec_from_file_location("build_expected", SAMPLES / "build_expected.py")
    assert spec is not None
    assert spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    assert builder.build() == MANIFEST


def test_generator_versions_recorded() -> None:
    """URS-GEN-004: the numpy and R versions that generated the data are recorded in the
    provenance files and stated in the README."""
    numpy_version = json.loads((SAMPLES / "generated_with.json").read_text("utf-8"))["numpy"]
    r_versions = {
        json.loads(line)["r_version"].split(" (")[0]
        for line in (SAMPLES / "be_r_output.jsonl").read_text("utf-8").splitlines()
    }
    readme = (SAMPLES / "README.md").read_text("utf-8")
    assert f"numpy {numpy_version}" in readme
    for r in r_versions:
        assert r in readme


@pytest.mark.parametrize("name", FILES)
def test_sample_file_parses_with_template_columns(name: str) -> None:
    """URS-GEN-004: each file has exactly the header of its area's UI template."""
    area = MANIFEST["files"][name]["area"]
    header = (SAMPLES / name).read_text("utf-8").splitlines()[0]
    assert header == ui.template_csv(area).decode("utf-8").splitlines()[0]


@pytest.mark.parametrize("name", [n for n in FILES if n.startswith("stability")])
def test_stability_samples(name: str) -> None:
    """URS-GEN-004: model, governing batch and shelf-life as documented (R-verified values,
    the same data as GOLD-STAB-001..003)."""
    result, exp = run(name)
    assert isinstance(result, StabilityResult)
    model, governing, months = STATED[name]  # type: ignore[misc]
    assert (exp["model"], exp["governing_batch"], exp["proposed_shelf_life_months"]) == (
        model,
        governing,
        months,
    )
    assert result.poolability.model == exp["model"]
    assert result.governing_batch == exp["governing_batch"]
    assert result.proposed_shelf_life_months == exp["proposed_shelf_life_months"]
    assert result.crossing_months == pytest.approx(exp["crossing_months"], abs=5e-9)


@pytest.mark.parametrize("name", [n for n in FILES if n.startswith("dissolution")])
def test_dissolution_samples(name: str) -> None:
    """URS-GEN-004: decision basis, similarity verdict and f1/f2 as documented."""
    result, exp = run(name)
    assert isinstance(result, DissolutionResult)
    if name in STATED:
        assert exp["f2_similar"] is STATED[name]
    assert result.decision_basis == exp["decision_basis"]
    assert result.f2_similar is exp["f2_similar"]
    assert result.n_points_used == exp["n_points_used"]
    assert result.f1 == pytest.approx(exp["f1"], abs=0.005)
    assert result.f2 == pytest.approx(exp["f2"], abs=0.005)
    if exp["decision_basis"] == "bootstrap_f2":
        assert result.bootstrap is not None
        assert result.bootstrap.seed == MANIFEST["files"][name]["settings"]["bootstrap_seed"]
        assert result.bootstrap.lower == pytest.approx(exp["bootstrap_lower"], abs=0.005)


@pytest.mark.parametrize("name", [n for n in FILES if n.startswith("be")])
def test_be_samples(name: str) -> None:
    """URS-GEN-004: subjects per sequence, verdict and rounded 90% CIs as documented
    (the rounded CIs are R's own output from the generator, checked against the core)."""
    result, exp = run(name)
    assert isinstance(result, BeResult)
    assert exp["bioequivalent"] is STATED[name]
    assert result.bioequivalent is exp["bioequivalent"]
    for p in result.parameters:
        e = exp["parameters"][p.parameter]
        assert (p.n_tr, p.n_rt) == (e["n_tr"], e["n_rt"])
        assert (p.ci_lower_rounded, p.ci_upper_rounded) == (
            e["ci_lower_rounded"],
            e["ci_upper_rounded"],
        )
        assert p.within_limits is e["within_limits"]
