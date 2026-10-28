# Changelog

## 0.5.0 - 2026-10-28
No calculated result changes for existing inputs: every number from 0.4.0 is reproduced (all
golden tests pass unchanged). Two behaviour changes to note:
- Result JSON gains `metadata.source_files` (an empty list when the input did not come from
  a file).
- Stability input that 0.4.0 accepted is now rejected when batch labels have leading or
  trailing whitespace or differ only by letter case (URS-STAB-015); such input used to run
  as extra batches.

Versioning: pre-1.0 versions may change behaviour (as above) in a minor release; 1.0.0 is
reserved for when all pending confirmations listed in docs/traceability.md are closed.

### Added
- FastAPI app `cmc_stats.api` (URS-API-001 to 006): `GET /health`; `POST /dissolution`,
  `/stability` and `/be` taking the existing input models and returning the core result
  models unchanged; invalid input and core `ValueError`s give 422, an internal result that
  fails its own model gives 500.
- Streamlit app `cmc_stats.ui` (URS-UI-001 to 014), calling the core directly: three tabs
  with the disclaimer, CSV template download, upload or template dummy data (with the
  warning "Result from template dummy data, not your data"), explicit settings with no
  defaults, warning boxes for provisional and pending-confirmation notes, full-precision
  tables and Plotly line/bar charts.
- `cmc_stats.ui_helpers`: strict stdlib-csv parsing (blank cells, unknown columns, non-UTF-8,
  NaN/inf/decimal-comma text rejected with row and column), templates, settings checks,
  `run_analysis`, notes, tables and charts; all unit-tested.
- `SourceFile` model and `ResultMetadata.source_files`: name, size and SHA-256 of the raw
  uploaded bytes (URS-GEN-003); optional `source_files` argument on `compare_profiles`,
  `estimate_shelf_life` and `assess_bioequivalence`, not part of `input_hash`.
- Sample-data pack in `sample_data/` (URS-GEN-004): 8 dummy CSVs in the template format with
  seeded generators (numpy 2.5.4, R 4.6.1), `build_expected.py` and `expected.json`, checked by
  `tests/test_sample_data.py`.
- Requirements URS-GEN-003, URS-GEN-004, URS-API-001 to 006 and URS-UI-001 to 014.
- Dev dependency `httpx2` for FastAPI's `TestClient` (replaces `httpx`, which Starlette 1.9
  deprecates for its test client).

### Changed
- URS-STAB-015 widened: stability batch labels with leading or trailing whitespace, or
  differing only by letter case, are rejected (as BE subject IDs already were).
- `/verify` measures coverage on `src/cmc_stats` (a directory) instead of the `cmc_stats`
  package, so `ui.py`, run by Streamlit's AppTest as `__main__`, is counted.
- `test_dissolution_golden` now cites URS-DISS-002, so every test traces to a requirement.
- No existing constant changed.

### Fixed
- Nothing.

## 0.4.0 - 2026-10-28
No calculated result changes for existing inputs: this release adds new calculations only.

### Added
- Bioequivalence module `cmc_stats.core.be` for the 2x2 crossover (ICH M13A, 2024; FDA BE
  statistics guidance): `analyse_parameter`, `gmr_interval`, `tost_p_values`, `cv_within_pct`,
  `be_decision` and the `assess_bioequivalence` orchestrator.
  - Log-scale ANOVA with sequence, subject(sequence), period and treatment; type I table
    (df, SS, MS) reported per parameter.
  - T/R geometric mean ratio with 90% CI, both TOST p-values (alpha 0.05 derived from the
    90% CI) and within-subject CV; unequal sequence sizes accepted and counted.
  - Acceptance 80.00-125.00% after rounding the exact CI limits half up to 2 decimals
    (placeholder, pending confirmation against the target agency text); unrounded and rounded
    limits both reported; a note and a caveat in the conclusion when the rounded-CI decision
    and TOST disagree.
  - Cmax and AUC0-t always analysed; AUC0-inf optional (all records or none), decision-making
    by `BE_AUC0INF_DECISION_MAKING` (placeholder; FDA and EMA differ).
  - Replicate, parallel and reference-scaled analyses refused as not supported in v1.
- `cmc_stats.models`: `BeRecord`, `BeInput` and result models (`AnovaRow`,
  `BeParameterResult`, `BeResult`), with the traceability stamp. Input checks reject
  non-positive values, AUC0-inf below AUC0-t, missing periods, duplicate or inconsistent
  records, subjects under both sequences, empty sequences, residual df below 1, partial
  AUC0-inf, non-finite values and empty, padded or case-clashing subject IDs.
- Requirements URS-BE-004 to URS-BE-018 in `docs/URS.md`.
- Constants in `criteria.py`: `BE_ROUNDING_MODE` and `BE_AUC0INF_DECISION_MAKING`
  (placeholders pending agency text), `BE_MIN_SUBJECTS_PER_SEQUENCE` and `BE_MIN_RESIDUAL_DF`
  (project policy, not regulatory).
