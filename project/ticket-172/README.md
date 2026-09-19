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

1. **Repair slice** (first PR): remove the hand-added extendable
   `.governance/manifest.json` pin from `.governance/manifest.lock.json`
   (introduced by ticket-154) so the lock's target set equals the package
   manifest's managed strategies; the 0.20.33 atomic adoption proof validates
   its Git base fail-closed against exactly this invariant.
2. **Adoption slice** (second PR, after the repair merges): regenerate the
   managed package and `manifest.lock.json` through the immutable updater,
   update `.governance/standard-adoption.json` and evidence receipts, and
   update version carriers (`.governance/manifest.json`,
   `.governance/manifest.base.json`, `package.json`, `pyproject.toml`).

Depends on ticket-173 (governance) making the new managed workflow path
trackable in `.gitignore`; that path stays outside this ticket's scope.

SESSION_EXECUTION_AUTHORIZATION: the user explicitly requested to continue
with the next ticket in this conversation (2026-09-19), covering execution,
protected publication and merge of this allocated ticket.

## Acceptance criteria

- [ ] AC-01: `.governance/manifest.lock.json` target set equals the package manifest managed strategies (repair slice).
- [ ] AC-02: `.governance/manifest.json`, `.governance/manifest.base.json` and `.governance/manifest.lock.json` bind published `wellmanifest/new-project` 0.20.33 at `a8245857259d8d42115108f191c586b76cb1e2bd` (adoption slice).
- [ ] AC-03: Standard-managed files match the 0.20.33 projection, including the new branch-hygiene workflow; updater drift check reports up-to-date (adoption slice).
- [ ] AC-04: `.governance/standard-adoption.json` and `.governance/standard-pack-evidence/new-project.json` carry valid S0-S4 evidence with upstream CI run 35451961370 and ruleset 20451097 receipts (adoption slice).
- [ ] AC-05: `package.json` and `pyproject.toml` `[tool.wellmanifest]` reference 0.20.33 and the new revision (adoption slice).
- [ ] AC-06: `standard_pack_check.py`, `standard_pack_projection_check.py`, `governance-check.sh` and `git diff --check` pass on both slices.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
