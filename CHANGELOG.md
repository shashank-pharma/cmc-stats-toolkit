# Changelog

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
