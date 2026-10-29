"""Pure UI helpers: CSV templates and parsing, settings, notes, tables and charts.
Each test cites the requirement it proves."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from cmc_stats import ui_helpers as ui
from cmc_stats.core import be, dissolution, stability
from cmc_stats.models import (
    BeInput,
    BootstrapSettings,
    DissolutionInput,
    DissolutionProfile,
    StabilityInput,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)
GOLDEN = Path(__file__).parent / "golden" / "data"
STAB_SETTINGS: dict[str, Any] = {
    "attribute": "Assay",
    "unit": "% label claim",
    "direction": "decrease",
    "lower_limit": 95.0,
    "significant_change_at_accelerated": False,
    "statistical_analysis_performed": True,
}
BE_SETTINGS: dict[str, Any] = {"design": "2x2_crossover", "limits": "average"}


def csv_bytes(*lines: str) -> bytes:
    return ("\n".join(lines) + "\n").encode("utf-8")


def stab_golden(case: str) -> StabilityInput:
    inputs = json.loads((GOLDEN / f"{case}.json").read_text("utf-8"))["inputs"]
    return StabilityInput.model_validate(inputs)


def be_golden(case: str) -> BeInput:
    return BeInput.model_validate(
        json.loads((GOLDEN / f"{case}.json").read_text("utf-8"))["inputs"]
    )


STAB_OK = (
    "batch,time_months,value",
    "B001,0,99.9",
    "B001,3,99.7",
    "B001,6,99.5",
    "B002,0,100.5",
    "B002,3,99.8",
    "B002,6,99.0",
)
BE_HEADER = "subject,sequence,period,treatment,cmax,auc0t"


# --- URS-UI-001: templates ----------------------------------------------------------------


def test_dissolution_template_parses_and_runs() -> None:
    """URS-UI-001: the dissolution template parses into a valid input (12 units each)."""
    data = ui.parse_dissolution_csv(ui.template_csv("dissolution"))
    assert len(data.reference.units) == len(data.test.units) == 12
    assert dissolution.compare_profiles(data).f2 is not None


def test_stability_template_parses_and_runs() -> None:
    """URS-UI-001: the stability template parses into batches that make a valid input."""
    batches = ui.parse_stability_csv(ui.template_csv("stability"))
    data = StabilityInput.model_validate({**STAB_SETTINGS, "batches": batches})
    assert len(data.batches) == 3
    assert stability.estimate_shelf_life(data).proposed_shelf_life_months > 0


def test_be_template_parses_and_runs() -> None:
    """URS-UI-001: the BE template parses into records that make a valid input."""
    records = ui.parse_be_csv(ui.template_csv("be"))
    data = BeInput.model_validate({**BE_SETTINGS, "records": records})
    assert be.assess_bioequivalence(data).bioequivalent is True


def test_unknown_template_area_refused() -> None:
    """URS-UI-001: only the three areas have templates."""
    with pytest.raises(ValueError, match="unknown area"):
        ui.template_csv("assay")  # type: ignore[arg-type]


# --- URS-UI-002 to 005: CSV rejections ----------------------------------------------------


def test_missing_column_rejected() -> None:
    """URS-UI-002: a missing required column is named."""
    with pytest.raises(ui.CsvError, match="missing column.*'value'"):
        ui.parse_stability_csv(csv_bytes("batch,time_months", "B001,0"))


def test_unknown_column_rejected() -> None:
    """URS-UI-002: an unknown column is named, not ignored."""
    with pytest.raises(ui.CsvError, match="unknown column.*'analyst'"):
        ui.parse_stability_csv(csv_bytes("batch,time_months,value,analyst", "B001,0,99.9,AB"))


def test_duplicate_column_rejected() -> None:
    """URS-UI-002: a column given twice is rejected."""
    with pytest.raises(ui.CsvError, match="duplicate column.*'value'"):
        ui.parse_stability_csv(csv_bytes("batch,time_months,value,value", "B001,0,99.9,99.8"))


def test_row_with_wrong_field_count_rejected() -> None:
    """URS-UI-002: a row with more fields than the header (e.g. an unquoted 1,5) is rejected."""
    with pytest.raises(ui.CsvError, match="row 3: 4 fields, header has 3"):
        ui.parse_stability_csv(csv_bytes("batch,time_months,value", "B001,0,99.9", "B001,3,99,7"))


def test_auc0inf_column_is_optional() -> None:
    """URS-UI-002: auc0inf may be left out of the BE file; other columns are required."""
    records = ui.parse_be_csv(csv_bytes(BE_HEADER, "S01,TR,1,T,100.1,1500.2"))
    assert records[0].auc0inf is None


@pytest.mark.parametrize("cell", ["", "   "])
def test_blank_cell_rejected(cell: str) -> None:
    """URS-UI-003: a blank cell is named by row and column."""
    with pytest.raises(ui.CsvError, match=r"row 3, column 'value': blank"):
        ui.parse_stability_csv(
            csv_bytes("batch,time_months,value", "B001,0,99.9", f"B001,3,{cell}")
        )


def test_all_errors_reported_together() -> None:
    """URS-UI-003, URS-UI-004: every bad cell is listed, not just the first."""
    with pytest.raises(ui.CsvError) as info:
        ui.parse_stability_csv(csv_bytes("batch,time_months,value", "B001,0,", "B001,x,99.0"))
    assert len(info.value.errors) == 2
    assert "row 2, column 'value'" in str(info.value)
    assert "row 3, column 'time_months'" in str(info.value)


@pytest.mark.parametrize(
    "text", ["abc", "NaN", "nan", "inf", "-Infinity", '"1,5"', "1_000", " 99.5", "1e"]
)
def test_non_numeric_text_rejected(text: str) -> None:
    """URS-UI-004: only plain decimal numbers are accepted; nothing is coerced."""
    with pytest.raises(ui.CsvError, match=r"row 2, column 'value': .* is not a (finite )?number"):
        ui.parse_stability_csv(csv_bytes("batch,time_months,value", f"B001,0,{text}"))


@pytest.mark.parametrize("text", ["99.5", "+0.5", "1e2", "1.5E-3", ".5", "100"])
def test_plain_numbers_accepted(text: str) -> None:
    """URS-UI-004: ordinary decimal and exponent notation parse exactly as float(text)."""
    batches = ui.parse_stability_csv(
        csv_bytes("batch,time_months,value", f"B001,0,{text}", "B001,3,1", "B001,6,2")
    )
    assert batches[0].values[0] == float(text)


def test_overflowing_number_rejected() -> None:
    """URS-UI-004: 1e999 looks like a number but is infinite as a float; it is rejected."""
    with pytest.raises(ui.CsvError, match=r"row 2, column 'value': '1e999' is not a finite number"):
        ui.parse_stability_csv(csv_bytes("batch,time_months,value", "B001,0,1e999"))


def test_blank_period_rejected() -> None:
    """URS-UI-003: a blank whole-number cell is named by row and column."""
    with pytest.raises(ui.CsvError, match=r"row 2, column 'period': blank"):
        ui.parse_be_csv(csv_bytes(BE_HEADER, "S01,TR,,T,100.1,1500.2"))


@pytest.mark.parametrize("text", ["1.0", "one", "1.5", "+-1"])
def test_non_integer_period_rejected(text: str) -> None:
    """URS-UI-004: the BE period must be a whole number written as one."""
    with pytest.raises(ui.CsvError, match=r"row 2, column 'period': .* is not a whole number"):
        ui.parse_be_csv(csv_bytes(BE_HEADER, f"S01,TR,{text},T,100.1,1500.2"))


@pytest.mark.parametrize(("raw", "message"), [(b"", "empty"), (b"\n\n", "empty")])
def test_empty_file_rejected(raw: bytes, message: str) -> None:
    """URS-UI-005: an empty file is rejected."""
    with pytest.raises(ui.CsvError, match=message):
        ui.parse_stability_csv(raw)


def test_header_only_file_rejected() -> None:
    """URS-UI-005: a header without data rows is rejected."""
    with pytest.raises(ui.CsvError, match="no data rows"):
        ui.parse_stability_csv(csv_bytes("batch,time_months,value"))


def test_non_utf8_file_rejected() -> None:
    """URS-UI-005: Latin-1 bytes are rejected rather than guessed."""
    raw = "batch,time_months,value\nBätch,0,99.9\n".encode("latin-1")
    with pytest.raises(ui.CsvError, match="not UTF-8"):
        ui.parse_stability_csv(raw)


def test_near_duplicate_batch_labels_in_csv_rejected() -> None:
    """URS-STAB-015, URS-UI-007: 'B001 ' in a CSV is not quietly turned into a second batch."""
    rows = [
        f"{lab},{t},{v}" for lab in ("B001", "B001 ") for t, v in ((0, 100.0), (3, 99.5), (6, 99.1))
    ]
    with pytest.raises(ValidationError, match=r"'B001 ' has leading or trailing whitespace"):
        ui.parse_stability_csv(csv_bytes("batch,time_months,value", *rows))


def test_utf8_bom_accepted() -> None:
    """URS-UI-005: a UTF-8 byte-order mark (as written by Excel) is accepted."""
    batches = ui.parse_stability_csv(b"\xef\xbb\xbf" + csv_bytes(*STAB_OK))
    assert [b.label for b in batches] == ["B001", "B002"]


# --- URS-UI-006: dissolution layout -------------------------------------------------------


def diss_rows(units: int = 12, times: tuple[float, ...] = (5.0, 10.0, 15.0)) -> list[list[str]]:
    rows = []
    for product, base in (("Reference", 30.0), ("Test", 28.0)):
        for u in range(1, units + 1):
            for k, t in enumerate(times):
                rows.append([product, str(u), str(t), str(base * (k + 1) + 0.1 * u)])
    return rows


def diss_csv(rows: list[list[str]]) -> bytes:
    return csv_bytes("product,unit,time_min,percent_dissolved", *(",".join(r) for r in rows))


def test_dissolution_pivot_by_unit_and_time() -> None:
    """URS-UI-006: long rows become one row per unit and one column per time point."""
    data = ui.parse_dissolution_csv(diss_csv(diss_rows()))
    assert data.times_min == (5.0, 10.0, 15.0)
    assert data.reference.units[0] == (30.1, 60.1, 90.1)
    assert data.test.units[11] == pytest.approx((29.2, 57.2, 85.2))


def test_dissolution_missing_cell_rejected() -> None:
    """URS-UI-006: a unit without a value at one time point is named."""
    rows = [r for r in diss_rows() if not (r[0] == "Reference" and r[1] == "4" and r[2] == "15.0")]
    with pytest.raises(ui.CsvError, match=r"Reference, unit 4: no value at 15.0 min"):
        ui.parse_dissolution_csv(diss_csv(rows))


def test_dissolution_duplicate_cell_rejected() -> None:
    """URS-UI-006: two values for the same unit and time are named with their rows."""
    rows = diss_rows()
    rows.append(["Test", "3", "10.0", "57.0"])
    with pytest.raises(ui.CsvError, match=r"Test, unit 3, 10.0 min: 2 values \(rows \d+, \d+\)"):
        ui.parse_dissolution_csv(diss_csv(rows))


def test_dissolution_unknown_product_rejected() -> None:
    """URS-UI-006: product must be exactly Reference or Test."""
    rows = diss_rows()
    rows[0][0] = "Ref"
    with pytest.raises(
        ui.CsvError, match=r"row 2, column 'product': 'Ref' must be 'Reference' or 'Test'"
    ):
        ui.parse_dissolution_csv(diss_csv(rows))


def test_dissolution_missing_product_rejected() -> None:
    """URS-UI-006: both products must be present."""
    rows = [r for r in diss_rows() if r[0] == "Reference"]
    with pytest.raises(ui.CsvError, match="no rows for product 'Test'"):
        ui.parse_dissolution_csv(diss_csv(rows))


def test_dissolution_model_rules_still_apply() -> None:
    """URS-UI-006, URS-UI-009: parsed data still pass through the model (here, 11 units)."""
    with pytest.raises(ValidationError, match="at least 12 required"):
        ui.parse_dissolution_csv(diss_csv(diss_rows(units=11)))


# --- URS-UI-007: original order kept ------------------------------------------------------


def test_stability_rows_grouped_by_first_appearance_in_file_order() -> None:
    """URS-UI-007: interleaved batches are grouped in order of first appearance and each
    batch keeps its rows in file order (not sorted by time)."""
    batches = ui.parse_stability_csv(
        csv_bytes(
            "batch,time_months,value",
            "B002,6,99.0",
            "B001,0,99.9",
            "B002,0,100.5",
            "B001,6,99.5",
            "B002,3,99.8",
            "B001,3,99.7",
        )
    )
    assert [b.label for b in batches] == ["B002", "B001"]
    assert batches[0].times_months == (6.0, 0.0, 3.0)
    assert batches[0].values == (99.0, 100.5, 99.8)


def test_be_records_kept_in_file_order() -> None:
    """URS-UI-007: BE records are returned in file order, as entered."""
    raw = csv_bytes(BE_HEADER, "S02,RT,2,T,95.0,1400.0", "S01,TR,1,T,100.1,1500.2")
    assert [(r.subject, r.period) for r in ui.parse_be_csv(raw)] == [("S02", 2), ("S01", 1)]


def test_dissolution_shuffled_rows_give_same_input() -> None:
    """URS-UI-007: values are placed by unit and time, so reordering the time rows of units 2-12
    gives the same data. Time order comes from the first unit, unit order from first appearance."""
    rows = diss_rows()
    n_times = 3
    blocks = [rows[i : i + n_times] for i in range(0, len(rows), n_times)]  # one block per unit
    shuffled = [r for k, b in enumerate(blocks) for r in (b if k % 12 == 0 else b[::-1])]
    assert shuffled != rows
    assert ui.parse_dissolution_csv(diss_csv(shuffled)) == ui.parse_dissolution_csv(diss_csv(rows))


# --- URS-UI-008: explicit settings --------------------------------------------------------


def test_missing_settings_lists_every_unset_item() -> None:
    """URS-UI-008: nothing is defaulted; the file and every setting must be given."""
    assert ui.missing_settings("stability", {}) == [
        "file",
        "attribute",
        "unit",
        "direction",
        "lower_limit",
        "significant_change_at_accelerated",
        "statistical_analysis_performed",
    ]
    assert ui.missing_settings("be", {"file": ("a.csv", b"x")}) == ["design", "limits"]
    assert ui.missing_settings("stability", {"file": ("a.csv", b"x"), **STAB_SETTINGS}) == []


def test_empty_text_and_false_are_handled_correctly() -> None:
    """URS-UI-008: an empty attribute is unset, but False is a real answer."""
    settings = {"file": ("a.csv", b"x"), **STAB_SETTINGS, "attribute": "  "}
    assert ui.missing_settings("stability", settings) == ["attribute"]
    settings = {**settings, "attribute": "Assay", "significant_change_at_accelerated": False}
    assert ui.missing_settings("stability", settings) == []


@pytest.mark.parametrize(
    ("seed", "n", "missing"),
    [
        (None, None, []),
        (1, 1000, []),
        (1, None, ["bootstrap_n_resamples"]),
        (None, 1000, ["bootstrap_seed"]),
    ],
)
def test_bootstrap_settings_together_or_not_at_all(
    seed: int | None, n: int | None, missing: list[str]
) -> None:
    """URS-UI-008: dissolution seed and resample count are given together or not at all."""
    settings = {"file": ("a.csv", b"x"), "bootstrap_seed": seed, "bootstrap_n_resamples": n}
    assert ui.missing_settings("dissolution", settings) == missing


# --- URS-GEN-003, URS-UI-009: running from an upload --------------------------------------


def test_source_file_hashes_raw_bytes() -> None:
    """URS-GEN-003: name, size and SHA-256 of exactly the bytes uploaded."""
    raw = ui.template_csv("stability")
    sf = ui.source_file("my data.csv", raw)
    assert (sf.name, sf.size_bytes) == ("my data.csv", len(raw))
    assert sf.sha256 == hashlib.sha256(raw).hexdigest()


def test_run_analysis_stamps_file_hash() -> None:
    """URS-GEN-003: the uploaded file's hash reaches the result metadata; one changed byte
    changes it while the parsed input hash stays the same when the data are equivalent."""
    raw = ui.template_csv("stability")
    result = ui.run_analysis("stability", "stab.csv", raw, STAB_SETTINGS, timestamp=FIXED_TIME)
    assert result.metadata.source_files == (ui.source_file("stab.csv", raw),)
    edited = raw.replace(b"\n", b"\r\n")  # same data, different bytes
    other = ui.run_analysis("stability", "stab.csv", edited, STAB_SETTINGS, timestamp=FIXED_TIME)
    assert other.metadata.source_files[0].sha256 != result.metadata.source_files[0].sha256
    assert other.metadata.input_hash == result.metadata.input_hash


def test_run_analysis_dissolution_with_and_without_bootstrap() -> None:
    """URS-UI-008, URS-GEN-003: dissolution runs with no bootstrap settings, or with both."""
    raw = ui.template_csv("dissolution")
    plain = ui.run_analysis("dissolution", "d.csv", raw, {}, timestamp=FIXED_TIME)
    assert plain.bootstrap_settings is None
    seeded = ui.run_analysis(
        "dissolution",
        "d.csv",
        raw,
        {"bootstrap_seed": 7, "bootstrap_n_resamples": 1000},
        timestamp=FIXED_TIME,
    )
    assert seeded.bootstrap_settings == BootstrapSettings(seed=7, n_resamples=1000)


@pytest.mark.parametrize("settings", [{"bootstrap_seed": 7}, {"bootstrap_n_resamples": 1000}])
def test_run_analysis_refuses_half_bootstrap_settings(settings: dict[str, int]) -> None:
    """URS-UI-008: a seed without a resample count (or the reverse) is refused, not filled in."""
    with pytest.raises(ValueError, match="both the bootstrap seed and the resample count"):
        ui.run_analysis("dissolution", "d.csv", ui.template_csv("dissolution"), settings)


def test_run_analysis_be() -> None:
    """URS-GEN-003: BE runs from the template with the chosen design and limits."""
    raw = ui.template_csv("be")
    result = ui.run_analysis("be", "be.csv", raw, BE_SETTINGS, timestamp=FIXED_TIME)
    assert result.metadata.source_files[0].name == "be.csv"


def test_run_analysis_passes_model_errors_through() -> None:
    """URS-UI-009: an unsupported setting raises the model's own message, unchanged."""
    raw = ui.template_csv("be")
    with pytest.raises(ValidationError, match="not supported in v1"):
        ui.run_analysis("be", "be.csv", raw, {**BE_SETTINGS, "design": "replicate"})


