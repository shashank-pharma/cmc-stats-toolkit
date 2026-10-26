---
name: golden-test
description: Add a golden (reference) test from a published worked example, textbook table or independent R/SAS output, so a statistics function is proven against known answers. Use whenever a new calculation is added or changed in src/cmc_stats/core, or the user shares a published dataset, paper table or software output to check against.
argument-hint: "[short description of the source]"
---

# Add a golden test

Source given by the user: $ARGUMENTS

1. Ask for anything missing: the citation (authors, year, title, table or page), the input
   data exactly as published, the expected outputs, and how many decimals the source reports.
2. Pick the next free ID: `GOLD-<AREA>-<NNN>` with AREA = STAB, DISS or BE. Find the
   requirement ID it proves in `docs/URS.md`.
3. Write `tests/golden/data/<ID>.json`:
   ```json
   {
     "id": "GOLD-STAB-001",
     "requirement": "URS-STAB-003",
     "source": "Full citation, table or page number",
     "inputs": {},
     "expected": {},
     "tolerance": 0.001
   }
   ```
   Set the tolerance from the source's reported precision (half of the last reported digit),
   never wider to make a test pass.
4. Make sure a parametrised test in `tests/golden/test_golden_<area>.py` loads every
   `<ID>.json` for that area. Create the test file if it does not exist.
5. Run `uv run pytest tests/golden -q`.
6. If the test fails, do not touch the expected values. Report the difference, then check in
   this order: transcription of the inputs, the rule in `/ich-stats-rules`, the code.
7. Add the new test ID to `docs/traceability.md` against its requirement.