- Golden cases GOLD-BE-001 to 003 from independent R output on seeded dummy data
  (`tests/golden/r/be_gold.R`); published example pending.
- Unit, property-based (hypothesis) and requirement-linked BE tests.

### Changed
- QR least-squares helper moved from `core/stability.py` to the shared `core/_linear.py`;
  stability results are unchanged (GOLD-STAB-001..003 pass as before). Its rank-deficiency
  error message is now worded generically.
- `gxp-review` skill, checklist point 4: "odd subject counts per sequence" replaced by
  "subjects missing a period", because unbalanced sequences are valid.
- No existing constant or result changed.

### Fixed
- Nothing.

## 0.3.0 - 2026-10-28
No calculated result changes for existing inputs: this release adds new calculations only.

### Added
- Stability shelf-life module `cmc_stats.core.stability` (ICH Q1E, 2003, Appendices A and B):
  `fit_batches`, `poolability`, `select_model`, `lower_bound`, `crossing_time`,
  `extrapolation_cap`, `propose_shelf_life` and the `estimate_shelf_life` orchestrator.
  - Poolability by ANCOVA at 0.25: slopes on the full model's error, then intercepts on the
    common-slope model's error (sequential ANCOVA).
  - One-sided 95% lower bound of the mean; earliest crossing of the lower limit found in closed
    form at full precision; worst batch governs; ties are named in a note.
  - Separate-slopes model uses each batch's own regression error (ICH Q1E Appendix B.1 per
    batch) - provisional, pending confirmation against the Q1E text.
  - ICH Q1E Appendix A cap min(2X, X + 12) for the "no significant change at accelerated,
    statistical analysis performed" branch only; X is the shortest batch coverage.
  - Proposed shelf-life rounded down to whole months; v1 supports decreasing attributes only.
- `cmc_stats.models`: `StabilityBatch`, `StabilityInput` and result models (`BatchFit`,
  `PoolabilityTest`, `PoolabilityResult`, `BatchShelfLife`, `ExtrapolationCap`,
  `StabilityResult`), with the traceability stamp.
- Requirements URS-STAB-005 to URS-STAB-018 in `docs/URS.md`.
- Constants in `criteria.py`: `STABILITY_PRIMARY_BATCHES` (ICH Q1A(R2), Selection of Batches;
  section numbers pending confirmation) and `STABILITY_MIN_BATCHES`,
  `STABILITY_MIN_POINTS_PER_BATCH`, `STABILITY_MIN_DISTINCT_TIMES` (project policy, not
  regulatory).
- Golden cases GOLD-STAB-001 to 003 from independent R output (`tests/golden/r/stability_gold.R`),
  cross-checked against statsmodels; published example pending.
- Unit, property-based (hypothesis) and requirement-linked stability tests.

### Changed
- `ich-stats-rules` skill: records the sequential intercept test and the provisional
  separate-slopes error term (user decisions, 2026-10-27).
- No existing constant or result changed.

### Fixed
- Nothing.

## 0.2.0 - 2026-10-26
No calculated result changes for existing inputs: this release adds new calculations only.

### Added
- Dissolution similarity module `cmc_stats.core.dissolution` (FDA IR dissolution guidance,
  1997): `f1`, `f2`, `f1_within_limit`, `truncate_at_85`, `unit_cv_pct`, `check_cv`,
  `is_rapidly_dissolving`, `bootstrap_f2` and the `compare_profiles` orchestrator.
- Percentile bootstrap f2 with a required seed and resample count, both recorded in the result
  (Shah et al., Pharm Res 1998 - provisional, pending agency text).
- `cmc_stats.models`: pydantic input models (`DissolutionProfile`, `DissolutionInput`,
  `BootstrapSettings`) and result models, plus a `ResultMetadata` stamp with disclaimer, app
  version, guideline version, SHA-256 input hash and timestamp.
- Requirements URS-DISS-004 to URS-DISS-009 in `docs/URS.md`.
- Constants in `criteria.py`: `CV_EARLY_MAX_TIME_MIN`, `RAPID_DISSOLUTION_TIME_MIN`,
  `F1_SIMILAR_MAX` (FDA 1997), `BOOTSTRAP_CI_LEVEL` (Shah 1998, provisional) and
  `BOOTSTRAP_MIN_RESAMPLES` (project policy, not regulatory).
- Unit, property-based (hypothesis) and requirement-linked tests; GOLD-DISS-001 now runs.

### Changed
- No existing constant or result changed.

### Fixed
- Nothing.

## 0.1.0 - project start
### Added
- Project skeleton, regulatory constants in `criteria.py`, starter tests and Claude Code skills.
