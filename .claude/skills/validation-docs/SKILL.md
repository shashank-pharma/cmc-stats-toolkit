---
name: validation-docs
description: Update the validation documents - requirement list (docs/URS.md), traceability matrix (docs/traceability.md) and CHANGELOG.md - after a feature is finished.
disable-model-invocation: true
---

# Update validation documents

Current changes:

!`git diff HEAD --stat`

1. For each new or changed behaviour, make sure `docs/URS.md` has a requirement with an ID,
   a one-line statement and the guideline it comes from. Add missing ones and show them to me.
2. In `docs/traceability.md`, every requirement row must list: the function(s) that implement
   it, the test ID(s) that prove it, and the result of the last `/verify` run.
   Flag any requirement without a test, and any test without a requirement.
3. Add a dated entry to `CHANGELOG.md` (Added, Changed, Fixed). Bump the version in
   `pyproject.toml` following semantic versioning: patch for fixes, minor for new features,
   major for changed results or removed features.
4. If any calculated result changes for existing inputs, say so at the top of the changelog
   entry. That is a major version change.
