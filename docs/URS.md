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
| URS-BE-001 | Accept bioequivalence when the 90% CI of the GMR lies within 80.00-125.00%. | ICH M13A |
| URS-BE-002 | Analyse log values with sequence, subject(sequence), period and treatment terms. | ICH M13A; FDA BE statistics guidance |
| URS-BE-003 | Report within-subject CV and both TOST p-values. | FDA BE statistics guidance |
