"""Pydantic input and result models.

Inputs reject bad data loudly; nothing is dropped, sorted, clipped or imputed. Results carry the
inputs, every intermediate value a reviewer would check, and a traceability stamp. Values are
kept at full precision; rounding happens only in the UI and report.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from cmc_stats import __version__, criteria

DISCLAIMER = "Educational and decision-support use only. Not validated for GxP use."

DissolutionDecisionBasis = Literal["rapid_dissolution", "mean_f2", "bootstrap_f2"]
StabilityDirection = Literal["decrease", "increase", "either"]
StabilityModel = Literal["pooled", "common_slope", "separate"]
ShelfLifeLimitedBy = Literal["crossing", "extrapolation_cap", "bound_below_limit_at_start"]


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


# --- Stability inputs (ICH Q1E, 2003) ------------------------------------------------------


class StabilityBatch(_Frozen):
    """Long-term results for one batch (ICH Q1E; URS-STAB-010 to 015).

    ``times_months`` and ``values`` are paired by position and kept as entered: not sorted,
    averaged or deduplicated. Replicate results at one time point are allowed.
    """

    label: str = Field(min_length=1)
    times_months: tuple[float, ...]
    values: tuple[float, ...]

    @model_validator(mode="after")
    def _shape(self) -> Self:
        """URS-STAB-010 to 013, 018: paired lengths, no negative times or values, enough data.

        Values above 100% are valid results and are kept as entered.
        """
        n_times, n_values = len(self.times_months), len(self.values)
        if n_times != n_values:
            raise ValueError(
                f"{self.label}: {n_times} time points but {n_values} values; they must pair up"
            )
        negative = [t for t in self.times_months if t < 0]
        if negative:
            raise ValueError(f"{self.label}: negative time point(s) {negative}")
        negative_values = [v for v in self.values if v < 0]
        if negative_values:
            raise ValueError(f"{self.label}: negative value(s) {negative_values}")
        if n_times < criteria.STABILITY_MIN_POINTS_PER_BATCH:
            raise ValueError(
                f"{self.label}: {n_times} observations; at least "
                f"{criteria.STABILITY_MIN_POINTS_PER_BATCH} required (project policy)"
            )
        distinct = len(set(self.times_months))
        if distinct < criteria.STABILITY_MIN_DISTINCT_TIMES:
            raise ValueError(
                f"{self.label}: {distinct} distinct time point(s); at least "
                f"{criteria.STABILITY_MIN_DISTINCT_TIMES} required to estimate a slope"
            )
        return self


class StabilityInput(_Frozen):
    """Shelf-life input: batches, acceptance limit and Appendix A conditions (ICH Q1E).

    v1 supports only an attribute expected to decrease (for example assay) with a lower
    limit, and only the ICH Q1E Appendix A branch "no significant change at accelerated,
    statistical analysis performed". Both Appendix A conditions must be stated; there are no
    defaults.
    """

    attribute: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    direction: StabilityDirection
    lower_limit: float = Field(ge=0)
    batches: tuple[StabilityBatch, ...]
    significant_change_at_accelerated: StrictBool
    statistical_analysis_performed: StrictBool

    @field_validator("direction")
    @classmethod
    def _decrease_only(cls, direction: StabilityDirection) -> StabilityDirection:
        """URS-STAB-006: v1 handles a decreasing attribute with a lower limit only."""
        if direction != "decrease":
            raise ValueError(
                f"direction '{direction}' is not supported in v1: only an attribute expected "
                "to decrease, with a one-sided lower bound against a lower limit"
            )
        return direction

    @model_validator(mode="after")
    def _batches_and_branch(self) -> Self:
        """URS-STAB-009 (>= 2 batches), URS-STAB-015 (unique labels), URS-STAB-007 (branch)."""
        n = len(self.batches)
        if n < criteria.STABILITY_MIN_BATCHES:
            raise ValueError(
                f"at least {criteria.STABILITY_MIN_BATCHES} batches required for the "
                f"poolability tests; got {n} (project policy)"
            )
        labels = [b.label for b in self.batches]
        duplicates = sorted({x for x in labels if labels.count(x) > 1})
        if duplicates:
            raise ValueError(f"duplicate batch label(s): {duplicates}")
        if self.significant_change_at_accelerated or not self.statistical_analysis_performed:
            raise ValueError(
                "ICH Q1E Appendix A: only the branch with no significant change at accelerated "
                "and statistical analysis performed is implemented; got "
                f"significant_change_at_accelerated={self.significant_change_at_accelerated}, "
                f"statistical_analysis_performed={self.statistical_analysis_performed}"
            )
        return self


# --- Stability results ---------------------------------------------------------------------


class BatchFit(_Frozen):
    """Least-squares line for one batch on its own data (URS-STAB-001)."""

    label: str
    intercept: float
    slope: float
    intercept_se: float
    slope_se: float
    residual_df: int
    mse: float


class PoolabilityTest(_Frozen):
    """One ANCOVA F test (URS-STAB-002)."""

    f_value: float
    df_num: int
    df_den: int
    p_value: float


class PoolabilityResult(_Frozen):
    """Slope then intercept equality tests and the model chosen (URS-STAB-002, 005).

    ``intercepts`` is ``None`` when slopes differ, because the intercept test is not run.
    """

    alpha: float
    slopes: PoolabilityTest
    intercepts: PoolabilityTest | None
    model: StabilityModel


class BatchShelfLife(_Frozen):
    """Bound and crossing for one line of the chosen model (URS-STAB-003, 005).

    ``label`` is ``None`` for the single pooled line. ``crossing_months`` is ``None`` when the
    bound never meets the limit.
    """

    label: str | None
    intercept: float
    slope: float
    df: int
    t_value: float
    bound_at_0: float
    crossing_months: float | None


class ExtrapolationCap(_Frozen):
    """ICH Q1E Appendix A cap, statistical analysis performed (URS-STAB-004, 008)."""

    x_months: float
    factor: float
    max_extra_months: int
    cap_months: float


class StabilityResult(_Frozen):
    """Full shelf-life result (URS-STAB-001 to 017, URS-GEN-001, URS-GEN-002).

    Crossing times are at full precision; only ``proposed_shelf_life_months`` is rounded
    (down to whole months, as the rule requires).
    """

    inputs: StabilityInput
    metadata: ResultMetadata
    batch_fits: tuple[BatchFit, ...]
    poolability: PoolabilityResult
    per_batch: tuple[BatchShelfLife, ...]
    governing_batch: str | None
    crossing_months: float | None
    extrapolation: ExtrapolationCap
    proposed_shelf_life_months: int
    limited_by: ShelfLifeLimitedBy
    conclusion: str
    notes: tuple[str, ...]
    warnings: tuple[str, ...]
