# CMC Stats Toolkit

ICH Q1E stability shelf-life, dissolution f1/f2 (with bootstrap f2) and 2x2 crossover
bioequivalence, built as a tested Python engine with a FastAPI backend and a Streamlit UI.

Educational and decision-support tool. Not validated for GxP use.

## Quick start

```bash
uv sync
uv run pytest
```

## Working with Claude Code

Open this folder in a terminal and run `claude`. Project rules are in `CLAUDE.md`.
Project skills live in `.claude/skills/`:

| Skill | Use it for |
|---|---|
| `/ich-stats-rules` | The regulatory rules every calculation must follow (loads automatically) |
| `/golden-test` | Add a test from a published worked example |
| `/verify` | Lint, types, tests and coverage before every commit |
| `/validation-docs` | Update URS, traceability matrix and changelog after a feature |
| `/gxp-review` | Data-integrity review of your changes |
