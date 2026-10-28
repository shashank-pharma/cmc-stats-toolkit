"""Pure helpers for the Streamlit UI: CSV templates and parsing, settings, notes, tables, charts.

No Streamlit import, so everything here is unit-tested directly. CSV parsing uses the stdlib
``csv`` module, not pandas, so nothing is coerced silently: blank cells, unknown columns and
anything that is not a plain decimal number are rejected with the row and column. Rows are kept
in file order and grouped in order of first appearance; nothing is sorted, dropped or averaged.
Tables keep full precision; rounding is left to display formatting.
"""

import csv
import hashlib
import io
import math
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Any, Literal

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from cmc_stats import criteria
from cmc_stats.core.be import assess_bioequivalence
from cmc_stats.core.dissolution import compare_profiles
from cmc_stats.core.stability import estimate_shelf_life, lower_bound
from cmc_stats.models import (
    BeInput,
    BeRecord,
    BeResult,
    BootstrapSettings,
    DissolutionInput,
    DissolutionProfile,
    DissolutionResult,
    SourceFile,
    StabilityBatch,
    StabilityInput,
    StabilityResult,
)

Area = Literal["dissolution", "stability", "be"]
AnyResult = DissolutionResult | StabilityResult | BeResult

TEMPLATE_WARNING = "Result from template dummy data, not your data"
_PROMINENT = re.compile(r"pending confirmation|provisional", re.IGNORECASE)
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_INTEGER = re.compile(r"[+-]?\d+")

# Required and optional columns per area (URS-UI-002)
COLUMNS: dict[Area, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "dissolution": (("product", "unit", "time_min", "percent_dissolved"), ()),
    "stability": (("batch", "time_months", "value"), ()),
    "be": (("subject", "sequence", "period", "treatment", "cmax", "auc0t"), ("auc0inf",)),
}
# Settings that must be chosen explicitly before Run (URS-UI-008)
REQUIRED_SETTINGS: dict[Area, tuple[str, ...]] = {
    "dissolution": ("file",),
    "stability": (
        "file",
        "attribute",
        "unit",
        "direction",
        "lower_limit",
        "significant_change_at_accelerated",
        "statistical_analysis_performed",
    ),
    "be": ("file", "design", "limits"),
}


class CsvError(ValueError):
    """Every problem found in an uploaded CSV, reported together (URS-UI-002 to 006)."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__("CSV rejected:\n" + "\n".join(f"- {e}" for e in self.errors))


# --- Source files and templates (URS-GEN-003, URS-UI-001, URS-UI-014) ----------------------


def source_file(name: str, raw: bytes) -> SourceFile:
    """Name, size and SHA-256 of the raw bytes exactly as uploaded (URS-GEN-003; ALCOA+)."""
    return SourceFile(name=name, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def _csv(header: Sequence[str], rows: Sequence[Sequence[object]]) -> bytes:
    lines = [",".join(header)] + [",".join(str(v) for v in row) for row in rows]
    return ("\n".join(lines) + "\n").encode("utf-8")


def template_csv(area: Area) -> bytes:
    """Downloadable CSV template with dummy data that parses into a valid input (URS-UI-001).

    Dummy data only: dissolution profiles generated from fixed means, the stability batches
    of GOLD-STAB-001 and the hand-written BE crossover used in the unit tests.
    """
    if area == "dissolution":
        diss_times = (5, 10, 15, 20, 30, 45)
        means = {"Reference": (20, 40, 60, 75, 88, 95), "Test": (18, 37, 56, 72, 86, 94)}
        factors = [2 * i / 11 - 1 for i in range(12)]
        diss_rows = [
            (product, unit + 1, t, f"{m * (1 + 0.02 * f):.2f}")
            for product, profile in means.items()
            for unit, f in enumerate(factors)
            for t, m in zip(diss_times, profile, strict=True)
        ]
        return _csv(COLUMNS["dissolution"][0], diss_rows)
    if area == "stability":
        stab_times = (0, 3, 6, 9, 12, 18, 24)
        batches = {
            "B001": (99.9, 99.7, 99.5, 98.6, 98.6, 97.6, 96.6),
            "B002": (100.5, 99.8, 99.0, 98.9, 98.5, 97.5, 96.9),
            "B003": (100.1, 99.8, 99.5, 98.7, 98.5, 97.5, 96.8),
        }
        stab_rows = [
            (label, t, v)
            for label, vals in batches.items()
            for t, v in zip(stab_times, vals, strict=True)
        ]
        return _csv(COLUMNS["stability"][0], stab_rows)
    if area == "be":
        subjects = (
            ("S01", "TR", 102.3, 98.7, 1510.2, 1480.6, 1602.4, 1571.0),
            ("S02", "RT", 88.1, 93.4, 1322.8, 1390.1, 1405.5, 1468.3),
            ("S03", "TR", 120.5, 115.2, 1755.0, 1702.3, 1850.2, 1799.9),
            ("S04", "RT", 95.6, 99.8, 1440.7, 1425.2, 1530.1, 1518.8),
            ("S05", "TR", 110.2, 104.9, 1600.3, 1612.7, 1695.0, 1702.6),
            ("S06", "RT", 79.4, 85.0, 1210.5, 1250.9, 1290.4, 1333.7),
            ("S07", "TR", 99.9, 101.2, 1495.5, 1460.0, 1580.2, 1549.3),
            ("S08", "RT", 105.3, 100.1, 1550.8, 1530.4, 1645.6, 1622.0),
        )
        be_rows = []
        for subject, seq, c_t, c_r, a_t, a_r, i_t, i_r in subjects:
            for period in (1, 2):
                trt = "T" if (seq == "TR") == (period == 1) else "R"
                vals = (c_t, a_t, i_t) if trt == "T" else (c_r, a_r, i_r)
                be_rows.append((subject, seq, period, trt, *vals))
        return _csv(COLUMNS["be"][0] + COLUMNS["be"][1], be_rows)
    raise ValueError(f"unknown area {area!r}")


def template_source(area: Area) -> tuple[str, bytes]:
    """File name and bytes used when the template's dummy data replace an upload (URS-UI-014)."""
    return f"template_{area}.csv", template_csv(area)


