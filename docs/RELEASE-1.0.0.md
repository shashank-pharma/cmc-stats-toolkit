# Release 1.0.0: confirmation register

Version 1.0.0 is reserved for when every item below is closed (CHANGELOG 0.5.0, "Versioning").
This register collects every pending confirmation, provisional method and placeholder in the
project, so none is forgotten and each can be closed against its source.

Built on 2026-10-29 at v0.5.0 by searching every tracked file (`git ls-files`, excluding
`uv.lock`, the sample CSVs and the CHANGELOG history) for "pending confirmation", "pending
agency", "provisional", "placeholder", "confirm for the target agency" and "published example
pending". A second search looked for section citations and interpretations that are just as
unconfirmed but carry none of those words; those rows are marked **(unmarked)**. "Where it
appears" names files and symbols rather than line numbers, which drift.

## Register

| ID | Where it appears | What must be confirmed | Source document needed | Status |
|---|---|---|---|---|
| PC-STAB-01 | `ich-stats-rules` skill §1 rule 2; `core/stability.py` (`SEPARATE_MODEL_NOTE`, `lower_bound`); URS-STAB-003, URS-STAB-005; `docs/traceability.md`; GOLD-STAB-003 and `tests/golden/r/stability_gold.R`; `tests/test_stability.py`; `sample_data/README.md` | When batch slopes differ, does each batch's bound use its own regression error (Appendix B.1 single-batch approach per batch, df = n − 2) or the pooled error of the full ANCOVA model? This changes the crossing for GOLD-STAB-003 (24.62 vs 24.33 months). | ICH Q1E (2003), Appendix B | **confirmed** 2026-10-29: pooled error. ICH Q1E, Step 4 (6 February 2003), Appendix B.2.2.1 (same wording in B.2.1), printed p. 10: "using individual intercepts and individual slopes and the pooled mean square error calculated from all batches"; same in ICH Q1 Step 2 draft (11 April 2025) 13.2.1, p. 51. Code changed in 0.6.0 (URS-STAB-003, URS-STAB-005); GOLD-STAB-003 regenerated from R: crossing 24.33389941 months, shelf-life 24. The p = 0.25 boundary rule (only p > 0.25 pools) was recorded at the same time as URS-STAB-019 (user decision 2026-10-29, Shashank). |
| PC-STAB-02 | `criteria.py` (`STABILITY_PRIMARY_BATCHES`); `core/stability.py` (fewer-than-3-batches warning); URS-STAB-017; `docs/traceability.md` | Section numbers for "Selection of Batches" (believed 2.1.3 drug substance, 2.2.3 drug product) and the exact "at least three primary batches" wording. | ICH Q1A(R2) (2003) | open |
| PC-STAB-03 (unmarked) | `criteria.py` (`POOLABILITY_ALPHA` comment: "section 2.3 and Appendix B") | That section 2.3 and Appendix B are the correct locations for the 0.25 poolability significance level. | ICH Q1E (2003) | open |
| PC-STAB-04 (unmarked) | `criteria.py` (`SHELF_LIFE_CONFIDENCE`, `EXTRAPOLATION_FACTOR_STATS`, `EXTRAPOLATION_MAX_EXTRA_MONTHS_STATS`); `core/stability.py` docstrings | Section and page for the one-sided 95% confidence bound on the mean, and for the Appendix A cap in the "no significant change at accelerated, statistical analysis performed" branch (2X, at most 12 months beyond). | ICH Q1E (2003), main text and Appendix A | open |
| PC-STAB-05 (unmarked) | URS-STAB-008; `core/stability.py` (`extrapolation_cap`) | X, "the period covered by long-term data", is taken as the shortest of the batches' last time points (user decision 2026-10-27). Check this against the Appendix A wording. | ICH Q1E (2003), Appendix A | open |
| PC-STAB-06 | `ich-stats-rules` skill (ICH Q1 consolidation note); `criteria.py` (`GUIDELINE_VERSIONS["stability"]`) | ICH Q1 is being consolidated (Step 2 draft, April 2025). Q1E is kept as the rule set until the final text is confirmed; record which text 1.0.0 follows. | ICH Q1 final (Step 4) text, if adopted | open |
| PC-STAB-07 | `docs/traceability.md`; GOLD-STAB-001..003 `source` fields | A published worked example for GOLD-STAB-004. The current golden cases are independent R output on dummy data. | Published shelf-life example with batch data and results | open |
| PC-DISS-01 | `criteria.py` (`BOOTSTRAP_CI_LEVEL`); `core/dissolution.py` (`BOOTSTRAP_METHOD_NOTE`, `bootstrap_f2`, module docstring); `api.py` (`/dissolution` docstring); URS-DISS-007; `ich-stats-rules` skill §2 ("ask which agency's expectation applies"); `sample_data/README.md` | The bootstrap f2 method: percentile 90% interval, similarity when the 5th percentile is at least 50, units resampled with replacement per product. Also which agency's expectation applies. | Target agency's text on bootstrap f2; Shah et al., Pharm Res 1998 (full paper) | open |
| PC-DISS-02 (unmarked) | `core/dissolution.py` docstrings ("section V") | The section number for the dissolution profile comparison rules (f1, f2, 85% cut-off, CV limits, rapid dissolution). | FDA IR dissolution guidance (1997) | open |
| PC-DISS-03 (unmarked) | `criteria.py` (`CV_EARLY_MAX_TIME_MIN`, `RAPID_DISSOLUTION_TIME_MIN`) | "Earlier time points (for example up to 15 minutes)" is implemented as t ≤ 15 min for the 20% CV limit. Confirm the wording, and that this reading is acceptable. | FDA IR dissolution guidance (1997) | open |
| PC-DISS-04 | `docs/traceability.md` (URS-DISS-002, URS-DISS-007); GOLD-DISS-001 | A published f1/f2 worked example to replace the hand calculation in GOLD-DISS-001, and a bootstrap golden case against an independent implementation (for example R bootf2). | Published worked example; independent software output | open |
| PC-BE-01 | `criteria.py` (`BE_ROUND_DECIMALS` "confirm for the target agency", `BE_ROUNDING_MODE`); `core/be.py` (`be_decision`, result notes); URS-BE-016; `tests/golden/r/be_gold.R`; `sample_data/generate_be.R`; `ich-stats-rules` skill §3 | The rule for rounding CI limits before comparing them with 80.00–125.00%: number of decimals, and round half up or another rule. | Target agency's BE guidance | open |
| PC-BE-02 | `criteria.py` (`BE_AUC0INF_DECISION_MAKING`); `core/be.py` (result notes); URS-BE-014 | Whether AUC0-inf is a decision-making parameter; agencies differ (FDA vs EMA). | Target agency's BE guidance | open |
| PC-BE-03 (unmarked) | `core/be.py` docstrings; `docs/traceability.md` open-confirmations list | Section numbers for the 2x2 ANOVA model, the equivalence of the 90% CI and TOST at alpha 0.05, and the within-subject CV formula. | ICH M13A (2024); FDA BE statistics guidance | open |
| PC-BE-04 | `docs/traceability.md`; GOLD-BE-001..003 `source` fields | A published 2x2 crossover worked example. The current golden cases are independent R output on seeded dummy data. | Published BE worked example with subject data | open |
| PC-GEN-01 | Prerequisite for PC-DISS-01, PC-BE-01 and PC-BE-02 | Which target agency (or agencies) the tool assumes, recorded as a URS requirement. | User decision | open |

