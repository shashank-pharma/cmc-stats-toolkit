# Changelog

## 0.9.1 - 2026-11-06
No calculated result changes; no code changes. Patch bump: documentation only. The app
version stamped in `ResultMetadata` reads 0.9.1; no calculated value, guideline stamp or
input hash changes. `/gxp-review` ran on v0.9.0 with all 8 checks clear (reported by
Shashank, 2026-11-06). Not 1.0.0: the 1.0.0 release steps have not yet been done.

### Changed (validation documents, 2026-11-06)
- `/validation-docs` run. `/verify` PASS on v0.9.1 (397 tests, 10 golden, coverage 99.25%).
  Every row of `docs/traceability.md` now shows that result. All 87 URS IDs have a row with
  the implementing function(s) and at least one test. No requirement lacks a test and no
  test lacks a requirement. The matrix now names the dissolution golden runner
  (`test_golden_dissolution::test_dissolution_golden`, GOLD-DISS-001, URS-DISS-002), as it
  already did for the stability and BE runners. No URS requirement was added or changed.

### Changed (decision by Shashank, 2026-11-04)
- The PDF report (`src/cmc_stats/report.py`, ReportLab) is not part of 1.0.0 and is planned
  for v1.1. It was described in `CLAUDE.md` but never built. `CLAUDE.md`, the `gxp-review`
  skill and `docs/RELEASE-1.0.0.md` ("Planned for v1.1") now say so. It is a planned feature,
  not a known limitation of the calculations. No URS requirement depended on it (URS-GEN-002
  and URS-GEN-003 are met by `models.ResultMetadata`).

## 0.9.0 - 2026-11-03
Behaviour changes: `BeInput` now refuses fewer than 12 evaluable subjects (ICH M13A 2.2.3.1,
p. 12; URS-BE-019). 0.8.0 accepted 3 or more, so BE input or `/be` requests with 3 to 11
subjects are now rejected. The BE guideline stamp changes from "ICH M13A (Step 4, 2024)" to
"ICH M13A (Step 4, 2024) + FDA Statistical Approaches to Establishing Bioequivalence (May
2026)". The BE result notes are replaced by known-limitation notes. The downloadable BE
template gains 4 dummy subjects (S09-S12, now 12), so its file hash changes. Minor bump under
the pre-1.0 policy. It is not 1.0.0: every register item is now closed, but `/gxp-review` and
`/validation-docs` have not been run. No calculated result changes. The CI, TOST, CVw,
rounding and AUC0-inf logic is untouched, and no golden expected value was edited
(GOLD-BE-001..003 and both BE sample files already had 12 or more subjects).

### Changed (decisions by Shashank, 2026-11-03; quotes confirmed by the user)
- PC-BE-01 confirmed: two decimals per FDA, Statistical Approaches to Establishing
  Bioequivalence (May 2026), I.B footnote 6, p. 3 (URS-BE-016). EMA 4.1.8 is a note only.
- PC-BE-02 confirmed: AUC0-inf stays decision-making per FDA (May 2026) II.C.2, p. 13
  (URS-BE-014). ICH M13A 2.2.2.2 and EMA 4.1.8 differ (notes only).
- PC-BE-03 confirmed: ICH M13A 2.2.3.1, 2.2.3.2 and 2.2.4, and FDA II.C.1.a, cited in
  `criteria.py`, `core/be.py` and URS-BE-001..003. The CVw formula is cited to EMA 4.1.10,
  p. 17/27 (highly variable drug context), the only source that gives it.

### Added
- URS-BE-019: fewer than 12 evaluable subjects is refused, giving the count, the minimum and
  the source (`criteria.BE_MIN_EVALUABLE_SUBJECTS`). The residual-df check (URS-BE-013) runs
  first and still reports 1 or 2 subjects as a df problem.

### Known limitations (decided by Shashank, 2026-11-03)
- PC-BE-01: no guidance states the CI rounding mode, so round half up is this tool's choice
  (URS-BE-020).
- PC-BE-02: the FDA ANDA PK-endpoints guidance cited in FDA footnote 6 was not checked
  (URS-BE-021).
- PC-BE-04: BE golden cases are base R output on seeded dummy data. A published example
  (Schutz et al. 2014) is planned for v1.1 (URS-BE-022).
Every affected BE result carries these as notes, shown in the warning box (URS-UI-011).

### Still open for 1.0.0
No register items. `/gxp-review` and `/validation-docs` still have to run.

## 0.8.0 - 2026-10-29
Behaviour changes: the stability guideline stamp changes from "ICH Q1E (Step 4, 2003)" to
"ICH Q1A(R2) (Step 4, 6 February 2003) + ICH Q1E (Step 4, 6 February 2003)" (URS-STAB-026).
`DissolutionResult` has a new field `warnings` (also in the `/dissolution` API response);
minor bump under the pre-1.0 policy. No calculated result changes: f1, f2, bootstrap f2 and
shelf-life logic are untouched, and no golden expected value was edited (GOLD-DISS-001
regenerated from R with an empty diff).

