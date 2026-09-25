# Ticket 195: Adopt Wellmanifest new-project 0.20.38

- **ID**: ticket-195
- **Owner**: agent
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

Adopt and synchronize `wellmanifest/new-project` 0.20.38
(`e2fd653ff801fb228fca818e1d874ee685a4da62`, annotated tag `v0.20.38`, final
published release) across Koru's managed governance projection through the
immutable updater (`create_adoption_lock.py --source-revision e2fd653f…
--upgrade`).

Motivation: the protected Validator's semantic review of PR #357 (ticket-172)
flagged the 0.20.33 `AGENTS.md` `wellmanifest:autonomous-merge` section as a
critical governance finding — it authorized reviewer profile rotation,
administrative branch-protection bypass and CDP merge fallback. Upstream
corrected that guidance in `wellmanifest/new-project` ticket-256 (commit
`74fc51e`, published in `v0.20.38`), replacing it with
`wellmanifest:protected-delivery` instructions: tests never grant merge
authority, never self-approve, never rotate reviewers, never bypass branch
protection or use admin tokens/browser sessions to evade review.

## Acceptance criteria

- [ ] AC-01: `.governance/manifest.json`, `.governance/manifest.base.json` and
  `.governance/manifest.lock.json` bind 0.20.38 at
  `e2fd653ff801fb228fca818e1d874ee685a4da62`; `standard_pack_check.py` and
  `git diff --check` pass.
- [ ] AC-02: Standard-managed files match the 0.20.38 projection; the updater
  drift check against `e2fd653f…` reports up-to-date.
- [ ] AC-03: `.governance/standard-adoption.json` and
  `.governance/standard-pack-evidence/new-project.json` carry valid S0-S4
  receipts bound to `e2fd653f…`; `standard_pack_projection_check.py` passes.
- [ ] AC-04: `package.json` and `pyproject.toml` `[tool.wellmanifest]`
  reference 0.20.38 and `e2fd653ff801fb228fca818e1d874ee685a4da62`;
  `./project/governance-check.sh` passes.
- [ ] AC-05: The adopted `AGENTS.md` no longer contains the
  `wellmanifest:autonomous-merge` section flagged by the Validator; it carries
  the upstream `wellmanifest:protected-delivery` guidance.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
