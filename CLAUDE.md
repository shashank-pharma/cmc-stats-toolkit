# CMC Stats Toolkit

Statistics engine and web app for CMC regulatory work: ICH Q1E stability shelf-life,
dissolution similarity (f1, f2, bootstrap f2) and 2x2 crossover bioequivalence (90% CI, TOST).
Educational and decision-support tool. Not validated for GxP use.

## Stack
- Python 3.12+, managed with `uv`
- Core maths: NumPy, SciPy, statsmodels, pandas
- Data models and input validation: pydantic v2
- API: FastAPI. UI (v1): Streamlit with simple Plotly bar and line charts
- PDF reports: ReportLab
- Tests: pytest, pytest-cov, hypothesis. Lint/format: ruff. Types: mypy (strict on src/)

## Commands
- Install: `uv sync`
- All checks: `/verify` (ruff, mypy, pytest with coverage)
- Run tests only: `uv run pytest -q`
- Run API: `uv run uvicorn cmc_stats.api:app --reload`
- Run UI: `uv run streamlit run src/cmc_stats/ui.py`

## Architecture (keep these layers separate)
- `src/cmc_stats/criteria.py`: every regulatory constant, each with its guideline and section
- `src/cmc_stats/core/`: pure functions only. No file I/O, no printing, no UI code
- `src/cmc_stats/models.py`: pydantic input and result models
- `src/cmc_stats/api.py`: FastAPI routes that call core functions
- `src/cmc_stats/ui.py`: Streamlit screens that call the API or core
- `src/cmc_stats/report.py`: PDF report; stamps app version, guideline version and input hash

## Rules
- Never invent or change a regulatory criterion. Read `/ich-stats-rules` first; if a rule is not
  there, stop and ask me.
- Every public function gets type hints and a docstring that cites the guideline and section.
- Never edit an expected value in `tests/golden/` to make a test pass. A mismatch means the code
  or the reference is wrong: investigate and report.
- Keep full precision in calculations. Round only when displaying or reporting.
- Reject bad input loudly (pydantic errors). Never drop or impute data silently.
- Any random step (bootstrap, simulation) takes an explicit seed and records it in the result.
- New requirement: add an ID in `docs/URS.md`, a test that references the ID, then the code.
- Use dummy or published data only. No real company data in the repo.

## Definition of done for a feature
1. Golden test against a published worked example passes (use `/golden-test`)
2. `/verify` passes
3. `/validation-docs` updates the traceability matrix
4. `/gxp-review` finds no open issues
