# Next session (written 2026-11-06, after v1.0.0 commit, branch release/1.0.0)

Current state: v1.0.0 committed on release/1.0.0; not merged to main and not tagged
(see CHANGELOG 1.0.0). No calculated result changed since 0.9.0.

- Register: every row in docs/RELEASE-1.0.0.md is confirmed or a known limitation; the
  release decision (2026-11-06, Shashank) is recorded there, including that no second
  /gxp-review is needed (0.9.0 review stands; only documentation changed since).
- /verify: PASS on v1.0.0 (2026-11-06): 397 tests, 10 golden, coverage 99.25%.
- README rewritten for 1.0.0; screenshot placeholders still to be filled.

Remaining release steps (awaiting Shashank):
1. Merge release/1.0.0 into main.
2. Tag v1.0.0.

v1.1 roadmap: published golden examples, PDF report, refrigerated stability branch.

Golden regeneration: uv run python tests/golden/r/merge_stability_gold.py and
uv run python tests/golden/r/merge_dissolution_gold.py.
