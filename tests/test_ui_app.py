"""Streamlit app smoke tests with AppTest. Each test cites the requirement it proves.

AppTest cannot upload files, so the run path is driven through each tab's "use the template's
dummy data" checkbox, which feeds the template bytes through the same parsing and hashing.
"""

import hashlib
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from cmc_stats import ui_helpers
from cmc_stats.models import DISCLAIMER

APP = str(Path(__file__).parents[1] / "src" / "cmc_stats" / "ui.py")
TABS = {"dissolution": 0, "stability": 1, "be": 2}


@pytest.fixture
def app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    return at


def set_stability(at: AppTest) -> None:
    at.checkbox(key="example_stability").check()
    at.text_input(key="stab_attribute").input("Assay")
    at.text_input(key="stab_unit").input("% label claim")
    at.selectbox(key="stab_direction").set_value("decrease")
    at.number_input(key="stab_lower_limit").set_value(95.0)
    at.selectbox(key="stab_sig_change").set_value(False)
    at.selectbox(key="stab_stats_done").set_value(True)


def test_three_tabs_each_with_disclaimer(app: AppTest) -> None:
    """URS-UI-010: the disclaimer is shown on every tab."""
    assert [t.label for t in app.tabs] == ["Dissolution", "Stability", "Bioequivalence"]
    for tab in app.tabs:
        assert any(DISCLAIMER in box.value for box in tab.info)


def test_run_disabled_until_file_and_settings_given(app: AppTest) -> None:
    """URS-UI-008: Run starts disabled; selections start empty; Run enables when all are set."""
    for area in TABS:
        assert app.button(key=f"run_{area}").disabled
    assert app.selectbox(key="be_design").value is None
    assert app.selectbox(key="stab_direction").value is None
    assert app.number_input(key="stab_lower_limit").value is None
    app.checkbox(key="example_stability").check().run()
    assert app.button(key="run_stability").disabled
    set_stability(app)
    app.run()
    assert not app.button(key="run_stability").disabled


def test_stability_run_shows_conclusion_tables_chart_and_file_hash(app: AppTest) -> None:
    """URS-UI-012, URS-UI-013, URS-GEN-003: results, chart and the source file hash appear."""
    set_stability(app)
    app.run()
    app.button(key="run_stability").click().run()
    assert not app.exception
    tab = app.tabs[TABS["stability"]]
    assert not tab.error
    assert any("Proposed shelf-life" in m.value for m in tab.markdown)
    assert len(tab.dataframe) >= 3
    assert tab.get("plotly_chart")
    digest = hashlib.sha256(ui_helpers.template_csv("stability")).hexdigest()
    assert any(digest in c.value for c in tab.caption)


def test_be_run_shows_pending_confirmation_warning(app: AppTest) -> None:
    """URS-UI-011: BE placeholder notes appear in warning boxes."""
    app.checkbox(key="example_be").check()
    app.selectbox(key="be_design").set_value("2x2_crossover")
    app.selectbox(key="be_limits").set_value("average")
    app.run()
    app.button(key="run_be").click().run()
    assert not app.exception
    tab = app.tabs[TABS["be"]]
    assert any("pending confirmation" in w.value for w in tab.warning)
    assert any("Bioequivalent" in m.value for m in tab.markdown)
    assert tab.get("plotly_chart")


def test_unsupported_choice_shows_error_and_no_result(app: AppTest) -> None:
    """URS-UI-009: the model's message is shown verbatim and no result is displayed."""
    app.checkbox(key="example_be").check()
    app.selectbox(key="be_design").set_value("replicate")
    app.selectbox(key="be_limits").set_value("average")
    app.run()
    app.button(key="run_be").click().run()
    assert not app.exception
    tab = app.tabs[TABS["be"]]
    assert any("not supported in v1" in e.value for e in tab.error)
    assert not tab.dataframe
    assert not tab.get("plotly_chart")


@pytest.mark.parametrize("area", ["dissolution", "stability", "be"])
def test_template_data_result_carries_dummy_data_warning(app: AppTest, area: str) -> None:
    """URS-UI-014: a result from template data shows the dummy-data warning and names the
    template as the source file."""
    if area == "stability":
        set_stability(app)
    else:
        app.checkbox(key=f"example_{area}").check()
    if area == "be":
        app.selectbox(key="be_design").set_value("2x2_crossover")
        app.selectbox(key="be_limits").set_value("average")
    app.run()
    app.button(key=f"run_{area}").click().run()
    assert not app.exception
    tab = app.tabs[TABS[area]]
    assert any(w.value == ui_helpers.TEMPLATE_WARNING for w in tab.warning)
    assert any(f"template_{area}.csv" in c.value for c in tab.caption)


def test_dissolution_run_without_bootstrap(app: AppTest) -> None:
    """URS-UI-008, URS-UI-013: dissolution runs with no bootstrap settings and plots lines."""
    app.checkbox(key="example_dissolution").check().run()
    assert not app.button(key="run_dissolution").disabled
    app.button(key="run_dissolution").click().run()
    assert not app.exception
    tab = app.tabs[TABS["dissolution"]]
    assert not tab.error
    assert any("Similar" in m.value for m in tab.markdown)
    assert tab.get("plotly_chart")