@pytest.mark.parametrize("area", ["dissolution", "stability", "be"])
def test_template_source_is_named_after_the_template(area: str) -> None:
    """URS-UI-014: template data are recorded under the template's file name, with the hash of
    the template bytes, and the dummy-data warning text is fixed."""
    name, raw = ui.template_source(area)  # type: ignore[arg-type]
    assert name == f"template_{area}.csv"
    assert raw == ui.template_csv(area)  # type: ignore[arg-type]
    assert ui.TEMPLATE_WARNING == "Result from template dummy data, not your data"


def test_template_run_records_template_name() -> None:
    """URS-UI-014, URS-GEN-003: a run on template data stamps the template name and hash."""
    name, raw = ui.template_source("be")
    result = ui.run_analysis("be", name, raw, BE_SETTINGS)
    assert result.metadata.source_files == (ui.source_file("template_be.csv", raw),)


# --- URS-UI-011: prominent notes ----------------------------------------------------------


def test_prominent_notes_skip_confirmed_stability_notes() -> None:
    """URS-UI-011: the separate-slopes note (ICH Q1E Appendix B.2.2.1, PC-STAB-01) and the
    Q1A(R2) fewer-than-3-batches warning (2.1.3 and 2.2.3, PC-STAB-02) are confirmed, so neither
    is promoted; the warning is still shown in its own box by ui.show_result."""
    data = stab_golden("GOLD-STAB-003")
    two_batches = data.model_copy(update={"batches": data.batches[1:]})
    result = stability.estimate_shelf_life(two_batches)
    assert stability.SEPARATE_MODEL_NOTE in result.notes
    assert any("ICH Q1A(R2)" in w for w in result.warnings)
    assert ui.prominent_notes(result) == []


