# User requirements (URS)

Each requirement has an ID, a testable statement and its source. Tests reference these IDs.

| ID | Requirement | Source |
|---|---|---|
| URS-GEN-001 | Every result states that the tool is for education and decision support, not GxP use. | Project policy |
| URS-GEN-002 | Every result records the app version, guideline version, input hash and timestamp. | ALCOA+ data integrity |
| URS-GEN-003 | When data come from an uploaded file, the result metadata records the file name, size in bytes and SHA-256 of the raw bytes; the field is empty when there is no file. | ALCOA+ data integrity; user decision 2026-10-28 |
| URS-GEN-004 | A sample-data pack in sample_data/ uses the exact UI template CSV format, is regenerated reproducibly from committed seeded scripts, and lists each file's settings and expected result; a test runs every file through the UI parsing and core path and checks those expectations. | Project policy (dummy data only); user requirement 2026-10-28 |
| URS-STAB-001 | Fit a least-squares line of attribute against time for each batch. | ICH Q1E |
| URS-STAB-002 | Test equality of slopes, then intercepts, at significance 0.25 and choose the model. | ICH Q1E |
| URS-STAB-003 | Report the time where the one-sided 95% bound of the mean meets the limit. When slopes differ, each batch's bound uses its own intercept and slope with the pooled mean square error of the full model (individual intercepts and slopes, df = N - 2k). | ICH Q1E (2003) 2.6, p. 7; separate slopes: ICH Q1E (2003) Appendix B.2.2.1 and B.2.1, p. 10 |
| URS-STAB-004 | Cap the proposed shelf-life by the Appendix A extrapolation rule. | ICH Q1E (2003) 2.4.1.2, p. 4, and Appendix A, p. 8 |
| URS-STAB-005 | Report the model chosen, slope and intercept F, df and p (intercept not tested when slopes differ), residual df and t value of the model used for each bound (full model, df = N - 2k, when slopes differ), crossing time and the proposed shelf-life rounded down to whole months. | ICH Q1E; separate slopes: ICH Q1E (2003) Appendix B.2.2.1 and B.2.1, p. 10 |
| URS-STAB-006 | Accept only an attribute expected to decrease, with a lower limit; refuse "increase" and "either" as not supported in v1. | Project scope (v1) |
| URS-STAB-007 | Apply the extrapolation cap only when statistical analysis of the long-term data was performed (required true/false, no default); refuse "not performed". Storage condition and significant change are covered by URS-STAB-022 and 023. | ICH Q1E (2003) 2.4.1.2, p. 4, and Appendix A, p. 8 |
| URS-STAB-008 | Take X, the period covered by long-term data, as the shortest of the batches' last time points; report X and the cap min(2X, X + 12). | ICH Q1E (2003) Appendix A, p. 8 ("X = Period covered by long-term data"); user decision 2026-10-27; known limitation (URS-STAB-021) |
| URS-STAB-009 | Reject input with fewer than 2 batches. | Project policy (minimum for the poolability tests) |
| URS-STAB-010 | Reject a batch with fewer than 3 observations, naming the batch. | Project policy (at least 1 residual df per batch) |
| URS-STAB-011 | Reject a batch with fewer than 2 distinct time points, naming the batch. | Project policy (slope must be estimable) |
| URS-STAB-012 | Reject a batch whose time and value lists differ in length, naming the batch. | Project policy |
| URS-STAB-013 | Reject negative time points, naming the batch. | Project policy |
| URS-STAB-014 | Reject non-finite values (NaN, infinity) in times, values or the limit. | Project policy |
| URS-STAB-015 | Reject empty or duplicate batch labels, labels with leading or trailing whitespace and labels that differ only by letter case, naming them. | Project policy |
| URS-STAB-016 | If the bound is at or below the limit at time 0, report a shelf-life of 0 and that no shelf-life is supported; if the bound never meets the limit, the extrapolation cap sets the shelf-life and a note says so. | Project policy |
| URS-STAB-017 | With fewer than 3 batches, add a warning (not an error) to the result; the calculation still runs. | ICH Q1A(R2) (2003), Selection of Batches: 2.1.3 (drug substance), p. 2, and 2.2.3 (drug product), p. 6 |
| URS-STAB-018 | Reject negative values (naming the batch) and a negative lower limit; values above 100% are kept as entered. | Project policy (reject bad input loudly) |
| URS-STAB-019 | A poolability test pools only when p > 0.25; at p <= 0.25 equality is rejected (slopes, then intercepts). | ICH Q1A(R2) 2.1.9 and 2.2.9 ("more than 0.25"): 2.1.9, p. 5; 2.2.9 (begins p. 12; quoted sentence p. 13); ICH Q1 Step 2 draft (2025) Annex 2 A2-1.2-1, p. A2-6; user decision 2026-10-29 (Shashank) |
| URS-STAB-020 | Every stability result states, as a known-limitation note, that the extrapolation cap covers only the room-temperature, no-significant-change, statistical-analysis-performed branch; the refrigerated branch (1.5X, not exceeding X + 6) and other Appendix A branches are not supported (refused at input by URS-STAB-022 and 023). | ICH Q1E (2003) 2.4.1.2, p. 4, 2.5.1.1, p. 6, and Appendix A, p. 8; known limitation, decided by Shashank 2026-10-29 (PC-STAB-04) |
| URS-STAB-021 | Every stability result states, as a known-limitation note, that X is taken as the shortest batch coverage (a conservative reading). | ICH Q1E (2003) Appendix A, p. 8 ("X = Period covered by long-term data"); known limitation, decided by Shashank 2026-10-29 (PC-STAB-05) |
| URS-STAB-022 | Require the storage condition (room temperature, refrigerated or freezer; no default). Refuse refrigerated and freezer as not supported in v1. | ICH Q1E (2003) 2.4.1.2, p. 4, 2.5.1.1, p. 6, and Appendix A, p. 8; user decision 2026-10-29 (Shashank) |
| URS-STAB-023 | Require "significant change at accelerated condition" (true/false, no default). Refuse true as not supported in v1. | ICH Q1E (2003) Appendix A, p. 8; user decision 2026-10-29 (Shashank) |
| URS-STAB-024 | Every stability result states, as a known-limitation note, that the rules follow ICH Q1A(R2) and Q1E (Step 4, 2003), that the consolidated ICH Q1 is a Step 2 draft (11 April 2025) and not applied, and that the rules are re-checked when ICH Q1 reaches Step 4 or is adopted by FDA. | Known limitation, decided by Shashank 2026-10-29 (PC-STAB-06) |
| URS-DISS-001 | Use only time points up to the first where both products reach 85%. | FDA IR dissolution guidance (1997) |
| URS-DISS-002 | Calculate f1 and f2 from mean profiles. | FDA IR dissolution guidance (1997) |
| URS-DISS-003 | Check CV limits (20% early, 10% later) and switch to bootstrap f2 when they fail. | FDA IR dissolution guidance (1997) |
| URS-DISS-004 | Reject input with fewer than 12 units for either product, naming the product and its unit count. | FDA IR dissolution guidance (1997) |
| URS-DISS-005 | Reject input when reference and test time points differ in count or in any value, listing the mismatches. | FDA IR dissolution guidance (1997) |
| URS-DISS-006 | When both products reach 85% within 15 minutes, flag that profile comparison is usually unnecessary and give no f2 verdict. | FDA IR dissolution guidance (1997) |
| URS-DISS-007 | Bootstrap f2 resamples units with replacement from a caller-supplied seed and resample count, reports the percentile 90% interval and records both; similar if the 5th percentile is at least 50. | Shah et al., Pharm Res 1998 - provisional, pending agency text |
| URS-DISS-008 | Report f1 against the companion limit of 15; f2 alone decides similarity. | FDA IR dissolution guidance (1997) |
| URS-DISS-009 | Reject ragged unit rows, non-finite or negative values, and time points that are not strictly increasing and positive. | Project policy (reject bad input loudly) |
| URS-BE-001 | Accept bioequivalence when the 90% CI of the GMR lies within 80.00-125.00%. | ICH M13A |
| URS-BE-002 | Analyse log values with sequence, subject(sequence), period and treatment terms. | ICH M13A; FDA BE statistics guidance |
| URS-BE-003 | Report within-subject CV and both TOST p-values. | FDA BE statistics guidance |
| URS-BE-004 | Refuse replicate designs, whether declared or detected from a sequence longer than two treatments or a period other than 1 or 2, as not supported in v1. | Project scope (v1); ich-stats-rules |
| URS-BE-005 | Refuse reference-scaled limits as not supported in v1. | Project scope (v1); ich-stats-rules |
| URS-BE-006 | Refuse parallel designs as not supported in v1. | Project scope (v1); ich-stats-rules |
| URS-BE-007 | Reject zero or negative PK values, naming the subject, period and parameter. | Project policy (log transform undefined) |
| URS-BE-008 | Reject a subject missing a period, naming the subject. | User requirement 2026-10-28 |
| URS-BE-009 | Reject duplicate subject-period records. | Project policy |
| URS-BE-010 | Reject a sequence other than TR or RT, or a treatment that does not match the sequence (TR: period 1 T, period 2 R; RT the reverse), naming the subject. | Project policy |
| URS-BE-011 | Reject a subject listed under both sequences. | Project policy |
| URS-BE-012 | Require at least 1 subject per sequence; accept unequal sequence sizes and report n per sequence. | Project policy; user decision 2026-10-28 |
| URS-BE-013 | Reject input whose residual degrees of freedom (n - 2 for a complete 2x2) would be below 1, giving the subject count, the resulting df and that at least 3 subjects are needed. | Project policy |
| URS-BE-014 | AUC0-inf is optional but must be supplied for every record or none (a partial set is rejected, listing the missing records); when supplied it is analysed, and whether it counts towards the BE decision is set by BE_AUC0INF_DECISION_MAKING. | User decision 2026-10-28; agencies differ on whether AUC0-inf is decision-making (FDA vs EMA) - pending confirmation against the target agency text |
| URS-BE-015 | Reject non-finite values, empty subject IDs, IDs with leading or trailing whitespace and IDs that differ only by letter case. | Project policy |
| URS-BE-016 | Round the CI limits half up to BE_ROUND_DECIMALS before comparing them with the acceptance range; report both unrounded and rounded limits. | ich-stats-rules; rounding mode pending confirmation against the target agency text |
| URS-BE-017 | For each parameter report the type I ANOVA table (df, SS, MS), n per sequence, residual df, MSE, log difference and SE, t value, point estimate and CI (full precision and rounded) and pass/fail; bioequivalent overall only if every decision-making parameter passes. When the rounded-CI decision and TOST disagree, say so in the result notes and the conclusion. | ICH M13A; FDA BE statistics guidance |
| URS-BE-018 | Reject AUC0-inf smaller than AUC0-t, naming the subject and period; equal values are accepted. | Project policy (AUC0-inf = AUC0-t + extrapolated area) |
| URS-API-001 | GET /health returns status "ok", the app version and the disclaimer. | Project policy |
| URS-API-002 | POST /dissolution takes DissolutionInput and optional BootstrapSettings and returns DissolutionResult exactly as compare_profiles produces it. | Project policy |
| URS-API-003 | POST /stability takes StabilityInput and returns StabilityResult exactly as estimate_shelf_life produces it. | Project policy |
| URS-API-004 | POST /be takes BeInput and returns BeResult exactly as assess_bioequivalence produces it. | Project policy |
| URS-API-005 | Input that fails model validation, including NaN or infinity, returns 422 with the validation messages. | Project policy (reject bad input loudly) |
| URS-API-006 | A ValueError raised by a core function returns 422 with its message, never 500; a result that fails its own model inside an endpoint (a defect in the tool) returns 500, never a 422 that blames the input. | Project policy |
| URS-UI-001 | Each tab offers a downloadable CSV template with dummy data that parses into a valid input. | Project policy |
| URS-UI-002 | Reject a CSV with missing required columns or unknown columns, naming them. | Project policy |
| URS-UI-003 | Reject blank cells, naming the row and column. | Project policy |
| URS-UI-004 | Reject non-numeric or non-integer text in numeric columns (including NaN, inf and decimal commas), naming the row and column. | Project policy |
| URS-UI-005 | Reject an empty file, a header-only file and a file that is not UTF-8. | Project policy |
| URS-UI-006 | Dissolution: every unit of a product must have every time point exactly once; reject missing or duplicate cells, naming the unit and time. | Project policy; FDA IR dissolution guidance (1997) (identical time points) |
| URS-UI-007 | Keep rows in file order and group batches, units and subjects in order of first appearance; never sort, drop or average. | ALCOA+ (original data) |
| URS-UI-008 | Settings not in the CSV must be chosen explicitly before Run is enabled (stability attribute, unit, direction, limit, storage condition and Appendix A conditions; BE design and limits); dissolution bootstrap seed and resample count are given together or not at all. No defaults. | Project policy (no invented seed or settings) |
| URS-UI-009 | Show parsing, validation and core errors verbatim, with no result displayed. | Project policy |
| URS-UI-010 | Show the disclaimer on every tab. | URS-GEN-001 |
| URS-UI-011 | Show every note, warning or method note containing "pending confirmation", "provisional" or "known limitation" in a warning box above the results. | Project policy; docs/RELEASE-1.0.0.md, Definition of 1.0.0 (known limitations) |
| URS-UI-012 | Results tables keep full precision; values are rounded only by display formatting. | CLAUDE.md (round only for display) |
| URS-UI-013 | Charts are Plotly line or bar only: dissolution mean profiles; stability batch data, fitted mean line, 95% lower bound and limit; BE point estimate bars with 90% CI error bars and 80/125% reference lines. | Project policy |
| URS-UI-014 | When the template's dummy data are used instead of an upload, show the warning "Result from template dummy data, not your data" with the result, and record the template file name as the source file. | ALCOA+ (attributable); user requirement 2026-10-28 |