## Out of scope for v1 (not blocking 1.0.0)

These are deliberate limits, already refused with "not supported in v1". They are listed so
they are not mistaken for open items; they are not closed by 1.0.0.

- Stability: attributes expected to increase or to move either way (URS-STAB-006), and the
  ICH Q1E Appendix A branches other than "no significant change at accelerated, statistical
  analysis performed" (URS-STAB-007).
- Bioequivalence: replicate designs, parallel designs and reference-scaled limits
  (URS-BE-004 to 006).

## Definition of 1.0.0

1.0.0 may be released only when every row in the register has been closed in one of two ways.

**Confirmed against the source**
- The item is checked against the named source document. The register records the document
  title and version, section and page.
- Code, `criteria.py` comments, docstrings, URS and docs cite that section, and the
  "provisional", "placeholder" or "pending" wording for the item is removed.
- If the confirmed rule differs from the current implementation, the code changes under a
  URS ID with tests. Golden expected values are never edited to make a test pass; a changed
  calculated result is called out at the top of the CHANGELOG entry.

**Recorded as a known limitation**
- The register records why the item cannot be confirmed or is accepted as it is, the
  decision date and who decided.
- The limitation stays visible in the UI: it appears in the warning box on every affected
  result. URS-UI-011 currently promotes notes containing "pending confirmation" or
  "provisional", so recording the first known limitation also means extending that rule (and
  its test) to the limitation wording.
- The limitation is listed in the sample-data README where relevant, and in the CHANGELOG
  entry for 1.0.0.

**For every item, either way**
- The register row's status changes from **open** to **confirmed** or **known limitation**,
  with its evidence (section and page, or the justification).
- `/verify` and `/gxp-review` pass with no open issues, and `/validation-docs` has been run.
- The "Open confirmations" list in `docs/traceability.md` is empty, or lists only known
  limitations.

## Local references

Guideline PDFs used to close items go in `references/`, which is git-ignored so copyrighted
documents are never committed. Name files so the register can point to them, for example
`references/ICH_Q1E_2003.pdf` or `references/ICH_Q1A_R2_2003.pdf`.