def test_prominent_notes_include_bootstrap_method_note() -> None:
    """URS-UI-011: the provisional bootstrap method note is surfaced (high late CV forces the
    bootstrap path)."""
    times = [5.0, 10.0, 15.0, 20.0, 30.0, 45.0]
    spreads = [0.02, 0.02, 0.02, 0.02, 0.4, 0.4]
    factors = [2 * i / 11 - 1 for i in range(12)]

    def profile(label: str, means: list[float]) -> DissolutionProfile:
        units = [[m * (1 + s * f) for m, s in zip(means, spreads, strict=True)] for f in factors]
        return DissolutionProfile(label=label, times_min=times, units=units)

    data = DissolutionInput(
        reference=profile("Reference", [20, 40, 60, 75, 88, 95]),
        test=profile("Test", [18, 37, 56, 72, 86, 94]),
    )
    result = dissolution.compare_profiles(data, BootstrapSettings(seed=1, n_resamples=1000))
    assert result.bootstrap is not None
    assert result.bootstrap.method_note in ui.prominent_notes(result)

    # URS-UI-012: the summary table records the seed and the interval at full precision
    summary = dict(ui.dissolution_tables(result)["summary"].itertuples(index=False))
    assert summary["bootstrap_seed"] == "1"
    assert summary["bootstrap_lower"] == str(result.bootstrap.lower)


