"""Write R's expected values into tests/golden/data/GOLD-STAB-*.json (URS-STAB-001 to 005, 008).

Run from the repository root: uv run python tests/golden/r/merge_stability_gold.py
It runs `Rscript tests/golden/r/stability_gold.R` and, for each case R prints:
- refuses unless the committed file round-trips byte-identically through
  json.dumps(indent=2, ensure_ascii=False) + "\n", so only real changes show in git diff;
- refuses unless the R version is named in the file's "source" and R's lower limit and
  batches equal the committed inputs;
- replaces "expected" wholesale with R's object. No expected value is typed by hand.
The curated text ("source", "crosscheck", "tolerance", "requirement") is kept as committed;
when the method changes, edit that text in the JSON and say why in the CHANGELOG.

After a run, review `git diff tests/golden/data` before committing. An empty diff means the
committed expected values are exactly R's output.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tests" / "golden" / "r" / "stability_gold.R"
DATA = ROOT / "tests" / "golden" / "data"


def dump(case: dict[str, Any]) -> str:
    return json.dumps(case, indent=2, ensure_ascii=False) + "\n"


def r_cases() -> dict[str, dict[str, Any]]:
    """R's output for every case, keyed by case ID."""
    out = subprocess.run(
        ["Rscript", str(SCRIPT)], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    cases = [json.loads(line) for line in out.splitlines() if line.strip()]
    return {c["id"]: c for c in cases}


def merge(case_id: str, r: dict[str, Any]) -> bool:
    """Write R's expected values into the case file; True if the file changed."""
    path = DATA / f"{case_id}.json"
    text = path.read_text("utf-8")
    case = json.loads(text)
    if dump(case) != text:
        raise SystemExit(f"{case_id}: committed file does not round-trip; refusing to rewrite")
    if r["r_version"] not in case["source"]:
        raise SystemExit(f"{case_id}: {r['r_version']!r} is not named in the source field")
    inputs = case["inputs"]
    if (r["inputs"]["lower_limit"], r["inputs"]["batches"]) != (
        inputs["lower_limit"],
        inputs["batches"],
    ):
        raise SystemExit(f"{case_id}: R inputs differ from the committed inputs")
    case["expected"] = r["expected"]
    new = dump(case)
    if new == text:
        return False
    path.write_text(new, "utf-8")
    return True


def main() -> None:
    for case_id, r in sorted(r_cases().items()):
        changed = merge(case_id, r)
        print(f"{case_id}: {'expected updated from R' if changed else 'unchanged'}")


if __name__ == "__main__":
    main()
