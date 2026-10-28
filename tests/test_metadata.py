"""Traceability stamp: source file hashes in result metadata. Each test cites its requirement."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from cmc_stats.core import be, dissolution, stability
from cmc_stats.models import (
    BeInput,
    DissolutionInput,
    DissolutionProfile,
    SourceFile,
    StabilityInput,
    make_metadata,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
GOLDEN = Path(__file__).parent / "golden" / "data"
RAW = b"batch,time_months,value\nB001,0,99.9\n"
SOURCE = SourceFile(
    name="stability.csv", size_bytes=len(RAW), sha256=hashlib.sha256(RAW).hexdigest()
)


def golden_inputs(case: str) -> dict[str, object]:
    inputs: dict[str, object] = json.loads((GOLDEN / f"{case}.json").read_text("utf-8"))["inputs"]
    return inputs


def dissolution_input() -> DissolutionInput:
    times = [5.0, 10.0, 15.0, 20.0, 30.0, 45.0]
    means = {"Reference": [20, 40, 60, 75, 88, 95], "Test": [18, 37, 56, 72, 86, 94]}
    factors = [2 * i / 11 - 1 for i in range(12)]
    profiles = {
        label: DissolutionProfile(
            label=label,
            times_min=times,
            units=[[m * (1 + 0.02 * f) for m in vals] for f in factors],
        )
        for label, vals in means.items()
    }
    return DissolutionInput(reference=profiles["Reference"], test=profiles["Test"])


def test_metadata_records_source_files() -> None:
    """URS-GEN-003: name, size and SHA-256 of the raw bytes are recorded."""
    meta = make_metadata({"x": 1}, "stability", FIXED_TIME, source_files=(SOURCE,))
    assert meta.source_files == (SOURCE,)
    assert meta.source_files[0].sha256 == hashlib.sha256(RAW).hexdigest()


def test_source_files_default_to_empty() -> None:
    """URS-GEN-003: with no uploaded file the field is empty."""
    assert make_metadata({"x": 1}, "stability", FIXED_TIME).source_files == ()


def test_input_hash_does_not_depend_on_source_files() -> None:
    """URS-GEN-002, URS-GEN-003: input_hash covers the parsed inputs only."""
    a = make_metadata({"x": 1}, "stability", FIXED_TIME)
    b = make_metadata({"x": 1}, "stability", FIXED_TIME, source_files=(SOURCE,))
    assert a.input_hash == b.input_hash


@pytest.mark.parametrize(
    "fields",
    [
        {"name": "", "size_bytes": 1, "sha256": "0" * 64},
        {"name": "a.csv", "size_bytes": -1, "sha256": "0" * 64},
        {"name": "a.csv", "size_bytes": 1, "sha256": "XYZ"},
        {"name": "a.csv", "size_bytes": 1, "sha256": "A" * 64},
    ],
)
def test_source_file_rejects_bad_fields(fields: dict[str, object]) -> None:
    """URS-GEN-003: empty name, negative size or a malformed digest are rejected."""
    with pytest.raises(ValidationError):
        SourceFile.model_validate(fields)


def test_every_orchestrator_stamps_source_files() -> None:
    """URS-GEN-003: dissolution, stability and BE results carry the source files given."""
    diss = dissolution.compare_profiles(
        dissolution_input(), timestamp=FIXED_TIME, source_files=(SOURCE,)
    )
    stab = stability.estimate_shelf_life(
        StabilityInput.model_validate(golden_inputs("GOLD-STAB-001")),
        timestamp=FIXED_TIME,
        source_files=(SOURCE,),
    )
    bio = be.assess_bioequivalence(
        BeInput.model_validate(golden_inputs("GOLD-BE-001")),
        timestamp=FIXED_TIME,
        source_files=(SOURCE,),
    )
    for result in (diss, stab, bio):
        assert result.metadata.source_files == (SOURCE,)


def test_source_files_change_no_calculated_value() -> None:
    """URS-GEN-003: stamping a source file changes only the metadata."""
    data = StabilityInput.model_validate(golden_inputs("GOLD-STAB-002"))
    plain = stability.estimate_shelf_life(data, timestamp=FIXED_TIME)
    stamped = stability.estimate_shelf_life(data, timestamp=FIXED_TIME, source_files=(SOURCE,))
    assert plain.model_dump(exclude={"metadata"}) == stamped.model_dump(exclude={"metadata"})
    assert plain.metadata.input_hash == stamped.metadata.input_hash