def test_prominent_notes_be_rounding_placeholder() -> None:
    """URS-UI-011: the BE rounding and AUC0-inf placeholders are surfaced."""
    notes = ui.prominent_notes(be.assess_bioequivalence(be_golden("GOLD-BE-001")))
    assert any("rounded" in n and "pending confirmation" in n for n in notes)
    assert any("AUC0-inf" in n for n in notes)


def test_ordinary_notes_not_promoted() -> None:
    """URS-UI-011: a pooled, 3-batch stability result has no provisional notes."""
    assert ui.prominent_notes(stability.estimate_shelf_life(stab_golden("GOLD-STAB-001"))) == []


# --- URS-UI-012: tables keep full precision -----------------------------------------------


def test_stability_tables_full_precision() -> None:
    """URS-UI-012: table cells equal the result fields exactly."""
    result = stability.estimate_shelf_life(stab_golden("GOLD-STAB-002"))
    tables = ui.stability_tables(result)
    assert tables["per_batch"]["crossing_months"].tolist() == [
        p.crossing_months for p in result.per_batch
    ]
    assert tables["batch_fits"]["slope"].tolist() == [f.slope for f in result.batch_fits]
    assert tables["poolability"]["p_value"].tolist() == [
        result.poolability.slopes.p_value,
        result.poolability.intercepts.p_value,  # type: ignore[union-attr]
    ]


