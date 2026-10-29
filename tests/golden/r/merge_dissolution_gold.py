"""Write R's expected values into tests/golden/data/GOLD-DISS-*.json (URS-DISS-002).

Run from the repository root: uv run python tests/golden/r/merge_dissolution_gold.py
It runs `Rscript tests/golden/r/dissolution_gold.R` and, for each case R prints:
- refuses unless the committed file round-trips byte-identically through
  json.dumps(indent=2, ensure_ascii=False) + "\n", with number arrays kept on one line, so
  only real changes show in git diff;
- refuses unless R's inputs equal the committed inputs;
- replaces "expected" wholesale with R's object (3 decimals, the committed precision). No
  expected value is typed by hand. R's full-precision values are printed for the record.
The curated text ("source", "tolerance", "requirement") is kept as committed.

After a run, review `git diff tests/golden/data` before committing. An empty diff means the
committed expected values are exactly R's output.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tests" / "golden" / "r" / "dissolution_gold.R"
DATA = ROOT / "tests" / "golden" / "data"
NUMBER_ARRAY = re.compile(r"\[\s*(-?[\d.]+(?:,\s*-?[\d.]+)*)\s*\]")


def dump(case: dict[str, Any]) -> str:
    text = json.dumps(case, indent=2, ensure_ascii=False)
    text = NUMBER_ARRAY.sub(lambda m: "[" + ", ".join(re.split(r",\s*", m[1])) + "]", text)
    return text + "\n"


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
    if r["inputs"] != case["inputs"]:
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
        status = "expected updated from R" if changed else "unchanged"
        print(f"{case_id}: {status} ({r['r_version']}; full precision {r['full_precision']})")


if __name__ == "__main__":
    main()
