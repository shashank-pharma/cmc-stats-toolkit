# Next session (written 2026-11-06, after v0.9.1, branch release/1.0.0)

Current state: v0.9.1 (patch bump, documentation only; no calculated result or code changes;
see CHANGELOG 0.9.1).

- Register: every row in docs/RELEASE-1.0.0.md is confirmed or a known limitation. No open
  confirmations remain (docs/traceability.md "Open confirmations" lists known limitations only).
- /gxp-review: ran on v0.9.0, all 8 checks clear (no open issues).
- /validation-docs: ran on v0.9.1 (2026-11-06). Every traceability row refreshed; all 87 URS
  IDs have a row with implementing function(s) and at least one test.
- /verify: PASS on v0.9.1 (2026-11-06): 397 tests, 10 golden, coverage 99.25%.
- PDF report is not in 1.0.0; planned for v1.1 (decision by Shashank, 2026-11-04).

Only the 1.0.0 release steps remain:
1. Decide on the 1.0.0 release.
2. CHANGELOG 1.0.0 entry must list every known limitation (see docs/RELEASE-1.0.0.md and the
   traceability "Open confirmations" list).
3. Bump version to 1.0.0, run /verify, commit and tag.

Golden regeneration: uv run python tests/golden/r/merge_stability_gold.py and
uv run python tests/golden/r/merge_dissolution_gold.py.