# --- CSV parsing (URS-UI-002 to 007) -------------------------------------------------------


def _read_rows(raw: bytes, area: Area) -> list[tuple[int, dict[str, str]]]:
    """Decode, check the header and return (row number, cells) in file order (header = row 1)."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvError([f"file is not UTF-8 text (invalid byte at position {exc.start})"]) from exc
    if not text.strip():
        raise CsvError(["file is empty"])
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header = rows[0]
    required, optional = COLUMNS[area]
    errors = []
    duplicates = sorted({c for c in header if header.count(c) > 1})
    if duplicates:
        errors.append("duplicate column(s): " + ", ".join(repr(c) for c in duplicates))
    missing = [c for c in required if c not in header]
    if missing:
        errors.append("missing column(s): " + ", ".join(repr(c) for c in missing))
    unknown = [c for c in header if c not in required + optional]
    if unknown:
        errors.append("unknown column(s): " + ", ".join(repr(c) for c in unknown))
    if errors:
        raise CsvError(errors)
    if len(rows) == 1:
        raise CsvError(["no data rows below the header"])
    out = []
    for n, row in enumerate(rows[1:], start=2):
        if len(row) != len(header):
            errors.append(f"row {n}: {len(row)} fields, header has {len(header)}")
        else:
            out.append((n, dict(zip(header, row, strict=True))))
    if errors:
        raise CsvError(errors)
    return out


def _text(row: dict[str, str], n: int, col: str, errors: list[str]) -> str | None:
    value = row[col]
    if not value.strip():
        errors.append(f"row {n}, column '{col}': blank cell")
        return None
    return value


def _number(row: dict[str, str], n: int, col: str, errors: list[str]) -> float | None:
    value = _text(row, n, col, errors)
    if value is None:
        return None
    if not _NUMBER.fullmatch(value):
        errors.append(f"row {n}, column '{col}': {value!r} is not a number")
        return None
    number = float(value)
    if not math.isfinite(number):
        errors.append(f"row {n}, column '{col}': {value!r} is not a finite number")
        return None
    return number


def _integer(row: dict[str, str], n: int, col: str, errors: list[str]) -> int | None:
    value = _text(row, n, col, errors)
    if value is None:
        return None
    if not _INTEGER.fullmatch(value):
        errors.append(f"row {n}, column '{col}': {value!r} is not a whole number")
        return None
    return int(value)


def parse_stability_csv(raw: bytes) -> tuple[StabilityBatch, ...]:
    """Columns batch, time_months, value; one row per result (URS-UI-002 to 005, 007).

    Batches are grouped in order of first appearance and keep their rows in file order.
    Model rules (for example at least 3 results per batch) still apply.

    Raises:
        CsvError: every structural or cell problem, listed together.
        pydantic.ValidationError: the parsed batches break a model rule.
    """
    errors: list[str] = []
    groups: dict[str, tuple[list[float], list[float]]] = {}
    for n, row in _read_rows(raw, "stability"):
        label = _text(row, n, "batch", errors)
        time = _number(row, n, "time_months", errors)
        value = _number(row, n, "value", errors)
        if label is None or time is None or value is None:
            continue
        times, values = groups.setdefault(label, ([], []))
        times.append(time)
        values.append(value)
    if errors:
        raise CsvError(errors)
    return tuple(
        StabilityBatch(label=label, times_months=tuple(ts), values=tuple(vs))
        for label, (ts, vs) in groups.items()
    )


def parse_be_csv(raw: bytes) -> tuple[BeRecord, ...]:
    """Columns subject, sequence, period, treatment, cmax, auc0t and optional auc0inf; one row
    per subject-period, returned in file order (URS-UI-002 to 005, 007).

    Raises:
        CsvError: every structural or cell problem, listed together.
        pydantic.ValidationError: a record breaks a model rule.
    """
    errors: list[str] = []
    records: list[dict[str, object]] = []
    for n, row in _read_rows(raw, "be"):
        rec: dict[str, object | None] = {
            "subject": _text(row, n, "subject", errors),
            "sequence": _text(row, n, "sequence", errors),
            "period": _integer(row, n, "period", errors),
            "treatment": _text(row, n, "treatment", errors),
            "cmax": _number(row, n, "cmax", errors),
            "auc0t": _number(row, n, "auc0t", errors),
        }
        if "auc0inf" in row:
            rec["auc0inf"] = _number(row, n, "auc0inf", errors)
        if all(v is not None for v in rec.values()):
            records.append({k: v for k, v in rec.items()})
    if errors:
        raise CsvError(errors)
    return tuple(BeRecord.model_validate(r) for r in records)


def parse_dissolution_csv(raw: bytes) -> DissolutionInput:
    """Columns product (Reference or Test), unit, time_min, percent_dissolved; one row per
    unit and time point (URS-UI-002 to 007).

    Values are placed by unit and time. Units and time points keep their order of first
    appearance per product; every unit must have every time point exactly once.

    Raises:
        CsvError: every structural, cell or layout problem, listed together.
        pydantic.ValidationError: the profiles break a model rule (for example fewer than 12
            units, or time points that differ between products).
    """
    errors: list[str] = []
    units: dict[str, list[str]] = {"Reference": [], "Test": []}
    times: dict[str, list[float]] = {"Reference": [], "Test": []}
    cells: dict[tuple[str, str, float], list[tuple[int, float]]] = {}
    for n, row in _read_rows(raw, "dissolution"):
        product = _text(row, n, "product", errors)
        if product is not None and product not in units:
            errors.append(f"row {n}, column 'product': {product!r} must be 'Reference' or 'Test'")
            product = None
        unit = _text(row, n, "unit", errors)
        time = _number(row, n, "time_min", errors)
        value = _number(row, n, "percent_dissolved", errors)
        if product is None or unit is None or time is None or value is None:
            continue
        if unit not in units[product]:
            units[product].append(unit)
        if time not in times[product]:
            times[product].append(time)
        cells.setdefault((product, unit, time), []).append((n, value))
    if errors:
        raise CsvError(errors)

    for product in units:
        if not units[product]:
            errors.append(f"no rows for product {product!r}")
            continue
        for unit in units[product]:
            for time in times[product]:
                entries = cells.get((product, unit, time), [])
                if not entries:
                    errors.append(f"{product}, unit {unit}: no value at {time} min")
                elif len(entries) > 1:
                    rows = ", ".join(str(r) for r, _ in entries)
                    errors.append(
                        f"{product}, unit {unit}, {time} min: {len(entries)} values (rows {rows})"
                    )
    if errors:
        raise CsvError(errors)

    profiles = {
        product: DissolutionProfile(
            label=product,
            times_min=tuple(times[product]),
            units=tuple(
                tuple(cells[(product, unit, t)][0][1] for t in times[product])
                for unit in units[product]
            ),
        )
        for product in units
    }
    return DissolutionInput(reference=profiles["Reference"], test=profiles["Test"])


# --- Settings and running (URS-UI-008, URS-UI-009, URS-GEN-003) ---------------------------


def _unset(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def missing_settings(area: Area, settings: Mapping[str, object]) -> list[str]:
    """Names of the required file and settings not yet chosen; nothing is defaulted
    (URS-UI-008). Dissolution bootstrap seed and resample count go together or not at all."""
    missing = [k for k in REQUIRED_SETTINGS[area] if _unset(settings.get(k))]
    if area == "dissolution":
        seed, n = settings.get("bootstrap_seed"), settings.get("bootstrap_n_resamples")
        if seed is None and n is not None:
            missing.append("bootstrap_seed")
        if n is None and seed is not None:
            missing.append("bootstrap_n_resamples")
    return missing


def run_analysis(
    area: Area,
    name: str,
    raw: bytes,
    settings: Mapping[str, Any],
    *,
    timestamp: datetime | None = None,
) -> AnyResult:
    """Parse an uploaded file, build the input with the chosen settings and run the core
    calculation, recording the raw file's hash in the result (URS-GEN-003, URS-UI-009).

    Raises:
        ValueError: any parsing, model or core error, unchanged (CsvError and pydantic
            ValidationError are ValueErrors).
    """
    sources = (source_file(name, raw),)
    if area == "dissolution":
        seed, n = settings.get("bootstrap_seed"), settings.get("bootstrap_n_resamples")
        if (seed is None) != (n is None):
            raise ValueError("give both the bootstrap seed and the resample count, or neither")
        bootstrap = (
            None
            if seed is None
            else BootstrapSettings.model_validate({"seed": seed, "n_resamples": n})
        )
        return compare_profiles(
            parse_dissolution_csv(raw), bootstrap, timestamp=timestamp, source_files=sources
        )
    if area == "stability":
        fields = {k: settings.get(k) for k in REQUIRED_SETTINGS["stability"] if k != "file"}
        data = StabilityInput.model_validate({**fields, "batches": parse_stability_csv(raw)})
        return estimate_shelf_life(data, timestamp=timestamp, source_files=sources)
    data_be = BeInput.model_validate(
        {
            "design": settings.get("design"),
            "limits": settings.get("limits"),
            "records": parse_be_csv(raw),
        }
    )
    return assess_bioequivalence(data_be, timestamp=timestamp, source_files=sources)


# --- Notes and tables (URS-UI-011, URS-UI-012) ---------------------------------------------


def prominent_notes(result: AnyResult) -> list[str]:
    """Notes, warnings and method notes that are provisional or pending confirmation, in
    order and without repeats, for display in warning boxes (URS-UI-011)."""
    texts = list(result.notes)
    if isinstance(result, StabilityResult | BeResult):
        texts += list(result.warnings)
    if isinstance(result, DissolutionResult) and result.bootstrap is not None:
        texts.append(result.bootstrap.method_note)
    seen: list[str] = []
    for text in texts:
        if _PROMINENT.search(text) and text not in seen:
            seen.append(text)
    return seen


def _summary(items: Mapping[str, object]) -> pd.DataFrame:
    """Item/value table; values as full-precision text so mixed types display safely."""
    return pd.DataFrame({"item": list(items), "value": [str(v) for v in items.values()]})


def dissolution_tables(result: DissolutionResult) -> dict[str, pd.DataFrame]:
    """Mean profiles (with the points used), CV checks and a summary (URS-UI-012)."""
    used = set(result.truncation.included_indices) if result.truncation else set()
    tables = {
        "profile": pd.DataFrame(
            {
                "time_min": list(result.inputs.times_min),
                "mean_reference": list(result.mean_reference),
                "mean_test": list(result.mean_test),
                "used": [i in used for i in range(len(result.mean_reference))],
            }
        )
    }
    if result.cv_check is not None:
        tables["cv"] = pd.DataFrame([p.model_dump() for p in result.cv_check.points])
    items: dict[str, object] = {
        "rapid_dissolution": result.rapid_dissolution,
        "n_points_used": result.n_points_used,
        "f1": result.f1,
        "f1_within_limit": result.f1_within_limit,
        "f2": result.f2,
        "decision_basis": result.decision_basis,
        "f2_similar": result.f2_similar,
    }
    if result.bootstrap is not None:
        b = result.bootstrap
        items |= {
            "bootstrap_seed": b.seed,
            "bootstrap_n_resamples": b.n_resamples,
            "bootstrap_ci_level": b.ci_level,
            "bootstrap_lower": b.lower,
            "bootstrap_median": b.median,
            "bootstrap_upper": b.upper,
        }
    tables["summary"] = _summary(items)
    return tables


def stability_tables(result: StabilityResult) -> dict[str, pd.DataFrame]:
    """Poolability tests, per-batch fits, per-line bounds and a summary (URS-UI-012)."""
    pool = result.poolability
    tests = [{"test": "slopes", **pool.slopes.model_dump()}]
    if pool.intercepts is not None:
        tests.append({"test": "intercepts", **pool.intercepts.model_dump()})
    per_batch = [p.model_dump() for p in result.per_batch]
    for row in per_batch:
        row["label"] = row["label"] if row["label"] is not None else "All batches (pooled)"
    return {
        "poolability": pd.DataFrame(tests),
        "batch_fits": pd.DataFrame([f.model_dump() for f in result.batch_fits]),
        "per_batch": pd.DataFrame(per_batch),
        "summary": _summary(
            {
                "model": pool.model,
                "governing_batch": result.governing_batch,
                "crossing_months": result.crossing_months,
                "x_months": result.extrapolation.x_months,
                "cap_months": result.extrapolation.cap_months,
                "proposed_shelf_life_months": result.proposed_shelf_life_months,
                "limited_by": result.limited_by,
            }
        ),
    }


def be_tables(result: BeResult) -> dict[str, pd.DataFrame]:
    """One row per PK parameter, and the type I ANOVA tables (URS-UI-012)."""
    return {
        "parameters": pd.DataFrame(
            [p.model_dump(exclude={"anova", "notes"}) for p in result.parameters]
        ),
        "anova": pd.DataFrame(
            [
                {"parameter": p.parameter, **r.model_dump()}
                for p in result.parameters
                for r in p.anova
            ]
        ),
    }


TABLES: dict[Area, Callable[[Any], dict[str, pd.DataFrame]]] = {
    "dissolution": dissolution_tables,
    "stability": stability_tables,
    "be": be_tables,
}


# --- Charts: Plotly lines and bars only (URS-UI-013) ---------------------------------------


def dissolution_chart(result: DissolutionResult) -> go.Figure:
    """Mean dissolution profiles of reference and test as lines."""
    fig = go.Figure()
    times = list(result.inputs.times_min)
    for name, means in (("Reference", result.mean_reference), ("Test", result.mean_test)):
        fig.add_trace(go.Scatter(x=times, y=list(means), mode="lines+markers", name=name))
    fig.update_layout(xaxis_title="Time (min)", yaxis_title="Mean % dissolved")
    return fig


def stability_chart(result: StabilityResult, points: int = 200) -> go.Figure:
    """Batch data, fitted mean line(s), one-sided 95% lower bound(s) and the lower limit, as
    lines from time 0 to the Appendix A cap. Bounds come from ``core.stability.lower_bound``."""
    data = result.inputs
    model = result.poolability.model
    cap = result.extrapolation.cap_months
    grid = np.linspace(0.0, cap, points)
    fig = go.Figure()
    for batch in data.batches:
        fig.add_trace(
            go.Scatter(
                x=list(batch.times_months),
                y=list(batch.values),
                mode="lines+markers",
                name=f"{batch.label} data",
            )
        )
    for line in result.per_batch:
        name = line.label if line.label is not None else "Pooled"
        fig.add_trace(
            go.Scatter(
                x=grid, y=line.intercept + line.slope * grid, mode="lines", name=f"{name} mean"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=grid,
                y=lower_bound(data, model, line.label, grid),
                mode="lines",
                line={"dash": "dash"},
                name=f"{name} 95% lower bound",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[0.0, cap],
            y=[data.lower_limit, data.lower_limit],
            mode="lines",
            line={"dash": "dot"},
            name="Lower limit",
        )
    )
    fig.update_layout(xaxis_title="Time (months)", yaxis_title=f"{data.attribute} ({data.unit})")
    return fig


def be_chart(result: BeResult) -> go.Figure:
    """Point estimate bars with asymmetric 90% CI error bars and 80/125% reference lines."""
    params = result.parameters
    names = [p.parameter for p in params]
    fig = go.Figure(
        go.Bar(
            x=names,
            y=[p.pe_pct for p in params],
            error_y={
                "type": "data",
                "symmetric": False,
                "array": [p.ci_upper_pct - p.pe_pct for p in params],
                "arrayminus": [p.pe_pct - p.ci_lower_pct for p in params],
            },
            name="Point estimate (90% CI)",
        )
    )
    for limit in (criteria.BE_LOWER_PCT, criteria.BE_UPPER_PCT):
        fig.add_trace(
            go.Scatter(
                x=names,
                y=[limit] * len(names),
                mode="lines",
                line={"dash": "dot"},
                name=f"{limit:.2f}% limit",
            )
        )
    fig.update_layout(yaxis_title="T/R geometric mean ratio (%)")
    return fig


CHARTS: dict[Area, Callable[[Any], go.Figure]] = {
    "dissolution": dissolution_chart,
    "stability": stability_chart,
    "be": be_chart,
}
