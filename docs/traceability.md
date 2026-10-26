# Traceability matrix

Updated by the `/validation-docs` skill. Every requirement needs at least one test.

Test IDs: `GOLD-*` are golden cases in `tests/golden/data/`; `test_<module>::<name>` are tests in
`tests/`. Last /verify for every row below: **PASS 2026-10-26, v0.2.0** (ruff format, ruff
check, mypy strict, pytest 48 passed, coverage 98.51%).

| Requirement | Implemented in | Tests | Last /verify |
|---|---|---|---|
| URS-GEN-001 | models.DISCLAIMER, models.ResultMetadata | test_dissolution::test_result_carries_disclaimer_and_traceability_stamp | PASS 2026-10-26 |
| URS-GEN-002 | criteria.GUIDELINE_VERSIONS, models.make_metadata, models.ResultMetadata | test_criteria::test_every_area_has_a_guideline_version; test_dissolution::test_result_carries_disclaimer_and_traceability_stamp, test_input_hash_tracks_inputs, test_result_keeps_inputs_and_full_precision_means | PASS 2026-10-26 |
| URS-STAB-001 | | | **No test: not built** |
| URS-STAB-002 | | | **No test: not built** |
| URS-STAB-003 | | | **No test: not built** |
| URS-STAB-004 | | | **No test: not built** |
| URS-DISS-001 | core.dissolution.truncate_at_85, compare_profiles | test_dissolution::test_truncation_keeps_points_through_first_where_both_reach_85, test_truncation_waits_for_both_products, test_truncation_at_first_point, test_truncation_keeps_all_when_85_never_reached, test_compare_profiles_mean_f2_path | PASS 2026-10-26 |
| URS-DISS-002 | core.dissolution.f1, f2 | GOLD-DISS-001 (hand calculation; published example pending); test_dissolution::test_identical_profiles_give_f2_100_and_f1_0, test_uniform_10_point_difference_matches_analytic_f2, test_f1_f2_reject_unequal_lengths, test_f1_rejects_zero_reference_sum, test_f1_f2_reject_empty_profiles, test_f2_is_symmetric_and_at_most_100, test_f2_decreases_as_uniform_offset_grows, test_f1_is_non_negative, test_compare_profiles_mean_f2_path | PASS 2026-10-26 |
| URS-DISS-003 | criteria.CV_EARLY_MAX_TIME_MIN; core.dissolution.unit_cv_pct, check_cv, compare_profiles | test_criteria::test_dissolution_time_constants_match_15_minutes; test_dissolution::test_unit_cv_uses_sample_sd, test_unit_cv_rejects_zero_mean, test_cv_limit_is_20_up_to_15_minutes_then_10, test_cv_just_over_limit_fails_and_just_under_passes, test_compare_profiles_mean_f2_path, test_compare_profiles_requires_bootstrap_settings_when_cv_fails | PASS 2026-10-26 |
| URS-DISS-004 | models.DissolutionProfile._shape | test_dissolution::test_eleven_reference_units_rejected, test_eleven_test_units_rejected, test_twelve_units_each_accepted | PASS 2026-10-26 |
| URS-DISS-005 | models.DissolutionInput._same_time_points | test_dissolution::test_time_point_count_mismatch_rejected, test_time_point_value_mismatch_rejected, test_identical_time_points_accepted | PASS 2026-10-26 |
| URS-DISS-006 | criteria.RAPID_DISSOLUTION_TIME_MIN; core.dissolution.is_rapidly_dissolving, compare_profiles | test_criteria::test_dissolution_time_constants_match_15_minutes; test_dissolution::test_rapid_dissolution_flagged_without_f2_verdict, test_one_product_reaching_85_after_15_min_is_not_rapid | PASS 2026-10-26 |
| URS-DISS-007 | criteria.BOOTSTRAP_CI_LEVEL, BOOTSTRAP_MIN_RESAMPLES; models.BootstrapSettings, BootstrapF2Result; core.dissolution.bootstrap_f2, compare_profiles | test_criteria::test_bootstrap_interval_is_90_percent; test_dissolution::test_bootstrap_settings_require_seed_and_count, test_compare_profiles_requires_bootstrap_settings_when_cv_fails, test_bootstrap_is_reproducible_and_records_seed, test_bootstrap_different_seed_gives_different_draws, test_bootstrap_of_identical_units_is_100 (golden case vs R bootf2 pending) | PASS 2026-10-26 |
| URS-DISS-008 | criteria.F1_SIMILAR_MAX; core.dissolution.f1_within_limit | test_criteria::test_f1_companion_limit; test_dissolution::test_f1_limit_is_inclusive_at_15, test_compare_profiles_mean_f2_path | PASS 2026-10-26 |
| URS-DISS-009 | models.DissolutionProfile._times_positive_increasing, _values_non_negative, _shape; model config allow_inf_nan=False | test_dissolution::test_bad_profile_rejected (7 cases), test_values_above_100_are_kept_not_clipped | PASS 2026-10-26 |
| URS-BE-001 | criteria.BE_LOWER_PCT, BE_UPPER_PCT | test_criteria::test_be_range_is_symmetric_on_log_scale | PASS 2026-10-26 |
| URS-BE-002 | | | **No test: not built** |
| URS-BE-003 | | | **No test: not built** |
