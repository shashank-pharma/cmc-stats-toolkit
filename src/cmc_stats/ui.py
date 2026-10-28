"""Streamlit UI (v1): CSV upload, results tables and simple charts for the three modules.

Layout only: parsing, settings checks, notes, tables and charts live in ``cmc_stats.ui_helpers``
(unit-tested). The UI calls the core functions directly and records the uploaded file's
SHA-256 in the result metadata. Educational and decision-support use only. Not validated for
GxP use.

Run: uv run streamlit run src/cmc_stats/ui.py
"""

from typing import Any

import pandas as pd
import streamlit as st

from cmc_stats import __version__, criteria
from cmc_stats import ui_helpers as helpers
from cmc_stats.models import DISCLAIMER
from cmc_stats.ui_helpers import AnyResult, Area

TABS: tuple[tuple[Area, str], ...] = (
    ("dissolution", "Dissolution"),
    ("stability", "Stability"),
    ("be", "Bioequivalence"),
)


def yes_no(value: bool) -> str:
    """Label for a True/False choice."""
    return "Yes" if value else "No"


def choose_source(area: Area) -> tuple[str, bytes, bool] | None:
    """Uploaded file, or the template's dummy data if chosen; (name, raw bytes, is_template)."""
    uploaded = st.file_uploader("Upload CSV", type=["csv"], key=f"upload_{area}")
    use_template = st.checkbox(
        "Use the template's dummy data instead of an upload", key=f"example_{area}"
    )
    if uploaded is not None:
        if use_template:
            st.caption("An upload is present, so it is used and the template is ignored.")
        return str(uploaded.name), bytes(uploaded.getvalue()), False
    if use_template:
        name, raw = helpers.template_source(area)
        return name, raw, True
    return None


def settings_for(area: Area) -> dict[str, Any]:
    """Explicit setting widgets with no defaults (URS-UI-008)."""
    if area == "dissolution":
        st.caption(
            "Bootstrap f2 is needed only when the CV limits fail. Give both values or neither."
        )
        return {
            "bootstrap_seed": st.number_input(
                "Bootstrap seed", min_value=0, step=1, value=None, key="diss_seed"
            ),
            "bootstrap_n_resamples": st.number_input(
                "Bootstrap resamples",
                min_value=criteria.BOOTSTRAP_MIN_RESAMPLES,
                step=1000,
                value=None,
                key="diss_n",
            ),
        }
    if area == "stability":
        return {
            "attribute": st.text_input("Attribute", key="stab_attribute"),
            "unit": st.text_input("Unit", key="stab_unit"),
            "direction": st.selectbox(
                "Expected direction (v1 supports decrease only)",
                ["decrease", "increase", "either"],
                index=None,
                key="stab_direction",
            ),
            "lower_limit": st.number_input(
                "Lower acceptance limit", value=None, format="%.4f", key="stab_lower_limit"
            ),
            "significant_change_at_accelerated": st.selectbox(
                "Significant change at accelerated condition?",
                [True, False],
                index=None,
                format_func=yes_no,
                key="stab_sig_change",
            ),
            "statistical_analysis_performed": st.selectbox(
                "Statistical analysis of long-term data performed?",
                [True, False],
                index=None,
                format_func=yes_no,
                key="stab_stats_done",
            ),
        }
    return {
        "design": st.selectbox(
            "Study design (v1 supports 2x2 crossover only)",
            ["2x2_crossover", "replicate", "parallel"],
            index=None,
            key="be_design",
        ),
        "limits": st.selectbox(
            "Acceptance limits (v1 supports average BE only)",
            ["average", "reference_scaled"],
            index=None,
            key="be_limits",
        ),
    }


def show_table(title: str, frame: pd.DataFrame) -> None:
    """Full-precision data; floats are rounded only by the display format (URS-UI-012)."""
    st.markdown(f"**{title.replace('_', ' ').capitalize()}**")
    config = {
        col: st.column_config.NumberColumn(format="%.6g")
        for col in frame.columns
        if frame[col].dtype.kind == "f"
    }
    st.dataframe(frame, hide_index=True, column_config=config)


def show_result(area: Area, result: AnyResult, is_template: bool) -> None:
    """Warnings first (template data, provisional and pending notes), then the conclusion,
    traceability, tables, chart and all notes (URS-UI-011 to 014, URS-GEN-003)."""
    if is_template:
        st.warning(helpers.TEMPLATE_WARNING)
    prominent = helpers.prominent_notes(result)
    for note in prominent:
        st.warning(note)
    for warning in getattr(result, "warnings", ()):
        if warning not in prominent:
            st.warning(warning)
    st.markdown(f"**Conclusion:** {result.conclusion}")
    meta = result.metadata
    for source in meta.source_files:
        st.caption(
            f"Source file: {source.name} ({source.size_bytes} bytes), SHA-256 {source.sha256}"
        )
    st.caption(
        f"App {meta.app_version} | {meta.guideline_version} | input hash {meta.input_hash} | "
        f"{meta.timestamp.isoformat()}"
    )
    for title, frame in helpers.TABLES[area](result).items():
        show_table(title, frame)
    st.plotly_chart(helpers.CHARTS[area](result))
    with st.expander("All notes"):
        for note in result.notes:
            st.markdown(f"- {note}")


def render_tab(area: Area) -> None:
    """One analysis tab: disclaimer, template, upload, settings, Run and results."""
    st.info(DISCLAIMER)
    st.download_button(
        "Download CSV template",
        data=helpers.template_csv(area),
        file_name=f"template_{area}.csv",
        mime="text/csv",
        key=f"template_{area}",
    )
    source = choose_source(area)
    settings = settings_for(area)
    missing = helpers.missing_settings(area, {**settings, "file": source})
    if missing:
        st.caption("Needed before Run: " + ", ".join(missing))
    run = st.button("Run", key=f"run_{area}", disabled=bool(missing), type="primary")
    if not run or source is None:
        return
    name, raw, is_template = source
    try:
        result = helpers.run_analysis(area, name, raw, settings)
    except ValueError as exc:  # CsvError, pydantic ValidationError and core errors
        st.error(str(exc))
        return
    show_result(area, result, is_template)


st.set_page_config(page_title="CMC Stats Toolkit", layout="wide")
st.title("CMC Stats Toolkit")
st.caption(f"Version {__version__}")
for (tab_area, _), tab in zip(TABS, st.tabs([label for _, label in TABS]), strict=True):
    with tab:
        render_tab(tab_area)
