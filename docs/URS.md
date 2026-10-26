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
