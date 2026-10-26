"""Pydantic input and result models.

Inputs reject bad data loudly; nothing is dropped, sorted, clipped or imputed. Results carry the
inputs, every intermediate value a reviewer would check, and a traceability stamp. Values are
kept at full precision; rounding happens only in the UI and report.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cmc_stats import __version__, criteria

DISCLAIMER = "Educational and decision-support use only. Not validated for GxP use."

DissolutionDecisionBasis = Literal["rapid_dissolution", "mean_f2", "bootstrap_f2"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


# --- Shared --------------------------------------------------------------------------------


class ResultMetadata(_Frozen):
    """Traceability stamp on every result (URS-GEN-001, URS-GEN-002; ALCOA+)."""

    disclaimer: str = DISCLAIMER
    app_version: str
    guideline_version: str
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    timestamp: datetime


def make_metadata(
    inputs: dict[str, Any], area: str, timestamp: datetime | None = None
) -> ResultMetadata:
    """Build the traceability stamp for a result (URS-GEN-001, URS-GEN-002; ALCOA+).

    Args:
        inputs: JSON-serialisable inputs and settings; hashed with SHA-256 over canonical JSON
            (sorted keys, no whitespace), so equal inputs always give the same hash.
        area: key into ``criteria.GUIDELINE_VERSIONS``.
        timestamp: time of calculation; defaults to now in UTC. Pass one for reproducible tests.
    """
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return ResultMetadata(
        app_version=__version__,
        guideline_version=criteria.GUIDELINE_VERSIONS[area],
        input_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        timestamp=timestamp if timestamp is not None else datetime.now(UTC),
    )


# --- Dissolution inputs (FDA IR dissolution guidance, 1997) --------------------------------


class DissolutionProfile(_Frozen):
    """Unit-level dissolution data for one product (FDA IR dissolution guidance, 1997).

    ``units`` has one row per dosage unit and one column per time point, in % dissolved.
    Values over 100% are valid assay results and are kept as entered.
    """

    label: str = Field(min_length=1)
    times_min: tuple[float, ...]
    units: tuple[tuple[float, ...], ...]

    @field_validator("times_min")
    @classmethod
    def _times_positive_increasing(cls, times: tuple[float, ...]) -> tuple[float, ...]:
        """URS-DISS-009: at least one time point, all > 0 and strictly increasing."""
        if not times:
            raise ValueError("at least one time point is required")
        if times[0] <= 0:
            raise ValueError(f"time points must be > 0 minutes; got {times[0]}")
        for i in range(1, len(times)):
            if times[i] <= times[i - 1]:
                raise ValueError(
                    f"time points must be strictly increasing; index {i} ({times[i]}) "
                    f"follows {times[i - 1]}"
                )
        return times

    @field_validator("units")
    @classmethod
    def _values_non_negative(
        cls, units: tuple[tuple[float, ...], ...]
    ) -> tuple[tuple[float, ...], ...]:
        """URS-DISS-009: no negative % dissolved (non-finite values are refused by the config)."""
        for u, row in enumerate(units):
            for t, value in enumerate(row):
                if value < 0:
                    raise ValueError(f"unit {u}, time index {t}: negative value {value}")
        return units

    @model_validator(mode="after")
    def _shape(self) -> Self:
        """URS-DISS-004 (FDA 1997: at least 12 units) and URS-DISS-009 (no ragged rows)."""
        n_units = len(self.units)
        if n_units < criteria.DISSOLUTION_MIN_UNITS:
            raise ValueError(
                f"{self.label}: {n_units} units supplied; at least "
                f"{criteria.DISSOLUTION_MIN_UNITS} required (FDA IR dissolution guidance, 1997)"
            )
        n_times = len(self.times_min)
        for u, row in enumerate(self.units):
            if len(row) != n_times:
                raise ValueError(
                    f"{self.label}: unit {u} has {len(row)} values but there are "
                    f"{n_times} time points"
                )
        return self


class DissolutionInput(_Frozen):
    """Reference and test profiles for comparison (FDA IR dissolution guidance, 1997)."""

    reference: DissolutionProfile
    test: DissolutionProfile

    @model_validator(mode="after")
    def _same_time_points(self) -> Self:
        """URS-DISS-005 (FDA 1997: identical time points). Exact match, no tolerance."""
        ref, test = self.reference.times_min, self.test.times_min
        if len(ref) != len(test):
            raise ValueError(
                f"reference has {len(ref)} time points, test has {len(test)}; "
                "they must be identical (FDA IR dissolution guidance, 1997)"
            )
        mismatches = [
            f"index {i}: reference {r} vs test {t}"
            for i, (r, t) in enumerate(zip(ref, test, strict=True))
            if r != t
        ]
        if mismatches:
            raise ValueError(
                "reference and test time points differ (FDA IR dissolution guidance, 1997): "
                + "; ".join(mismatches)
            )
        return self

    @property
    def times_min(self) -> tuple[float, ...]:
        """The validated time points shared by both profiles."""
        return self.reference.times_min


class BootstrapSettings(_Frozen):
    """Bootstrap f2 settings (URS-DISS-007). Both fields are required; no seed is invented."""

    seed: int = Field(ge=0)
    n_resamples: int = Field(ge=criteria.BOOTSTRAP_MIN_RESAMPLES)


# --- Dissolution results -------------------------------------------------------------------


class TruncationResult(_Frozen):
    """Time points kept and excluded by the 85% rule (URS-DISS-001)."""

    included_indices: tuple[int, ...]
    excluded_indices: tuple[int, ...]
    cutoff_time_min: float | None
    reason: str


class CvPoint(_Frozen):
    """CV check at one time point (URS-DISS-003)."""

    time_min: float
    cv_reference_pct: float
    cv_test_pct: float
    limit_pct: float
    passed: bool


class CvCheck(_Frozen):
    """CV checks over the time points used (URS-DISS-003)."""

    points: tuple[CvPoint, ...]
    all_pass: bool


class BootstrapF2Result(_Frozen):
    """Percentile bootstrap f2 interval (URS-DISS-007)."""

    seed: int
    n_resamples: int
    ci_level: float
    time_points_used: tuple[float, ...]
    lower: float
    median: float
    upper: float
    similar: bool
    method_note: str


class DissolutionResult(_Frozen):
    """Full dissolution comparison result (URS-DISS-001 to 008, URS-GEN-001, URS-GEN-002)."""

    inputs: DissolutionInput
    bootstrap_settings: BootstrapSettings | None
    metadata: ResultMetadata
    mean_reference: tuple[float, ...]
    mean_test: tuple[float, ...]
    rapid_dissolution: bool
    truncation: TruncationResult | None
    cv_check: CvCheck | None
    n_points_used: int | None
    f1: float | None
    f1_within_limit: bool | None
    f2: float | None
    bootstrap: BootstrapF2Result | None
    decision_basis: DissolutionDecisionBasis
    f2_similar: bool | None
    conclusion: str
    notes: tuple[str, ...]