### Changed
- PC-DISS-02 confirmed: f1/f2, 12 units and the 85% rule cite FDA 1997 section V.A,
  pp. 8-9; every "section V" citation in `core/dissolution.py` and `criteria.py` now reads
  V.A, and URS-DISS-001..006 and 008 cite V.A.
- PC-GEN-01 confirmed: target agency is US FDA with ICH as the harmonised base; EMA
  differences are notes only (URS-GEN-005, `criteria.TARGET_AGENCY`).
- New URS-DISS-010: fewer than 3 time points after the 85% cut-off adds a warning ("three to
  four or more dissolution time points"; subsection pending confirmation, PC-DISS-05).
- `ui_helpers.prominent_notes` now also reads dissolution warnings (URS-UI-011).
- PC-STAB-08 confirmed: ICH Q1A(R2) cover page "Current Step 4 version dated 6 February
  2003"; the stamp gives the full date (URS-STAB-026).
- PC-DISS-05 confirmed: the "three to four or more dissolution time points" quote is FDA 1997
  section V.A, p. 9 (URS-DISS-010). The warning no longer says "pending confirmation", so it
  is shown in its own warning box rather than promoted under URS-UI-011.

### Added
- `tests/golden/r/dissolution_gold.R` reproduces GOLD-DISS-001 from base R, and
  `tests/golden/r/merge_dissolution_gold.py` writes R's values into the JSON (empty diff on
  2026-10-29).

### Known limitations (decided by Shashank, 2026-10-29)
- PC-STAB-07: stability golden cases are base R output on dummy data; a published-example
  cross-check is planned for v1.1 (URS-STAB-025).
- PC-DISS-01: FDA 1997 does not describe bootstrap f2; V.B (pp. 9-10) names a multivariate
  model independent procedure for within-batch CV above 15%. Bootstrap f2 stays supplementary
  and provisional; the MSD method is not in v1 (URS-DISS-013).
- PC-DISS-03: the 20% CV limit "at the earlier time points (e.g., 15 minutes)" is read as
  t <= 15 min (URS-DISS-011).
- PC-DISS-04: GOLD-DISS-001 is cross-checked against base R
  (`tests/golden/r/dissolution_gold.R`) and there is no bootstrap golden case; a published
  example (Shah et al. 1998) is planned for v1.1 (URS-DISS-014).
- PC-DISS-06: f2 = 50 exactly (and a bootstrap lower bound of 50) is treated as similar,
  reading "f2 values greater than 50 (50-100)" as inclusive (URS-DISS-012).
Every affected result carries these as notes, shown in the warning box (URS-UI-011).

### Still open for 1.0.0
PC-BE-01..04.

## 0.7.0 - 2026-10-29
Behaviour change: `StabilityInput` has a new required field `storage_condition`
("room_temperature", "refrigerated" or "freezer", no default; URS-STAB-022). Stability input
or API requests without it, accepted by 0.6.0, are now rejected. Refrigerated and freezer
storage, and `significant_change_at_accelerated` true (URS-STAB-023), are refused as "not
supported in v1"; significant change was already refused in 0.6.0, but with a combined
Appendix A message. No calculated result changes: R reproduces GOLD-STAB-001..003 exactly;
their inputs gain `storage_condition: "room_temperature"` only, and the input hash of a
stability result changes because the inputs now include it.

Version: minor bump under the pre-1.0 policy (behaviour change, no calculated result
change); not 1.0.0 because PC-STAB-07, PC-DISS-01..04, PC-BE-01..04 and PC-GEN-01 are open.

### Changed
- PC-STAB-02 confirmed: the fewer-than-3-batches warning, `criteria.STABILITY_PRIMARY_BATCHES`
  and URS-STAB-017 cite ICH Q1A(R2) 2.1.3 (p. 2) and 2.2.3 (p. 6); "pending confirmation"
  removed. The warning is still shown in a warning box, but is no longer promoted as pending
  (URS-UI-011; test renamed to test_prominent_notes_skip_confirmed_stability_notes).
  Register row records the confirmed 2.1.3 and 2.2.3 sentences, and 2.1.9 / 2.2.9
  ("rejection of more than 0.25") as support for URS-STAB-019.
- PC-STAB-03 confirmed: `criteria.POOLABILITY_ALPHA` comment now cites ICH Q1E Appendix
  B.2.2.1, p. 10 (was "section 2.3 and Appendix B").
