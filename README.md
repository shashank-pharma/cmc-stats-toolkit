# CMC Stats Toolkit

Version 1.0.0. A statistics engine and web app for CMC regulatory work:

- **Stability shelf-life** (ICH Q1A(R2) and ICH Q1E, Step 4, 2003): batch poolability at the
  0.25 significance level (pooled, common slope or separate model), the one-sided 95% confidence
  bound against the acceptance criterion, and the Appendix A extrapolation cap.
- **Dissolution similarity** (FDA, Dissolution Testing of Immediate Release Solid Oral Dosage
  Forms, 1997): f1, f2, the CV and 85% cut-off rules, and a seeded bootstrap f2 as a
  supplementary method (Shah et al. 1998, provisional).
- **Bioequivalence, 2x2 crossover** (ICH M13A, 2024; FDA, Statistical Approaches to
  Establishing Bioequivalence, May 2026): ANOVA on log-transformed Cmax, AUC0-t and AUC0-inf,
  the 90% confidence interval and TOST against 80.00-125.00%.

The target agency is US FDA, with ICH as the harmonised base; EMA differences are shown as
notes only (URS-GEN-005). Every result records the app version, guideline version, input
hash and any random seed in `ResultMetadata`.

> **Disclaimer:** Educational and decision-support tool. **Not validated for GxP use.** Do not
> use its results as the basis for a regulatory submission or a batch release decision.

## Screenshots

<!-- Screenshot placeholder: Stability tab, with the result and the regression chart -->
<!-- Screenshot placeholder: Dissolution tab, with the f1/f2 result and the profile chart -->
<!-- Screenshot placeholder: Bioequivalence tab, with the 90% CI result -->
<!-- Screenshot placeholder: the known-limitations warning box on a result -->

_Screenshots to be added._

## How to run

Needs Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                         # install
uv run streamlit run src/cmc_stats/ui.py        # web UI (Stability, Dissolution, Bioequivalence tabs)
uv run uvicorn cmc_stats.api:app --reload       # API: GET /health, POST /stability, /dissolution, /be
uv run pytest -q                                # tests
```

`sample_data/` holds dummy CSVs in the UI template format with their expected results (see
`sample_data/README.md`). Use dummy or published data only.

## Validation summary

As of v1.0.0 (`/verify` PASS, 2026-11-06): ruff format and lint, mypy strict, 397 tests
passed, coverage 99.25% on `src/cmc_stats`. All 87 URS requirements (`docs/URS.md`) trace to
code and at least one test (`docs/traceability.md`).

| Module | URS IDs | Tests | Coverage | Golden cases (cross-checked against base R) |
|---|---|---|---|---|
| Stability (`core/stability.py`) | 26 (URS-STAB) | 125 | 99% | 3: GOLD-STAB-001..003, base R `lm`/`anova` on dummy data, also checked against statsmodels |
| Dissolution (`core/dissolution.py`) | 14 (URS-DISS) | 49 | 98% | 1: GOLD-DISS-001, hand calculation reproduced in base R |
| Bioequivalence (`core/be.py`) | 22 (URS-BE) | 70 | 99% | 3: GOLD-BE-001..003, base R on seeded dummy data |
| General, API and UI (`models.py`, `criteria.py`, `api.py`, `ui.py`, `ui_helpers.py`) | 25 (URS-GEN 5, URS-API 6, URS-UI 14) | 153 | 96-100% | none |
| **Total** | **87** | **397** | **99.25%** | **7 cases, 10 golden tests** |

Tests are counted by test file (`tests/test_<module>.py` plus its golden runner); the
general row covers `test_api`, `test_criteria`, `test_metadata`, `test_sample_data`,
`test_ui_app` and `test_ui_helpers`. No golden case is yet a published worked example (see
the known limitations).

Every regulatory constant is in `src/cmc_stats/criteria.py` with its guideline and section.
Each guideline citation was confirmed against its source, or recorded as a known limitation,
in `docs/RELEASE-1.0.0.md`. `/gxp-review` ran on v0.9.0 with all checks clear; only
documentation changed after that.

## Known limitations

Each is shown in the warning box on every affected result.

**Stability**
- Only the room-temperature, no-significant-change, statistical-analysis branch of the
  ICH Q1E Appendix A cap is supported. Refrigerated and freezer storage, and significant
  change at accelerated, are refused as "not supported in v1".
- X, "the period covered by long-term data", is taken as the shortest batch coverage.
- Rules follow ICH Q1A(R2) and Q1E (2003), not the draft consolidated ICH Q1 (Step 2, 2025).
- Golden cases are base R output on dummy data, not a published example.

**Dissolution**
- Bootstrap f2 is not in FDA 1997; it is supplementary and provisional (Shah et al. 1998). The
  multivariate (MSD) method FDA names is not in v1. There is no bootstrap golden case.
- The 20% CV limit at "earlier time points (e.g., 15 minutes)" is read as t <= 15 min.
- f2 = 50 exactly, and a bootstrap lower bound of exactly 50, count as similar.
- The golden case is a hand calculation reproduced in base R, not a published example.

**Bioequivalence**
- No guidance states the CI rounding mode; rounding half up to 2 decimals is this tool's
  choice.
- The FDA ANDA PK-endpoints guidance cited in the FDA BE statistics guidance (footnote 6) was
  not checked.
- Golden cases are base R output on seeded dummy data, not a published example.

**Out of scope for v1:** stability attributes that increase or move either way; replicate and
parallel BE designs; reference-scaled limits.

## Roadmap (v1.1)

- Published golden examples: stability, dissolution f1/f2 (Shah et al. 1998) and BE
  (Schutz et al. 2014).
- PDF report stamped with app version, guideline version and input hash.
- Refrigerated stability branch (ICH Q1E Appendix A: Y up to 1.5X, not exceeding X + 6 months).

## Project documents

- `docs/URS.md`: user requirements
- `docs/traceability.md`: requirement to code to test matrix
- `docs/RELEASE-1.0.0.md`: confirmation register and release decision
- `CHANGELOG.md`: release history

## Working with Claude Code

Open this folder in a terminal and run `claude`. Project rules are in `CLAUDE.md`.
Project skills live in `.claude/skills/`:

| Skill | Use it for |
|---|---|
| `/ich-stats-rules` | The regulatory rules every calculation must follow (loads automatically) |
| `/golden-test` | Add a test from a published worked example |
| `/verify` | Lint, types, tests and coverage before every commit |
| `/validation-docs` | Update URS, traceability matrix and changelog after a feature |
| `/gxp-review` | Data-integrity review of your changes |
