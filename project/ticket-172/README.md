# Ticket 172: Adopt Wellmanifest new-project 0.20.33

- **ID**: ticket-172
- **Owner**: agent
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-19

## Goal and scope

Adopt and synchronize `wellmanifest/new-project` 0.20.33
(`a8245857259d8d42115108f191c586b76cb1e2bd`, annotated tag `v0.20.33`) across
Koru's managed governance projection, delivered as two sequential slices of
this one ticket:

1. **Repair slice** (first PR, PR #356): restore the pinned 0.20.32 managed
   projection atomically through the immutable updater
   (`create_adoption_lock.py --source-revision b6ba9c21… --upgrade`). This
   regenerates `.governance/manifest.lock.json`, removing the hand-added
   extendable `.governance/manifest.json` pin and the hand-pinned drifted
   `wellmanifest_governance.py` digest that ticket-154 introduced, and
   restores `wellmanifest_governance.py` to its pinned 0.20.32 content. The
   pytest `--collect-only` skip that ticket-154 hand-patched into the managed
   file is removed here and returns officially with the adoption slice
   (upstream wellmanifest/new-project ticket-248, PR #381, merged in the
   0.20.33 projection). The updater transaction is atomic: the lock change
   rides with a managed package target change, which the protected Validator's
   package-advisory contract requires (a lock-only repair is undeliverable;
   blocked receipt for PR #356 at `46ebf08e`).
2. **Adoption slice** (second PR, after the repair merges — the atomic
   adoption proof validates its Git base against exactly the repaired lock
   invariant): regenerate the managed package and `manifest.lock.json`
   through the immutable updater at `a8245857…`, update
   `.governance/standard-adoption.json` and evidence receipts, and update
   version carriers (`.governance/manifest.json`,
   `.governance/manifest.base.json`, `package.json`, `pyproject.toml`).

Depends on ticket-173 (governance) making the new managed workflow path
trackable in `.gitignore`; that dependency is merged (PR #355, `6b65c7f2`).

SESSION_EXECUTION_AUTHORIZATION: the user explicitly requested to continue
with the next ticket (2026-09-19), covering execution, protected publication
and merge of this allocated ticket. Repeated unchanged by the user in the
follow-up session on 2026-09-19 for the atomic updater-based repair slice
described above.

## Acceptance criteria

- [ ] AC-01: `.governance/manifest.lock.json` target set equals the package manifest managed strategies and every digest matches the working tree (repair slice).
- [ ] AC-02: `wellmanifest_governance.py` byte-equals the pinned 0.20.32 managed projection; the updater drift check against `b6ba9c21…` reports up-to-date (repair slice).
- [ ] AC-03: `.governance/manifest.json`, `.governance/manifest.base.json` and `.governance/manifest.lock.json` bind published `wellmanifest/new-project` 0.20.33 at `a8245857259d8d42115108f191c586b76cb1e2bd` (adoption slice).
- [ ] AC-04: Standard-managed files match the 0.20.33 projection, including the new branch-hygiene workflow and the upstream collect-only skip; updater drift check reports up-to-date (adoption slice).
- [ ] AC-05: `.governance/standard-adoption.json` and `.governance/standard-pack-evidence/new-project.json` carry valid S0-S4 evidence with upstream CI run 35451961370 and ruleset 20451097 receipts (adoption slice).
- [ ] AC-06: `package.json` and `pyproject.toml` `[tool.wellmanifest]` reference 0.20.33 and the new revision (adoption slice).
- [ ] AC-07: `standard_pack_check.py`, `standard_pack_projection_check.py`, `governance-check.sh` and `git diff --check` pass on both slices.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