- PC-STAB-04 confirmed: `SHELF_LIFE_CONFIDENCE` and the extrapolation constants, the
  `lower_bound` and `extrapolation_cap` docstrings and URS-STAB-003, 004, 007 and 008 cite
  ICH Q1E 2.6 (p. 7), 2.4.1.2 (p. 4) and Appendix A (p. 8).
- URS-UI-011: notes containing "known limitation" are also shown in the warning box.

### Known limitations (decided by Shashank, 2026-10-29)
- Appendix A cap: room temperature, no significant change at accelerated, statistical
  analysis performed only. The refrigerated branch (1.5X, not exceeding X + 6 months, Q1E
  2.5.1.1) and other branches are not supported, and are refused at input (PC-STAB-04,
  URS-STAB-020, URS-STAB-022, URS-STAB-023).
- X is taken as the shortest batch coverage; Q1E defines X only as "period covered by
  long-term data" (PC-STAB-05, URS-STAB-021).
- Rules follow ICH Q1A(R2) and Q1E (Step 4, 2003); the consolidated ICH Q1 is a Step 2 draft
  (11 April 2025) and is not applied. Re-check on Step 4 publication or FDA adoption
  (PC-STAB-06, URS-STAB-024).
Every stability result now carries all three as notes, shown in the warning box.

### Added
- test_ui_app::test_two_batch_stability_run_shows_q1a_warning (URS-UI-011, URS-STAB-017):
  the fewer-than-3-batches warning reaches the screen.
- URS-STAB-020 and URS-STAB-021 with tests; test_ui_helpers::
  test_prominent_notes_include_known_limitations and test_ui_app::
  test_stability_run_shows_known_limitations_in_warning_box.
- URS-STAB-022 (`storage_condition`, UI selectbox with no default), URS-STAB-023 (own refusal
  for significant change) and URS-STAB-024, with tests in test_stability, test_api and
  test_ui_app.
- URS-STAB-019 and the register cite Q1A(R2) 2.2.9 as "begins p. 12; quoted sentence p. 13".

## 0.6.0 - 2026-10-29
Calculated result changed: when batch slopes differ (separate-slopes model), each batch's
one-sided 95% bound now uses its own intercept and slope with the pooled mean square error of
the full ANCOVA model (df = N - 2k), as ICH Q1E (2003) Appendix B.2.2.1, p. 10 requires
(PC-STAB-01, confirmed 2026-10-29). Up to 0.5.0 each batch used its own regression error
(df = n - 2). GOLD-STAB-003 crossing 24.62037974 -> 24.33389941 months (B001 32.84197599 ->
33.44940849, B002 32.50987285 -> 33.32061198; df 5 -> 15, t 2.01504837 -> 1.75305036);
proposed shelf-life unchanged (24 months), B003 still governs. Pooled and common-slope results
are unchanged (GOLD-STAB-001 and 002 reproduced exactly by R).

Behaviour change: a poolability p-value of exactly 0.25 now rejects equality (only p > 0.25
pools; URS-STAB-019, user decision 2026-10-29). In 0.5.0 p = 0.25 pooled. No golden case sits
on the boundary.

### Added
- URS-STAB-019 (p = 0.25 boundary rule) with tests
  test_select_model_rejects_equality_at_p_0_25 and
  test_poolability_tests_intercepts_only_above_0_25.

### Changed
- `core.stability`: separate-slopes lines take the full model's residual error and df;
  `select_model` and `poolability` pool only when p > 0.25. `SEPARATE_MODEL_NOTE` now cites
  Q1E Appendix B.2.2.1 and is no longer marked provisional, so the UI no longer shows it in
  the warning box (URS-UI-011).
- URS-STAB-003 and URS-STAB-005 cite Q1E Appendix B.2.2.1 and B.2.1, p. 10.
- `tests/golden/r/stability_gold.R`: separate lines predicted from `lm(y ~ batch * time)`;
  boundary rule p > 0.25. GOLD-STAB-003 regenerated from R 4.6.1 (expected values not
  edited by hand); `sample_data/expected.json` rebuilt with `build_expected.py`.
- Tests replaced: test_separate_bound_uses_each_batch_own_fit ->
  test_separate_bound_uses_full_model_pooled_mse; test_separate_model_uses_own_df_and_t ->
  test_separate_model_uses_full_model_df_and_t;
  test_select_model_treats_p_equal_to_0_25_as_poolable -> test_select_model_rejects_equality_at_p_0_25;
  test_prominent_notes_pick_provisional_and_pending ->
  test_prominent_notes_pick_pending_and_skip_confirmed_separate_note.
- ich-stats-rules skill, `docs/traceability.md`, `sample_data/README.md` and
  `docs/RELEASE-1.0.0.md` (PC-STAB-01 confirmed) updated to match.
- No constant in `criteria.py` changed.

### Fixed
- The separate-slopes bound now follows ICH Q1E Appendix B.2.2.1 (see above).

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
