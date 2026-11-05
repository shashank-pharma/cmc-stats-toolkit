# Next session (written 2026-11-03, after v0.9.0, branch release/1.0.0, pushed to origin)

Done this session (decisions by Shashank, 2026-11-03; the user confirmed the quotes, PDFs not
reopened; see CHANGELOG 0.9.0 and docs/RELEASE-1.0.0.md):
- FDA guidance recorded as "Statistical Approaches to Establishing Bioequivalence (May 2026)";
  BE stamp is "ICH M13A (Step 4, 2024) + FDA Statistical Approaches to Establishing
  Bioequivalence (May 2026)".
- PC-BE-01 confirmed (2 decimals, FDA I.B footnote 6, p. 3) with known limitation: rounding
  mode half up is this tool's choice (URS-BE-020).
- PC-BE-02 confirmed (AUC0-inf decision-making, FDA II.C.2, p. 13) with known limitation: the
  FDA ANDA PK-endpoints guidance in footnote 6 was not checked (URS-BE-021).
- PC-BE-03 confirmed: M13A 2.2.3.1, 2.2.3.2, 2.2.4; FDA II.C.1.a; CVw formula from EMA 4.1.10.
- PC-BE-04 known limitation: base R golden cases; Schutz et al. 2014 planned for v1.1
  (URS-BE-022).
- New URS-BE-019: fewer than 12 evaluable subjects refused (M13A 2.2.3.1, p. 12). No golden
  or sample dataset had fewer than 12. The unit-test fixture and the UI BE template had 8, and
  both gained dummy subjects S09-S12.
- Version 0.9.0 (pre-1.0 minor bump: new refusal; not 1.0.0 because /gxp-review and
  /validation-docs have not run).

Register: every row in docs/RELEASE-1.0.0.md is confirmed or a known limitation.

Decision by Shashank, 2026-11-04: the PDF report is not in 1.0.0; planned for v1.1 (see
docs/RELEASE-1.0.0.md, "Planned for v1.1"). No URS requirement depended on it.

Still to do for 1.0.0:
1. /gxp-review (no open issues).
2. /validation-docs. The traceability matrix got targeted edits only (new rows URS-BE-019..022,
   renamed tests, open-confirmations list); refresh every row's /verify date.
3. Then decide on the 1.0.0 release (CHANGELOG entry must list every known limitation).
Golden regeneration: uv run python tests/golden/r/merge_stability_gold.py and
uv run python tests/golden/r/merge_dissolution_gold.py.
