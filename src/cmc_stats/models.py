"""Pydantic input and result models.

Inputs reject bad data loudly; nothing is dropped, sorted, clipped or imputed. Results carry the
inputs, every intermediate value a reviewer would check, and a traceability stamp. Values are
kept at full precision; rounding happens only in the UI and report.
"""

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from cmc_stats import __version__, criteria

DISCLAIMER = "Educational and decision-support use only. Not validated for GxP use."

DissolutionDecisionBasis = Literal["rapid_dissolution", "mean_f2", "bootstrap_f2"]
StabilityDirection = Literal["decrease", "increase", "either"]
StabilityStorageCondition = Literal["room_temperature", "refrigerated", "freezer"]
StabilityModel = Literal["pooled", "common_slope", "separate"]
ShelfLifeLimitedBy = Literal["crossing", "extrapolation_cap", "bound_below_limit_at_start"]
BeDesign = Literal["2x2_crossover", "replicate", "parallel"]
BeLimits = Literal["average", "reference_scaled"]
BeParameter = Literal["cmax", "auc0t", "auc0inf"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


# --- Shared --------------------------------------------------------------------------------


class SourceFile(_Frozen):
    """An uploaded file the inputs were parsed from (URS-GEN-003; ALCOA+).

    ``sha256`` is the digest of the raw bytes as uploaded, before any decoding or parsing.
    """

    name: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ResultMetadata(_Frozen):
    """Traceability stamp on every result (URS-GEN-001 to 003; ALCOA+).

    ``input_hash`` covers the parsed inputs and settings; ``source_files`` records the raw
    files they came from (empty when the inputs did not come from a file).
    """

    disclaimer: str = DISCLAIMER
    app_version: str
    guideline_version: str
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    timestamp: datetime
    source_files: tuple[SourceFile, ...] = ()


def make_metadata(
    inputs: dict[str, Any],
    area: str,
    timestamp: datetime | None = None,
    *,
    source_files: Sequence[SourceFile] = (),
) -> ResultMetadata:
    """Build the traceability stamp for a result (URS-GEN-001 to 003; ALCOA+).

    Args:
        inputs: JSON-serialisable inputs and settings; hashed with SHA-256 over canonical JSON
            (sorted keys, no whitespace), so equal inputs always give the same hash.
        area: key into ``criteria.GUIDELINE_VERSIONS``.
        timestamp: time of calculation; defaults to now in UTC. Pass one for reproducible tests.
        source_files: raw files the inputs were parsed from; not part of ``input_hash``.
    """
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return ResultMetadata(
        app_version=__version__,
        guideline_version=criteria.GUIDELINE_VERSIONS[area],
        input_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        timestamp=timestamp if timestamp is not None else datetime.now(UTC),
        source_files=tuple(source_files),
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

    @field_validator("label")
    @classmethod
    def _no_padding(cls, label: str) -> str:
        """URS-STAB-015: a label with leading or trailing spaces would make a second batch."""
        if label != label.strip():
            raise ValueError(f"batch label {label!r} has leading or trailing whitespace")
        return label

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
    limit, stored at room temperature, and only the ICH Q1E Appendix A branch "no significant
    change at accelerated, statistical analysis performed" (2.4.1.2, p. 4; Appendix A, p. 8).
    The storage condition and both Appendix A conditions must be stated; there are no
    defaults. Refrigerated and freezer storage and significant change at accelerated are
    refused as not supported in v1 (URS-STAB-022, URS-STAB-023).
    """

    attribute: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    direction: StabilityDirection
    storage_condition: StabilityStorageCondition
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

    @field_validator("storage_condition")
    @classmethod
    def _room_temperature_only(
        cls, condition: StabilityStorageCondition
    ) -> StabilityStorageCondition:
        """URS-STAB-022: ICH Q1E 2.4.1.2 and Appendix A cap for room temperature only; the
        refrigerated branch (2.5.1.1) and freezer storage are refused."""
        if condition != "room_temperature":
            raise ValueError(
                f"storage condition '{condition}' is not supported in v1: only room "
                "temperature (ICH Q1E 2.4.1.2 and Appendix A: Y up to 2X, but not exceeding "
                "X + 12 months) is implemented"
            )
        return condition

    @field_validator("significant_change_at_accelerated")
    @classmethod
    def _no_significant_change_only(cls, significant_change: bool) -> bool:
        """URS-STAB-023: ICH Q1E Appendix A branches after significant change at accelerated
        are refused."""
        if significant_change:
            raise ValueError(
                "significant change at accelerated condition is not supported in v1: only the "
                "ICH Q1E Appendix A branch with no significant change at accelerated is "
                "implemented"
            )
        return significant_change

    @model_validator(mode="after")
    def _batches_and_branch(self) -> Self:
        """URS-STAB-009 (>= 2 batches), URS-STAB-015 (unique labels), URS-STAB-007 (analysis
        performed)."""
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
        by_case: dict[str, set[str]] = {}
        for label in labels:
            by_case.setdefault(label.casefold(), set()).add(label)
        clashes = [sorted(group) for group in by_case.values() if len(group) > 1]
        if clashes:
            raise ValueError(
                "batch labels differ only by letter case: "
                + "; ".join(", ".join(repr(x) for x in group) for group in clashes)
            )
        if not self.statistical_analysis_performed:
            raise ValueError(
                "ICH Q1E Appendix A: only the branch with no significant change at accelerated "
                "and statistical analysis performed is implemented; got "
                "statistical_analysis_performed=False"
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


# --- Bioequivalence inputs (ICH M13A, 2024; FDA BE statistics guidance) --------------------


class BeRecord(_Frozen):
    """One subject-period result of a 2x2 crossover (URS-BE-007, URS-BE-015).

    Values are kept as entered. ``auc0inf`` is optional (URS-BE-014) but, when used, must be
    present on every record (checked by ``BeInput``).
    """

    subject: str = Field(min_length=1)
    sequence: str
    period: StrictInt
    treatment: Literal["T", "R"]
    cmax: float
    auc0t: float
    auc0inf: float | None = None

    @field_validator("subject")
    @classmethod
    def _no_padding(cls, subject: str) -> str:
        """URS-BE-015: an ID with leading or trailing spaces would make a second subject."""
        if subject != subject.strip():
            raise ValueError(f"subject ID {subject!r} has leading or trailing whitespace")
        return subject

    @model_validator(mode="after")
    def _positive(self) -> Self:
        """URS-BE-007: PK values > 0 (log transform); URS-BE-018: AUC0-inf >= AUC0-t."""
        for name in ("cmax", "auc0t", "auc0inf"):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(
                    f"subject {self.subject}, period {self.period}: {name} must be > 0 for "
                    f"the log transform; got {value}"
                )
        if self.auc0inf is not None and self.auc0inf < self.auc0t:
            raise ValueError(
                f"subject {self.subject}, period {self.period}: auc0inf ({self.auc0inf}) is "
                f"smaller than auc0t ({self.auc0t}); AUC0-inf cannot be below AUC0-t"
            )
        return self


class BeInput(_Frozen):
    """2x2 crossover bioequivalence input (ICH M13A; URS-BE-004 to 015).

    v1 supports only the 2x2 crossover (sequences TR and RT) with average-BE limits. The design
    and limits must be stated; there are no defaults. Records may be in any order.
    """

    design: BeDesign
    limits: BeLimits
    records: tuple[BeRecord, ...]

    @field_validator("design")
    @classmethod
    def _crossover_only(cls, design: BeDesign) -> BeDesign:
        """URS-BE-004, URS-BE-006: replicate and parallel designs are refused."""
        if design != "2x2_crossover":
            raise ValueError(
                f"{design} designs are not supported in v1: only the 2x2 crossover "
                "(sequences TR and RT) is implemented"
            )
        return design

    @field_validator("limits")
    @classmethod
    def _average_only(cls, limits: BeLimits) -> BeLimits:
        """URS-BE-005: reference-scaled limits are refused."""
        if limits != "average":
            raise ValueError(
                "reference-scaled limits are not supported in v1: only average bioequivalence "
                f"({criteria.BE_LOWER_PCT:.2f}-{criteria.BE_UPPER_PCT:.2f}%) is implemented"
            )
        return limits

    @model_validator(mode="after")
    def _complete_crossover(self) -> Self:
        """URS-BE-004, 008 to 014: a complete, consistent 2x2 crossover. Order matters: a
        replicate layout is reported as such before it can look like a missing period."""
        recs = self.records
        for r in recs:  # URS-BE-004 (detected), URS-BE-010 (sequence label)
            if len(r.sequence) > 2:
                raise ValueError(
                    f"subject {r.subject}: sequence '{r.sequence}' implies a replicate design; "
                    "replicate designs are not supported in v1"
                )
            if r.period not in (1, 2):
                raise ValueError(
                    f"subject {r.subject}: period {r.period} implies a replicate design; "
                    "replicate designs are not supported in v1"
                )
            if r.sequence not in ("TR", "RT"):
                raise ValueError(
                    f"subject {r.subject}: sequence '{r.sequence}' must be 'TR' or 'RT'"
                )

        keys = [(r.subject, r.period) for r in recs]  # URS-BE-009
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        if duplicates:
            raise ValueError(
                "duplicate subject-period record(s): "
                + ", ".join(f"{s} period {p}" for s, p in duplicates)
            )
        by_case: dict[str, set[str]] = {}  # URS-BE-015: IDs differing only by letter case
        for r in recs:
            by_case.setdefault(r.subject.casefold(), set()).add(r.subject)
        clashes = [sorted(ids) for ids in by_case.values() if len(ids) > 1]
        if clashes:
            raise ValueError(
                "subject IDs differ only by letter case: "
                + "; ".join(", ".join(repr(i) for i in ids) for ids in clashes)
            )

        sequences: dict[str, set[str]] = {}
        periods: dict[str, set[int]] = {}
        for r in recs:
            sequences.setdefault(r.subject, set()).add(r.sequence)
            periods.setdefault(r.subject, set()).add(r.period)
        for subject, seqs in sequences.items():  # URS-BE-011
            if len(seqs) > 1:
                raise ValueError(f"subject {subject} is listed under both sequences")
        for r in recs:  # URS-BE-010 (treatment matches sequence)
            expected = "T" if (r.sequence == "TR") == (r.period == 1) else "R"
            if r.treatment != expected:
                raise ValueError(
                    f"subject {r.subject} (sequence {r.sequence}): period {r.period} must be "
                    f"treatment {expected}; got {r.treatment}"
                )
        for subject, got in periods.items():  # URS-BE-008
            missing = sorted({1, 2} - got)
            if missing:
                raise ValueError(f"subject {subject}: missing period {missing[0]}")

        for seq in ("TR", "RT"):  # URS-BE-012
            n_seq = sum(1 for s in sequences.values() if seq in s)
            if n_seq < criteria.BE_MIN_SUBJECTS_PER_SEQUENCE:
                raise ValueError(
                    f"sequence {seq}: {n_seq} subjects; at least "
                    f"{criteria.BE_MIN_SUBJECTS_PER_SEQUENCE} subject per sequence required "
                    "(project policy)"
                )
        n = len(sequences)  # URS-BE-013: complete 2x2 has 2n results and n + 2 parameters
        df = n - 2
        if df < criteria.BE_MIN_RESIDUAL_DF:
            raise ValueError(
                f"{n} subjects give residual degrees of freedom {df}; at least "
                f"{criteria.BE_MIN_RESIDUAL_DF} required, so at least "
                f"{criteria.BE_MIN_RESIDUAL_DF + 2} subjects are needed (project policy)"
            )

        with_inf = [r.auc0inf is not None for r in recs]  # URS-BE-014
        if any(with_inf) and not all(with_inf):
            gaps = [f"{r.subject} period {r.period}" for r in recs if r.auc0inf is None]
            raise ValueError(
                "auc0inf supplied for some records but missing for: "
                + ", ".join(gaps)
                + "; supply it for every record or none"
            )
        return self


# --- Bioequivalence results ----------------------------------------------------------------


class AnovaRow(_Frozen):
    """One row of the sequential (type I) ANOVA table on the log scale (URS-BE-002, 017)."""

    term: str
    df: int
    ss: float
    ms: float


class BeParameterResult(_Frozen):
    """Analysis of one PK parameter (URS-BE-001 to 003, 012, 016, 017).

    CI limits are kept at full precision; ``ci_*_rounded`` are the values used for the
    decision (URS-BE-016).
    """

    parameter: BeParameter
    decision_making: bool
    n_tr: int
    n_rt: int
    df: int
    mse: float
    diff_log: float
    se_log: float
    t_value: float
    pe_pct: float
    ci_lower_pct: float
    ci_upper_pct: float
    ci_lower_rounded: float
    ci_upper_rounded: float
    within_limits: bool
    tost_p_lower: float
    tost_p_upper: float
    cv_within_pct: float
    anova: tuple[AnovaRow, ...]
    notes: tuple[str, ...]


class BeResult(_Frozen):
    """Full 2x2 crossover BE result (URS-BE-001 to 017, URS-GEN-001, URS-GEN-002)."""

    inputs: BeInput
    metadata: ResultMetadata
    parameters: tuple[BeParameterResult, ...]
    decision_parameters: tuple[BeParameter, ...]
    bioequivalent: bool
    conclusion: str
    notes: tuple[str, ...]
    warnings: tuple[str, ...]
