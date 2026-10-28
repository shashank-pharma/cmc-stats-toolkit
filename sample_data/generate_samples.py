"""Regenerate the stability and dissolution sample files (dummy data only).

Run from the repository root: uv run python sample_data/generate_samples.py
The BE files come from sample_data/generate_be.R.

Formats match the UI templates exactly (cmc_stats.ui_helpers.template_csv). Dissolution unit
values are drawn once from numpy's default_rng(SEED) in a fixed order, so the files are
reproducible: value = mean * (1 + cv * z), z standard normal, rounded to 2 decimals.

NumPy does not promise identical default_rng streams across releases, so the numpy version
used is written to generated_with.json. The committed files were generated with numpy 2.5.4;
regenerating with another version may change the dissolution values (then rebuild
expected.json with build_expected.py and review every change).
"""

import json
import platform
from pathlib import Path

import numpy as np

SEED = 20261028
OUT = Path(__file__).parent

STAB_TIMES = (0, 3, 6, 9, 12, 18, 24)
B001 = (99.9, 99.7, 99.5, 98.6, 98.6, 97.6, 96.6)
B002 = (100.5, 99.8, 99.0, 98.9, 98.5, 97.5, 96.9)
B003 = {
    "similar": (100.1, 99.8, 99.5, 98.7, 98.5, 97.5, 96.8),
    "start": (99.4, 99.1, 98.8, 98.0, 97.8, 96.8, 96.1),
    "faster": (100.1, 99.6, 99.1, 98.2, 97.8, 96.4, 95.4),
}

DISS_TIMES = (5, 10, 15, 20, 30, 45)
REFERENCE = (28, 52, 70, 82, 91, 96)
TEST_SIMILAR = (24, 47, 66, 79, 89, 95)
TEST_SLOW = (15, 33, 50, 64, 80, 90)
UNITS = 12
CV_NORMAL = 0.04  # well inside the 20% (<= 15 min) and 10% (later) CV limits
CV_HIGH = 0.15  # above the 10% limit at later points, so bootstrap f2 is needed


def write(name: str, header: str, rows: list[tuple[object, ...]]) -> None:
    lines = [header] + [",".join(str(v) for v in row) for row in rows]
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def stability() -> None:
    for case, b003 in B003.items():
        rows = [
            (label, t, v)
            for label, vals in (("B001", B001), ("B002", B002), ("B003", b003))
            for t, v in zip(STAB_TIMES, vals, strict=True)
        ]
        write(f"stability_b003_{case}.csv", "batch,time_months,value", rows)


def units(rng: np.random.Generator, means: tuple[int, ...], cv: float) -> np.ndarray:
    z = rng.standard_normal((UNITS, len(means)))
    return np.round(np.asarray(means, dtype=float) * (1 + cv * z), 2)


def dissolution() -> None:
    rng = np.random.default_rng(SEED)
    # Draw order is fixed: changing it changes every value
    ref_normal = units(rng, REFERENCE, CV_NORMAL)
    test_similar = units(rng, TEST_SIMILAR, CV_NORMAL)
    test_slow = units(rng, TEST_SLOW, CV_NORMAL)
    ref_high = units(rng, REFERENCE, CV_HIGH)
    test_similar_high = units(rng, TEST_SIMILAR, CV_HIGH)
    files = {
        "dissolution_similar.csv": (ref_normal, test_similar),
        "dissolution_slow.csv": (ref_normal, test_slow),
        "dissolution_similar_high_cv.csv": (ref_high, test_similar_high),
    }
    for name, (ref, test) in files.items():
        rows = [
            (product, u + 1, t, f"{data[u, k]:.2f}")
            for product, data in (("Reference", ref), ("Test", test))
            for u in range(UNITS)
            for k, t in enumerate(DISS_TIMES)
        ]
        write(name, "product,unit,time_min,percent_dissolved", rows)


def provenance() -> None:
    """Record what generated the dissolution values (read by build_expected.py)."""
    record = {"numpy": np.__version__, "python": platform.python_version(), "seed": SEED}
    (OUT / "generated_with.json").write_text(json.dumps(record, indent=2) + "\n", "utf-8")


if __name__ == "__main__":
    stability()
    dissolution()
    provenance()
    print("wrote stability and dissolution samples to", OUT)