def test_be_tables_full_precision() -> None:
    """URS-UI-012: CI limits are unrounded; rounded limits are their own columns."""
    result = be.assess_bioequivalence(be_golden("GOLD-BE-001"))
    tables = ui.be_tables(result)
    params = tables["parameters"]
    assert params["ci_lower_pct"].tolist() == [p.ci_lower_pct for p in result.parameters]
    assert params["ci_lower_rounded"].tolist() == [p.ci_lower_rounded for p in result.parameters]
    anova = tables["anova"]
    assert len(anova) == 5 * len(result.parameters)
    assert anova["ss"].tolist() == [r.ss for p in result.parameters for r in p.anova]


def test_dissolution_tables_full_precision() -> None:
    """URS-UI-012: mean profiles and CVs are shown unrounded; used points are flagged."""
    result = dissolution.compare_profiles(ui.parse_dissolution_csv(ui.template_csv("dissolution")))
    tables = ui.dissolution_tables(result)
    assert tables["profile"]["mean_reference"].tolist() == list(result.mean_reference)
    assert tables["profile"]["used"].sum() == result.n_points_used
    assert result.cv_check is not None
    assert tables["cv"]["cv_test_pct"].tolist() == [p.cv_test_pct for p in result.cv_check.points]


# --- URS-UI-013: charts -------------------------------------------------------------------


