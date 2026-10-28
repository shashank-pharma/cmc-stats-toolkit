# User requirements (URS)

Each requirement has an ID, a testable statement and its source. Tests reference these IDs.

| ID | Requirement | Source |
|---|---|---|
| URS-GEN-001 | Every result states that the tool is for education and decision support, not GxP use. | Project policy |
| URS-GEN-002 | Every result records the app version, guideline version, input hash and timestamp. | ALCOA+ data integrity |
| URS-STAB-001 | Fit a least-squares line of attribute against time for each batch. | ICH Q1E |
| URS-STAB-002 | Test equality of slopes, then intercepts, at significance 0.25 and choose the model. | ICH Q1E |
| URS-STAB-003 | Report the time where the one-sided 95% bound of the mean meets the limit. | ICH Q1E |
| URS-STAB-004 | Cap the proposed shelf-life by the Appendix A extrapolation rule. | ICH Q1E Appendix A |
| URS-STAB-005 | Report the model chosen, slope and intercept F, df and p (intercept not tested when slopes differ), residual df, t value, crossing time and the proposed shelf-life rounded down to whole months. | ICH Q1E |
| URS-STAB-006 | Accept only an attribute expected to decrease, with a lower limit; refuse "increase" and "either" as not supported in v1. | Project scope (v1) |
| URS-STAB-007 | Apply the extrapolation cap only when there is no significant change at accelerated and statistical analysis was performed; refuse every other combination. | ICH Q1E Appendix A |
| URS-STAB-008 | Take X, the period covered by long-term data, as the shortest of the batches' last time points; report X and the cap min(2X, X + 12). | ICH Q1E Appendix A; user decision 2026-10-27 |
| URS-STAB-009 | Reject input with fewer than 2 batches. | Project policy (minimum for the poolability tests) |
| URS-STAB-010 | Reject a batch with fewer than 3 observations, naming the batch. | Project policy (at least 1 residual df per batch) |
| URS-STAB-011 | Reject a batch with fewer than 2 distinct time points, naming the batch. | Project policy (slope must be estimable) |
| URS-STAB-012 | Reject a batch whose time and value lists differ in length, naming the batch. | Project policy |
| URS-STAB-013 | Reject negative time points, naming the batch. | Project policy |
| URS-STAB-014 | Reject non-finite values (NaN, infinity) in times, values or the limit. | Project policy |
| URS-STAB-015 | Reject empty or duplicate batch labels. | Project policy |
| URS-STAB-016 | If the bound is at or below the limit at time 0, report a shelf-life of 0 and that no shelf-life is supported; if the bound never meets the limit, the extrapolation cap sets the shelf-life and a note says so. | Project policy |
| URS-STAB-017 | With fewer than 3 batches, add a warning (not an error) to the result; the calculation still runs. | ICH Q1A(R2), Selection of Batches (drug substance and drug product); section numbers pending confirmation |
| URS-STAB-018 | Reject negative values (naming the batch) and a negative lower limit; values above 100% are kept as entered. | Project policy (reject bad input loudly) |
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
