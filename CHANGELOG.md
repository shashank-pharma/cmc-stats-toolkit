# Changelog

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