def trace_kinds(fig: Any) -> set[str]:
    kinds = set()
    for trace in fig.data:
        if trace.type == "scatter":
            assert "lines" in trace.mode
        kinds.add(trace.type)
    return kinds


def test_dissolution_chart_is_two_lines() -> None:
    """URS-UI-013: reference and test mean profiles as lines."""
    result = dissolution.compare_profiles(ui.parse_dissolution_csv(ui.template_csv("dissolution")))
    fig = ui.dissolution_chart(result)
    assert trace_kinds(fig) == {"scatter"}
    assert [t.name for t in fig.data] == ["Reference", "Test"]
    assert list(fig.data[0].y) == list(result.mean_reference)


def test_stability_chart_lines_and_bound() -> None:
    """URS-UI-013: batch data, fitted mean, 95% lower bound (from core.lower_bound) and limit."""
    result = stability.estimate_shelf_life(stab_golden("GOLD-STAB-002"))
    fig = ui.stability_chart(result)
    assert trace_kinds(fig) == {"scatter"}
    names = [t.name for t in fig.data]
    assert {"B001 data", "B003 mean", "B003 95% lower bound", "Lower limit"} <= set(names)
    bound = fig.data[names.index("B003 95% lower bound")]
    expected = stability.lower_bound(result.inputs, "common_slope", "B003", np.asarray(bound.x))
    np.testing.assert_array_equal(np.asarray(bound.y), expected)
    assert max(bound.x) == result.extrapolation.cap_months


def test_be_chart_bars_with_ci_and_limits() -> None:
    """URS-UI-013: point-estimate bars, asymmetric 90% CI error bars, 80/125% lines."""
    result = be.assess_bioequivalence(be_golden("GOLD-BE-001"))
    fig = ui.be_chart(result)
    assert trace_kinds(fig) == {"bar", "scatter"}
    bar = next(t for t in fig.data if t.type == "bar")
    p = result.parameters[0]
    assert bar.y[0] == p.pe_pct
    assert bar.error_y.array[0] == p.ci_upper_pct - p.pe_pct
    assert bar.error_y.arrayminus[0] == p.pe_pct - p.ci_lower_pct
    lines = [t for t in fig.data if t.type == "scatter"]
    assert sorted({y for t in lines for y in t.y}) == [80.0, 125.0]
