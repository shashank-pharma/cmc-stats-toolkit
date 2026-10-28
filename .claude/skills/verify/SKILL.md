---
name: verify
description: Run every quality check for this project - ruff lint and format, mypy strict typing, and the full pytest suite with golden tests and coverage. Use before every commit, after any code change, and whenever the user asks whether the code works or is ready.
allowed-tools: Bash(uv sync) Bash(uv run ruff *) Bash(uv run mypy) Bash(uv run mypy *) Bash(uv run pytest) Bash(uv run pytest *)
---

# Verify

Run these in order and stop at the first failure:

1. `uv sync`
2. `uv run ruff format --check .`
3. `uv run ruff check .`
4. `uv run mypy`
5. `uv run pytest --cov=src/cmc_stats --cov-report=term-missing --cov-fail-under=90`
   (a directory, not the package name, so `ui.py` run by Streamlit's AppTest as `__main__`
   is counted)

Then report in this shape:

- Result: PASS or FAIL
- Failing step and the exact error lines
- Golden tests: number passed, failed, skipped
- Coverage: total percentage and any core module below 90%

Fix lint, format and typing problems directly. For failing golden tests, follow
`/golden-test` step 6 and never change expected values.
