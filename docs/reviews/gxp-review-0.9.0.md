# /gxp-review record: v0.9.0

> **This is a summary of the run as reported by the user (Shashank, 2026-11-06), not the raw
> review output.** The raw output was not kept in the repository.

| Field | Value |
|---|---|
| Version reviewed | v0.9.0 |
| Scope | branch `release/1.0.0` compared with `main`: 9 commits, 41 files |
| Reported by | Shashank, 2026-11-06 |
| Result | No data-integrity findings; all 8 checks clear |

## Checks

| Check | Result |
|---|---|
| Attributable and traceable | clear |
| Original data kept | clear |
| Accurate | clear |
| Validated input | clear |
| Reproducible | clear |
| Cited | clear |
| Tested | clear |
| Honest output | clear |

## Note outside the diff

`src/cmc_stats/report.py` never existed, so the PDF report was moved to v1.1 (decided by
Shashank, 2026-11-04; see CHANGELOG 0.9.1 and `docs/RELEASE-1.0.0.md`, "Planned for v1.1").

## Use for 1.0.0

Only documentation and the version number changed after 0.9.0, so no second `/gxp-review` was
run for 1.0.0 (decided by Shashank, 2026-11-06). This review is the release review; see
`docs/RELEASE-1.0.0.md`, "Release decision (1.0.0, 2026-11-06)".
